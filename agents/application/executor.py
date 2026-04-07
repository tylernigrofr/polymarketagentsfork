import ast
import json
import math
import os
import re
from dataclasses import asdict
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, ValidationError

from agents.application.prompts import Prompter
from agents.connectors.chroma import PolymarketRAG as Chroma
from agents.llm.factory import get_chat_model, get_runtime_info
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.polymarket.polymarket import Polymarket
from agents.utils.objects import SimpleEvent, SimpleMarket


def retain_keys(data, keys_to_retain):
    if isinstance(data, dict):
        return {
            key: retain_keys(value, keys_to_retain)
            for key, value in data.items()
            if key in keys_to_retain
        }
    elif isinstance(data, list):
        return [retain_keys(item, keys_to_retain) for item in data]
    else:
        return data


class Executor:
    class ForecastResult(BaseModel):
        probability: float = Field(..., ge=0.0, le=1.0)
        outcome: Optional[str] = None
        confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
        rationale: Optional[str] = None
        raw: str

    class TradeProposal(BaseModel):
        price: float = Field(..., ge=0.0, le=1.0)
        size_fraction: float = Field(..., ge=0.0, le=1.0)
        side: Literal["BUY", "SELL"]
        raw: str

    def __init__(self, default_model: str = "gpt-3.5-turbo-16k") -> None:
        load_dotenv()
        max_token_model = {"gpt-3.5-turbo-16k": 15000, "gpt-4-1106-preview": 95000}
        self.token_limit = max_token_model.get(default_model, 12000)
        self.prompter = Prompter()
        # Provider/model selection is env-driven; `default_model` remains for backward compatibility
        # (e.g. token_limit heuristics) but does not directly configure the provider anymore.
        self.llm = get_chat_model(task_name="default", temperature=0.0)
        self.runtime = get_runtime_info(task_name="default")
        self.gamma = Gamma()
        self.chroma = Chroma()
        self.polymarket = Polymarket()

    def get_llm_response(self, user_input: str) -> str:
        system_message = SystemMessage(content=str(self.prompter.market_analyst()))
        human_message = HumanMessage(content=user_input)
        messages = [system_message, human_message]
        result = self.llm.invoke(messages)
        return result.content

    def get_superforecast(
        self, event_title: str, market_question: str, outcome: str
    ) -> str:
        messages = self.prompter.superforecaster(
            description=event_title, question=market_question, outcome=outcome
        )
        result = self.llm.invoke(messages)
        return result.content

    def forecast_probability(
        self, question: str, description: str, outcome: str
    ) -> "Executor.ForecastResult":
        prompt = self.prompter.superforecaster(question, description, outcome)
        result = self.llm.invoke(prompt)
        raw = str(result.content)

        # Extract first float in [0,1] from the model output as probability.
        prob: Optional[float] = None
        match = re.search(r"(?<!\d)(0(?:\.\d+)?|1(?:\.0+)?)(?!\d)", raw)
        if match:
            try:
                prob = float(match.group(1))
            except ValueError:
                prob = None
        if prob is None:
            # Fall back to a looser float parse then clamp.
            match2 = re.search(r"(\d+\.\d+|\d+)", raw)
            if match2:
                try:
                    prob = float(match2.group(1))
                except ValueError:
                    prob = 0.5
            else:
                prob = 0.5
        prob = max(0.0, min(1.0, prob))
        return Executor.ForecastResult(
            probability=prob,
            outcome=str(outcome) if outcome is not None else None,
            rationale=raw,
            raw=raw,
        )

    def propose_trade(
        self, prediction_text: str, outcomes: List[str], outcome_prices: List[float]
    ) -> "Executor.TradeProposal":
        prompt = self.prompter.one_best_trade(prediction_text, outcomes, outcome_prices)
        result = self.llm.invoke(prompt)
        raw = str(result.content)
        return self.parse_trade_proposal(raw)

    def parse_trade_proposal(self, raw: str) -> "Executor.TradeProposal":
        """
        Parse the legacy free-form trade proposal output into a structured TradeProposal.
        This is deterministic and does not call an LLM.
        """
        # Very permissive parsing of the existing non-JSON format.
        side_match = re.search(r"\b(BUY|SELL)\b", raw.upper())
        side: Literal["BUY", "SELL"] = (
            "BUY" if not side_match else side_match.group(1)  # type: ignore[assignment]
        )

        floats = re.findall(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", raw)
        price = float(floats[0]) if len(floats) >= 1 else 0.5
        size_fraction = float(floats[1]) if len(floats) >= 2 else 0.0

        price = max(0.0, min(1.0, price))
        size_fraction = max(0.0, min(1.0, size_fraction))
        return Executor.TradeProposal(
            price=price, size_fraction=size_fraction, side=side, raw=raw
        )

    def decide_trade(
        self,
        forecast: "Executor.ForecastResult",
        market_price: Optional[float] = None,
        min_edge: float = 0.02,
    ) -> Dict[str, Any]:
        """
        Deterministic decision wrapper. For now, this keeps behavior close to the existing flow:
        - If market_price is provided, compute a simple edge and direction.
        - Returns a structured dict suitable for logging/trade tickets later.
        """
        decision: Dict[str, Any] = {
            "forecast": forecast.model_dump(),
            "runtime": asdict(self.runtime),
        }
        if market_price is None:
            decision["action"] = "NO_TRADE"
            decision["reason"] = "missing_market_price"
            return decision

        edge = forecast.probability - market_price
        decision["market_price"] = market_price
        decision["edge"] = edge

        if abs(edge) < min_edge:
            decision["action"] = "NO_TRADE"
            decision["reason"] = "edge_below_threshold"
            return decision

        decision["action"] = "TRADE"
        decision["side"] = "BUY" if edge > 0 else "SELL"
        decision["target_price"] = forecast.probability
        return decision

    def estimate_tokens(self, text: str) -> int:
        # This is a rough estimate. For more accurate results, consider using a tokenizer.
        return len(text) // 4  # Assuming average of 4 characters per token

    def process_data_chunk(
        self, data1: List[Dict[Any, Any]], data2: List[Dict[Any, Any]], user_input: str
    ) -> str:
        system_message = SystemMessage(
            content=str(self.prompter.prompts_polymarket(data1=data1, data2=data2))
        )
        human_message = HumanMessage(content=user_input)
        messages = [system_message, human_message]
        result = self.llm.invoke(messages)
        return result.content

    def divide_list(self, original_list, i):
        # Calculate the size of each sublist
        sublist_size = math.ceil(len(original_list) / i)

        # Use list comprehension to create sublists
        return [
            original_list[j : j + sublist_size]
            for j in range(0, len(original_list), sublist_size)
        ]

    def get_polymarket_llm(self, user_input: str) -> str:
        data1 = self.gamma.get_current_events()
        data2 = self.gamma.get_current_markets()

        combined_data = str(self.prompter.prompts_polymarket(data1=data1, data2=data2))

        # Estimate total tokens
        total_tokens = self.estimate_tokens(combined_data)

        # Set a token limit (adjust as needed, leaving room for system and user messages)
        token_limit = self.token_limit
        if total_tokens <= token_limit:
            # If within limit, process normally
            return self.process_data_chunk(data1, data2, user_input)
        else:
            # If exceeding limit, process in chunks
            chunk_size = len(combined_data) // ((total_tokens // token_limit) + 1)
            print(
                f"total tokens {total_tokens} exceeding llm capacity, now will split and answer"
            )
            group_size = (total_tokens // token_limit) + 1  # 3 is safe factor
            keys_no_meaning = [
                "image",
                "pagerDutyNotificationEnabled",
                "resolvedBy",
                "endDate",
                "clobTokenIds",
                "negRiskMarketID",
                "conditionId",
                "updatedAt",
                "startDate",
            ]
            useful_keys = [
                "id",
                "questionID",
                "description",
                "liquidity",
                "clobTokenIds",
                "outcomes",
                "outcomePrices",
                "volume",
                "startDate",
                "endDate",
                "question",
                "questionID",
                "events",
            ]
            data1 = retain_keys(data1, useful_keys)
            cut_1 = self.divide_list(data1, group_size)
            cut_2 = self.divide_list(data2, group_size)
            cut_data_12 = zip(cut_1, cut_2)

            results = []

            for cut_data in cut_data_12:
                sub_data1 = cut_data[0]
                sub_data2 = cut_data[1]
                sub_tokens = self.estimate_tokens(
                    str(
                        self.prompter.prompts_polymarket(
                            data1=sub_data1, data2=sub_data2
                        )
                    )
                )

                result = self.process_data_chunk(sub_data1, sub_data2, user_input)
                results.append(result)

            combined_result = " ".join(results)

            return combined_result

    def filter_events(self, events: "list[SimpleEvent]") -> str:
        prompt = self.prompter.filter_events(events)
        result = self.llm.invoke(prompt)
        return result.content

    def filter_events_with_rag(self, events: "list[SimpleEvent]") -> str:
        prompt = self.prompter.filter_events()
        print()
        print("... prompting ... ", prompt)
        print()
        return self.chroma.events(events, prompt)

    def map_filtered_events_to_markets(
        self, filtered_events: "list[SimpleEvent]"
    ) -> "list[SimpleMarket]":
        markets = []
        for e in filtered_events:
            data = json.loads(e[0].json())
            market_ids = data["metadata"]["markets"].split(",")
            for market_id in market_ids:
                market_data = self.gamma.get_market(market_id)
                formatted_market_data = self.polymarket.map_api_to_market(market_data)
                markets.append(formatted_market_data)
        return markets

    def filter_markets(self, markets) -> "list[tuple]":
        prompt = self.prompter.filter_markets()
        print()
        print("... prompting ... ", prompt)
        print()
        return self.chroma.markets(markets, prompt)

    def source_best_trade(self, market_object) -> str:
        market_document = market_object[0].dict()
        market = market_document["metadata"]
        outcome_prices = ast.literal_eval(market["outcome_prices"])
        outcomes = ast.literal_eval(market["outcomes"])
        question = market["question"]
        description = market_document["page_content"]

        forecast = self.forecast_probability(
            question=question, description=description, outcome=str(outcomes)
        )
        print()
        print("forecast:", forecast.raw)
        print()

        trade = self.propose_trade(
            prediction_text=forecast.raw,
            outcomes=[str(x) for x in outcomes],
            outcome_prices=[float(x) for x in outcome_prices],
        )
        print("trade_proposal:", trade.raw)
        print()
        return trade.raw

    def source_best_trade_context(self, market_object) -> Dict[str, Any]:
        """
        Like `source_best_trade`, but returns a structured context object suitable for ticketing.
        Keeps the current RAG-first data flow intact while making downstream execution deterministic.
        """
        market_document = market_object[0].dict()
        market = market_document["metadata"]
        outcome_prices = ast.literal_eval(market["outcome_prices"])
        outcomes = ast.literal_eval(market["outcomes"])
        question = market["question"]
        description = market_document["page_content"]

        forecast = self.forecast_probability(
            question=question, description=description, outcome=str(outcomes)
        )
        proposal = self.propose_trade(
            prediction_text=forecast.raw,
            outcomes=[str(x) for x in outcomes],
            outcome_prices=[float(x) for x in outcome_prices],
        )

        return {
            "market_id": (
                int(market.get("id")) if market.get("id") is not None else None
            ),
            "question": question,
            "description": description,
            "outcomes": outcomes,
            "outcome_prices": outcome_prices,
            "forecast": forecast,
            "proposal": proposal,
            "proposal_raw": proposal.raw,
            "runtime": asdict(self.runtime),
        }

    def format_trade_prompt_for_execution(self, best_trade: str) -> float:
        data = best_trade.split(",")
        # price = re.findall("\d+\.\d+", data[0])[0]
        size = re.findall("\d+\.\d+", data[1])[0]
        usdc_balance = self.polymarket.get_usdc_balance()
        return float(size) * usdc_balance

    def source_best_market_to_create(self, filtered_markets) -> str:
        prompt = self.prompter.create_new_market(filtered_markets)
        print()
        print("... prompting ... ", prompt)
        print()
        result = self.llm.invoke(prompt)
        content = result.content
        return content
