"""
Standalone Polymarket AI Predictions Web App
A self-contained version using Polymarket Gamma API (no auth required) + OpenRouter
"""

import os
import json
import time
import ast
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
import httpx
import openai
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
import logging

# Note: No CLOB dependencies needed - using only Gamma API for market data

# Load environment variables
load_dotenv()

# Configuration constants
class Config:
    GAMMA_API_BASE = "https://gamma-api.polymarket.com"
    DEFAULT_TIMEOUT = 30.0
    MAX_MARKETS_LIMIT = 100
    DEFAULT_MODEL = "anthropic/claude-3-haiku"
    
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def safe_parse_list(data: str) -> List[str]:
    """Safely parse a string representation of a list"""
    if not data:
        return []
    try:
        # First try JSON parsing
        return json.loads(data)
    except json.JSONDecodeError:
        try:
            # Fall back to ast.literal_eval for Python literals
            result = ast.literal_eval(data)
            return result if isinstance(result, list) else []
        except (ValueError, SyntaxError):
            logger.warning(f"Failed to parse list data: {data}")
            return []

def safe_parse_float_list(data: str) -> List[float]:
    """Safely parse a string representation of a list of floats"""
    if not data:
        return []
    try:
        parsed_data = safe_parse_list(data)
        return [float(x) for x in parsed_data]
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse float list data: {data}")
        return []

# Initialize FastAPI app
app = FastAPI(
    title="Polymarket AI Predictions",
    description="AI-powered prediction market analysis",
    version="1.0.0"
)

# Add CORS middleware
def get_cors_origins():
    """Get allowed CORS origins based on environment"""
    if os.getenv("ENVIRONMENT") == "production":
        # In production, specify your actual domain(s)
        return ["https://yourdomain.com", "https://www.yourdomain.com"]
    else:
        # In development, allow localhost and common dev ports
        return ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=False,  # Only enable if you need authentication cookies
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Security middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Content Security Policy
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    
    # Other security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve static files directly (for CSS, JS, etc.)
@app.get("/style.css")
async def get_css():
    return FileResponse("static/style.css", media_type="text/css")

@app.get("/script.js")
async def get_js():
    return FileResponse("static/script.js", media_type="application/javascript")

# Configuration
USE_REAL_DATA = os.getenv("USE_REAL_DATA", "true").lower() == "true"
FALLBACK_TO_MOCK = os.getenv("FALLBACK_TO_MOCK", "true").lower() == "true"
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "anthropic/claude-3-haiku")

# Pydantic models
class MarketResponse(BaseModel):
    id: str
    question: str
    description: str
    active: bool
    volume: Optional[float] = None
    spread: Optional[float] = None
    outcomes: str
    outcome_prices: str
    clob_token_ids: str

class PredictionRequest(BaseModel):
    market_id: str
    question: str
    description: str
    outcomes: List[str]
    
    @field_validator('question')
    @classmethod
    def question_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty')
        if len(v) > 500:
            raise ValueError('Question too long (max 500 characters)')
        return v.strip()
    
    @field_validator('outcomes')
    @classmethod
    def outcomes_must_be_valid(cls, v):
        if len(v) < 2:
            raise ValueError('At least 2 outcomes required')
        if len(v) > 10:
            raise ValueError('Too many outcomes (max 10)')
        for outcome in v:
            if not outcome.strip():
                raise ValueError('All outcomes must be non-empty')
        return [outcome.strip() for outcome in v]
    
    @field_validator('description')
    @classmethod
    def description_must_be_reasonable(cls, v):
        if len(v) > 1000:
            raise ValueError('Description too long (max 1000 characters)')
        return v.strip()

class PredictionResponse(BaseModel):
    prediction: str
    confidence: float
    reasoning: str

class NewsRequest(BaseModel):
    keywords: str
    limit: Optional[int] = 10
    
    @field_validator('keywords')
    @classmethod
    def keywords_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('Keywords cannot be empty')
        if len(v) > 200:
            raise ValueError('Keywords too long (max 200 characters)')
        return v.strip()
    
    @field_validator('limit')
    @classmethod
    def limit_must_be_reasonable(cls, v):
        if v and (v < 1 or v > 50):
            raise ValueError('Limit must be between 1 and 50')
        return v

class NewsResponse(BaseModel):
    title: str
    description: str
    url: str
    published_at: str
    source: str

# Data models for services
@dataclass
class MarketData:
    id: str
    question: str
    description: str
    outcomes: List[str]
    prices: List[float]
    volume: float
    spread: float
    active: bool
    clob_token_ids: Optional[str] = None

@dataclass
class EventData:
    id: str
    title: str
    description: str
    active: bool
    markets: str

@dataclass
class OrderBookData:
    bids: List[tuple[float, float]]
    asks: List[tuple[float, float]]

@dataclass
class ModelInfo:
    id: str
    name: str
    description: str
    context_length: int
    pricing: Dict[str, float]

# Service Classes
class PolymarketService:
    """
    Service for fetching Polymarket market data using Gamma API (no auth required)

    This service uses Polymarket's Gamma API which provides:
    - Market questions, descriptions, and outcomes
    - Current market prices and volumes
    - Event information
    - All data is publicly available with NO authentication required

    Note: This does NOT include order book data (requires CLOB API authentication)
    or trading functionality. For AI analysis of market questions and predictions,
    this provides all necessary data.
    """

    def __init__(self):
        self.base_url = "https://gamma-api.polymarket.com"
        self.markets_endpoint = f"{self.base_url}/markets"
        self.events_endpoint = f"{self.base_url}/events"

        # Initialize HTTP client
        self.client = httpx.AsyncClient(timeout=30.0)

        print("[SUCCESS] Polymarket Gamma API service initialized (no authentication required)")

    async def get_markets(self, limit: int = 50) -> List[MarketData]:
        """Fetch markets from Polymarket API using correct parameters"""
        try:
            # Use the correct parameters from the original gamma.py implementation
            params = {
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit
            }

            print(f"[DEBUG] Fetching markets with params: {params}")
            response = await self.client.get(self.markets_endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"[DEBUG] API returned {len(data)} markets")

            markets = []
            for market in data:
                try:
                    # Parse outcomes and prices (handle stringified JSON)
                    outcomes = market.get("outcomes", [])
                    outcome_prices = market.get("outcomePrices", [])

                    # Handle stringified JSON from API
                    if isinstance(outcome_prices, str):
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except:
                            outcome_prices = []

                    if isinstance(outcomes, str):
                        try:
                            outcomes = json.loads(outcomes)
                        except:
                            outcomes = []

                    # Convert prices to float
                    prices = []
                    if outcome_prices:
                        for price in outcome_prices:
                            try:
                                prices.append(float(price))
                            except (ValueError, TypeError):
                                prices.append(0.0)

                    market_data = MarketData(
                        id=str(market.get("id", "")),
                        question=market.get("question", ""),
                        description=market.get("description", ""),
                        outcomes=outcomes,
                        prices=prices,
                        volume=float(market.get("volume", 0) or 0),
                        spread=float(market.get("spread", 0) or 0),
                        active=market.get("active", False),
                        clob_token_ids=str(market.get("clobTokenIds", ""))
                    )
                    markets.append(market_data)

                    # Debug first few markets
                    if len(markets) <= 3:
                        print(f"[DEBUG] Market {market_data.id}: {market_data.question[:50]}... (Active: {market_data.active})")

                except Exception as e:
                    print(f"Error processing market {market.get('id')}: {e}")
                    continue

            print(f"[DEBUG] Successfully processed {len(markets)} markets")
            return markets

        except Exception as e:
            print(f"Error fetching markets: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def get_market(self, market_id: str) -> Optional[MarketData]:
        """Fetch specific market details using correct endpoint"""
        try:
            # Use the correct endpoint format from gamma.py
            url = f"{self.markets_endpoint}/{market_id}"
            print(f"[DEBUG] Fetching market from: {url}")

            response = await self.client.get(url)
            response.raise_for_status()
            market = response.json()

            # Parse outcomes and prices (handle stringified JSON)
            outcomes = market.get("outcomes", [])
            outcome_prices = market.get("outcomePrices", [])

            # Handle stringified JSON from API
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = []

            if isinstance(outcomes, str):
                try:
                    outcomes = json.loads(outcomes)
                except:
                    outcomes = []

            # Convert prices to float
            prices = []
            if outcome_prices:
                for price in outcome_prices:
                    try:
                        prices.append(float(price))
                    except (ValueError, TypeError):
                        prices.append(0.0)

            return MarketData(
                id=str(market.get("id", "")),
                question=market.get("question", ""),
                description=market.get("description", ""),
                outcomes=outcomes,
                prices=prices,
                volume=float(market.get("volume", 0) or 0),
                spread=float(market.get("spread", 0) or 0),
                active=market.get("active", False),
                clob_token_ids=str(market.get("clobTokenIds", ""))
            )

        except Exception as e:
            print(f"Error fetching market {market_id}: {e}")
            return None

    async def get_events(self, limit: int = 20) -> List[EventData]:
        """Fetch events from Polymarket API"""
        try:
            response = await self.client.get(self.events_endpoint)
            response.raise_for_status()
            data = response.json()

            events = []
            for event in data[:limit]:
                try:
                    # Extract market IDs from markets list
                    markets = event.get("markets", [])
                    market_ids = ",".join([str(m.get("id", "")) for m in markets if m.get("id")])

                    event_data = EventData(
                        id=str(event.get("id", "")),
                        title=event.get("title", ""),
                        description=event.get("description", ""),
                        active=event.get("active", False),
                        markets=market_ids
                    )
                    events.append(event_data)
                except Exception as e:
                    print(f"Error processing event {event.get('id')}: {e}")
                    continue

            return events

        except Exception as e:
            print(f"Error fetching events: {e}")
            return []


    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

class OpenRouterService:
    """
    Service for AI predictions using OpenRouter API

    OpenRouter provides access to multiple AI models including:
    - Anthropic Claude models
    - OpenAI GPT models
    - Google models
    - And many others

    This service dynamically fetches available models and allows selection
    of any supported model for market analysis and predictions.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=60.0
        )
        self._models_cache = {}
        self._default_model = "anthropic/claude-3-haiku"

    async def get_available_models(self) -> List[ModelInfo]:
        """Fetch all available models from OpenRouter"""
        if self._models_cache:
            return list(self._models_cache.values())

        try:
            response = await self.client.get("/models")
            response.raise_for_status()
            data = response.json()

            models = []
            for model_data in data.get("data", []):
                try:
                    model_info = ModelInfo(
                        id=model_data.get("id", ""),
                        name=model_data.get("name", ""),
                        description=model_data.get("description", ""),
                        context_length=model_data.get("context_length", 4096),
                        pricing=model_data.get("pricing", {})
                    )
                    models.append(model_info)
                    self._models_cache[model_data["id"]] = model_info
                except Exception as e:
                    print(f"Error processing model {model_data.get('id')}: {e}")
                    continue

            return models

        except Exception as e:
            print(f"Error fetching models from OpenRouter: {e}")
            return []

    async def predict(self, prompt: str, model_id: str = None) -> dict:
        """Make prediction with specified or default model"""
        if not model_id:
            model_id = self._default_model

        try:
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 1000
            }

            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            if "choices" in data and data["choices"]:
                prediction_text = data["choices"][0]["message"]["content"]
                return {
                    "prediction": prediction_text,
                    "model": model_id,
                    "usage": data.get("usage", {}),
                    "success": True
                }
            else:
                return {
                    "prediction": "Unable to generate prediction",
                    "model": model_id,
                    "error": "No response from model",
                    "success": False
                }

        except Exception as e:
            print(f"Error making prediction with {model_id}: {e}")
            return {
                "prediction": "Error generating prediction",
                "model": model_id,
                "error": str(e),
                "success": False
            }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

class FallbackService:
    """Service providing mock data as fallback when APIs are unavailable"""

    def __init__(self):
        self.mock_markets = [
            {
                "id": "1",
                "question": "Will the Federal Reserve cut interest rates in Q1 2025?",
                "description": "This market resolves to Yes if the Federal Reserve announces an interest rate cut between January 1, 2025 and March 31, 2025.",
                "active": True,
                "volume": 1250000.50,
                "spread": 0.025,
                "outcomes": "['Yes', 'No']",
                "outcome_prices": "['0.65', '0.35']",
                "clob_token_ids": "['12345', '67890']"
            },
            {
                "id": "2",
                "question": "Will SpaceX successfully launch Starship in 2025?",
                "description": "This market resolves to Yes if SpaceX achieves a successful orbital launch of Starship in 2025.",
                "active": True,
                "volume": 890000.75,
                "spread": 0.018,
                "outcomes": "['Yes', 'No']",
                "outcome_prices": "['0.72', '0.28']",
                "clob_token_ids": "['23456', '78901']"
            }
        ]

        self.mock_events = [
            {
                "id": "1",
                "title": "Federal Reserve Policy 2025",
                "description": "Markets related to Federal Reserve monetary policy decisions in 2025",
                "active": True,
                "markets": "1,4,7"
            }
        ]

    async def get_markets(self, limit: int = 20) -> List[MarketData]:
        """Return mock market data"""
        markets = []
        for market in self.mock_markets[:limit]:
            try:
                outcomes = safe_parse_list(market["outcomes"])
                prices = safe_parse_float_list(market["outcome_prices"])

                market_data = MarketData(
                    id=market["id"],
                    question=market["question"],
                    description=market["description"],
                    outcomes=outcomes,
                    prices=prices,
                    volume=market["volume"],
                    spread=market["spread"],
                    active=market["active"],
                    clob_token_ids=market["clob_token_ids"]
                )
                markets.append(market_data)
            except Exception as e:
                print(f"Error processing mock market: {e}")
                continue
        return markets

    async def get_market(self, market_id: str) -> Optional[MarketData]:
        """Return mock market data for specific ID"""
        market = next((m for m in self.mock_markets if m["id"] == market_id), None)
        if not market:
            return None

        try:
            outcomes = safe_parse_list(market["outcomes"])
            prices = safe_parse_float_list(market["outcome_prices"])

            return MarketData(
                id=market["id"],
                question=market["question"],
                description=market["description"],
                outcomes=outcomes,
                prices=prices,
                volume=market["volume"],
                spread=market["spread"],
                active=market["active"],
                clob_token_ids=market["clob_token_ids"]
            )
        except Exception as e:
            print(f"Error processing mock market {market_id}: {e}")
            return None

    async def get_events(self, limit: int = 20) -> List[EventData]:
        """Return mock event data"""
        events = []
        for event in self.mock_events[:limit]:
            try:
                event_data = EventData(
                    id=event["id"],
                    title=event["title"],
                    description=event["description"],
                    active=event["active"],
                    markets=event["markets"]
                )
                events.append(event_data)
            except Exception as e:
                print(f"Error processing mock event: {e}")
                continue
        return events

    async def get_orderbook(self, token_id: str) -> OrderBookData:
        """Return mock orderbook data"""
        return OrderBookData(
            bids=[(0.40, 1000), (0.35, 2500), (0.30, 5000)],
            asks=[(0.60, 1000), (0.65, 2500), (0.70, 5000)]
        )

    async def predict(self, prompt: str, model_id: str = "mock-model") -> dict:
        """Return mock prediction"""
        return {
            "prediction": f"Mock prediction for: {prompt[:50]}...",
            "model": model_id,
            "confidence": 0.5,
            "success": True,
            "mock": True
        }

# Initialize services
polymarket_service = None
openrouter_service = None
fallback_service = FallbackService()

# Initialize Polymarket service
try:
    polymarket_service = PolymarketService()
    print("[SUCCESS] Polymarket service initialized")
except Exception as e:
    print(f"[WARNING] Polymarket service failed: {e}")
    print("Continuing with fallback data")

# Initialize OpenRouter service
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
if openrouter_api_key:
    try:
        openrouter_service = OpenRouterService(openrouter_api_key)
        print("[SUCCESS] OpenRouter service initialized")
    except Exception as e:
        print(f"[WARNING] OpenRouter service failed: {e}")
        print("Continuing with fallback predictions")
else:
    print("[WARNING] OPENROUTER_API_KEY not found - using fallback predictions")

# Legacy OpenAI client for backward compatibility (if needed)
openai_client = None
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    try:
        openai_client = ChatOpenAI(
            model="gpt-3.5-turbo-16k",
            temperature=0,
            openai_api_key=openai_api_key
        )
        print("[SUCCESS] OpenAI client initialized")
    except Exception as e:
        print(f"[WARNING] OpenAI client failed: {e}")

# Mock data for demonstration (replace with real API calls)
MOCK_MARKETS = [
    {
        "id": "1",
        "question": "Will the Federal Reserve cut interest rates in Q1 2025?",
        "description": "This market resolves to Yes if the Federal Reserve announces an interest rate cut between January 1, 2025 and March 31, 2025.",
        "active": True,
        "volume": 1250000.50,
        "spread": 0.025,
        "outcomes": "['Yes', 'No']",
        "outcome_prices": "['0.65', '0.35']",
        "clob_token_ids": "['12345', '67890']"
    },
    {
        "id": "2",
        "question": "Will SpaceX successfully launch Starship in 2025?",
        "description": "This market resolves to Yes if SpaceX achieves a successful orbital launch of Starship in 2025.",
        "active": True,
        "volume": 890000.75,
        "spread": 0.018,
        "outcomes": "['Yes', 'No']",
        "outcome_prices": "['0.72', '0.28']",
        "clob_token_ids": "['23456', '78901']"
    },
    {
        "id": "3",
        "question": "Will Bitcoin reach $200,000 by end of 2025?",
        "description": "This market resolves to Yes if Bitcoin's price reaches or exceeds $200,000 USD by December 31, 2025.",
        "active": True,
        "volume": 2100000.25,
        "spread": 0.032,
        "outcomes": "['Yes', 'No']",
        "outcome_prices": "['0.45', '0.55']",
        "clob_token_ids": "['34567', '89012']"
    }
]

MOCK_EVENTS = [
    {
        "id": "1",
        "title": "Federal Reserve Policy 2025",
        "description": "Markets related to Federal Reserve monetary policy decisions in 2025",
        "active": True,
        "markets": "1,4,7"
    },
    {
        "id": "2",
        "title": "Space & Technology 2025",
        "description": "Markets related to space exploration and technology developments in 2025",
        "active": True,
        "markets": "2,5,8"
    }
]

# API Endpoints

@app.get("/")
async def root():
    """Serve the main web interface"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/models")
async def get_available_models():
    """Get list of available OpenRouter models"""
    if openrouter_service:
        try:
            models = await openrouter_service.get_available_models()
            return {
                "models": [
                    {
                        "id": model.id,
                        "name": model.name,
                        "description": model.description,
                        "context_length": model.context_length,
                        "pricing": model.pricing
                    } for model in models
                ],
                "count": len(models),
                "service": "openrouter"
            }
        except Exception as e:
            print(f"Error fetching models: {e}")

    # Fallback response
    return {
        "models": [
            {
                "id": "anthropic/claude-3-haiku",
                "name": "Claude 3 Haiku",
                "description": "Fast and efficient model by Anthropic",
                "context_length": 200000,
                "pricing": {"prompt": 0.00025, "completion": 0.00125}
            },
            {
                "id": "openai/gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "description": "Fast and cost-effective model by OpenAI",
                "context_length": 16385,
                "pricing": {"prompt": 0.0015, "completion": 0.002}
            }
        ],
        "count": 2,
        "service": "fallback",
        "note": "OpenRouter service not available"
    }

@app.get("/config")
async def get_configuration():
    """Get current application configuration"""
    return {
        "use_real_data": USE_REAL_DATA,
        "fallback_to_mock": FALLBACK_TO_MOCK,
        "default_model": DEFAULT_MODEL,
        "services": {
            "polymarket": polymarket_service is not None,
            "openrouter": openrouter_service is not None,
            "openai": openai_client is not None,
            "fallback": True
        },
        "environment": {
            "openrouter_key": bool(os.getenv("OPENROUTER_API_KEY")),
            "openai_key": bool(os.getenv("OPENAI_API_KEY"))
        },
        "note": "No authentication required for Polymarket Gamma API - market data is publicly available"
    }

@app.get("/markets", response_model=List[MarketResponse])
async def get_markets(limit: int = 20, sort_by: str = "volume", use_real: bool = USE_REAL_DATA):
    """Get available markets from Polymarket or fallback to mock data"""
    # Validate inputs
    if limit < 1 or limit > Config.MAX_MARKETS_LIMIT:
        raise HTTPException(status_code=422, detail=f"Limit must be between 1 and {Config.MAX_MARKETS_LIMIT}")
    
    if sort_by not in ["volume", "spread"]:
        raise HTTPException(status_code=422, detail="sort_by must be 'volume' or 'spread'")
    
    if use_real and polymarket_service:
        try:
            markets_data = await polymarket_service.get_markets(limit * 2)  # Get more to allow sorting

            # Sort markets
            if sort_by == "volume":
                markets_data.sort(key=lambda x: x.volume, reverse=True)
            elif sort_by == "spread":
                markets_data.sort(key=lambda x: x.spread)

            # Convert to response format
            response_markets = []
            for market in markets_data[:limit]:
                response_markets.append(MarketResponse(
                    id=market.id,
                    question=market.question,
                    description=market.description,
                    active=market.active,
                    volume=market.volume,
                    spread=market.spread,
                    outcomes=str(market.outcomes),  # Convert list to string
                    outcome_prices=str(market.prices),
                    clob_token_ids=market.clob_token_ids
                ))
            return response_markets

        except Exception as e:
            logger.error(f"Error fetching real markets: {e}")
            # Check if it's a network connectivity issue
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                raise HTTPException(status_code=503, detail="Market data service temporarily unavailable. Please try again later.")

    # Fallback to mock data
    logger.info("Using fallback market data")
    markets_data = await fallback_service.get_markets(limit)

    # Sort markets
    if sort_by == "volume":
        markets_data.sort(key=lambda x: x.volume, reverse=True)
    elif sort_by == "spread":
        markets_data.sort(key=lambda x: x.spread)

    # Convert to response format
    response_markets = []
    for market in markets_data[:limit]:
        response_markets.append(MarketResponse(
            id=market.id,
            question=market.question,
            description=market.description,
            active=market.active,
            volume=market.volume,
            spread=market.spread,
            outcomes=str(market.outcomes),  # Convert list to string
            outcome_prices=str(market.prices),
            clob_token_ids=market.clob_token_ids
        ))
    return response_markets

@app.get("/events")
async def get_events(limit: int = 20, use_real: bool = USE_REAL_DATA):
    """Get available events from Polymarket or fallback to mock data"""
    if use_real and polymarket_service:
        try:
            events_data = await polymarket_service.get_events(limit)

            # Convert to response format
            response_events = []
            for event in events_data:
                response_events.append({
                    "id": event.id,
                    "title": event.title,
                    "description": event.description,
                    "active": event.active,
                    "markets": event.markets
                })
            return response_events

        except Exception as e:
            print(f"Error fetching real events: {e}")

    # Fallback to mock data
    print("Using fallback event data")
    events_data = await fallback_service.get_events(limit)

    # Convert to response format
    response_events = []
    for event in events_data:
        response_events.append({
            "id": event.id,
            "title": event.title,
            "description": event.description,
            "active": event.active,
            "markets": event.markets
        })
    return response_events

@app.post("/predict", response_model=PredictionResponse)
async def get_prediction(request: PredictionRequest, model: str = None):
    """Get AI prediction for a market using OpenRouter or fallback"""
    try:
        # Create the prediction prompt
        prompt = f"""
        You are a Superforecaster tasked with correctly predicting the likelihood of events.
        Use systematic analysis to develop an accurate prediction for the following market:

        Question: {request.question}
        Description: {request.description}
        Possible Outcomes: {', '.join(request.outcomes)}

        Key analysis steps:
        1. Break down the question into components
        2. Consider relevant factors and historical precedents
        3. Evaluate current market sentiment
        4. Provide probabilistic reasoning

        Give your response in the following format:
        I believe [question] has a likelihood [percentage]% for outcome of [outcome].
        """

        # Try OpenRouter first
        if openrouter_service:
            try:
                result = await openrouter_service.predict(prompt, model)
                if result["success"]:
                    prediction_text = result["prediction"]

                    # Extract confidence (simple parsing)
                    confidence = 0.5
                    try:
                        import re
                        percentages = re.findall(r'(\d+(?:\.\d+)?)%', prediction_text)
                        if percentages:
                            confidence = float(percentages[0]) / 100
                    except:
                        pass

                    return PredictionResponse(
                        prediction=prediction_text,
                        confidence=confidence,
                        reasoning=f"AI analysis using {result['model']}: {request.question}"
                    )
                else:
                    print(f"OpenRouter prediction failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"OpenRouter service error: {e}")

        # Fallback to OpenAI if available
        if openai_client:
            try:
                messages = [HumanMessage(content=prompt)]
                response = openai_client.invoke(messages)
                prediction_text = response.content

                # Extract confidence (simple parsing)
                confidence = 0.5
                try:
                    import re
                    percentages = re.findall(r'(\d+(?:\.\d+)?)%', prediction_text)
                    if percentages:
                        confidence = min(max(float(percentages[0]) / 100, 0.0), 1.0)
                except (ValueError, IndexError):
                    logger.warning("Could not extract confidence from prediction")

                return PredictionResponse(
                    prediction=prediction_text,
                    confidence=confidence,
                    reasoning=f"AI analysis using OpenAI: {request.question}"
                )

            except Exception as e:
                logger.error(f"OpenAI fallback error: {e}")
                # Don't expose internal errors to users
                if "rate limit" in str(e).lower():
                    raise HTTPException(status_code=429, detail="AI service temporarily unavailable due to rate limits. Please try again later.")
                elif "auth" in str(e).lower():
                    raise HTTPException(status_code=503, detail="AI service configuration error. Please contact support.")
                else:
                    logger.error(f"Unexpected OpenAI error: {e}")
                    # Continue to fallback instead of failing

        # Final fallback to mock prediction
        print("Using fallback prediction service")
        result = await fallback_service.predict(prompt, model or "fallback-model")
        return PredictionResponse(
            prediction=result["prediction"],
            confidence=result.get("confidence", 0.5),
            reasoning=f"Fallback analysis: {request.question}"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.post("/news", response_model=List[NewsResponse])
async def get_news(request: NewsRequest):
    """Get relevant news articles (mock data for demo)"""
    # Mock news data - in real implementation, this would call NewsAPI
    mock_news = [
        {
            "title": f"Latest developments related to: {request.keywords}",
            "description": f"Analysis of current trends and market sentiment around {request.keywords}",
            "url": f"https://example.com/news/{request.keywords.replace(' ', '-')}",
            "published_at": datetime.now().isoformat(),
            "source": "Market News Aggregator"
        },
        {
            "title": f"Expert opinions on {request.keywords}",
            "description": f"Industry experts weigh in on the future of {request.keywords}",
            "url": f"https://example.com/experts/{request.keywords.replace(' ', '-')}",
            "published_at": datetime.now().isoformat(),
            "source": "Financial Times"
        }
    ]

    return mock_news[:request.limit]

@app.get("/market/{market_id}")
async def get_market_details(market_id: str):
    """Get detailed information about a specific market"""
    market = next((m for m in MOCK_MARKETS if m["id"] == market_id), None)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    # Mock order book data
    order_book = {
        "market": market_id,
        "bids": [
            {"price": "0.40", "size": "1000"},
            {"price": "0.35", "size": "2500"},
            {"price": "0.30", "size": "5000"}
        ],
        "asks": [
            {"price": "0.60", "size": "1000"},
            {"price": "0.65", "size": "2500"},
            {"price": "0.70", "size": "5000"}
        ]
    }

    return {
        "market": market,
        "order_book": order_book
    }

@app.post("/analyze-market")
async def analyze_market(request: PredictionRequest):
    """Comprehensive market analysis"""
    try:
        # Get market data
        market = next((m for m in MOCK_MARKETS if m["id"] == request.market_id), None)
        if not market:
            raise HTTPException(status_code=404, detail="Market not found")

        # Get AI prediction
        prediction_response = await get_prediction(request)

        # Mock news and analysis
        analysis_result = {
            "market_data": market,
            "ai_prediction": prediction_response.prediction,
            "confidence": prediction_response.confidence,
            "relevant_news": [
                {
                    "title": f"Market Analysis: {market['question'][:50]}...",
                    "url": f"https://example.com/analysis/{market['id']}",
                    "summary": "Comprehensive analysis of market trends and predictions"
                }
            ],
            "order_book_summary": {
                "best_bid": "0.40",
                "best_ask": "0.60",
                "spread": "0.20"
            },
            "analysis_timestamp": datetime.now().isoformat()
        }

        return analysis_result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

# Simple test function
def test_markets_directly():
    """Test markets directly without full app initialization"""
    import asyncio
    import httpx

    async def test():
        print("Testing Polymarket Gamma API directly...")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test with active filter
                params = {"active": "true", "limit": "10"}
                response = await client.get("https://gamma-api.polymarket.com/markets", params=params)
                print(f"Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    print(f"Total markets returned: {len(data)}")

                    if data:
                        print("\nFirst 3 markets:")
                        for i, market in enumerate(data[:3]):
                            print(f"{i+1}. ID: {market.get('id')}")
                            print(f"   Question: {market.get('question', '')[:80]}...")
                            print(f"   Active: {market.get('active')}")
                            print(f"   End Date: {market.get('endDate')}")
                            print(f"   Volume: {market.get('volume')}")
                            print()
                    else:
                        print("No markets returned with active=true filter")

                        # Try without filter
                        print("Trying without active filter...")
                        response2 = await client.get("https://gamma-api.polymarket.com/markets")
                        if response2.status_code == 200:
                            data2 = response2.json()
                            print(f"Total markets without filter: {len(data2)}")

                            if data2:
                                market = data2[0]
                                print(f"First market: {market.get('question', '')[:80]}...")
                                print(f"Active: {market.get('active')}")
                else:
                    print(f"API Error: {response.text}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(test())

if __name__ == "__main__":
    import uvicorn

    print("Starting Polymarket AI Predictions Web App")
    print("Web app will be available at: http://localhost:8000")
    print("API documentation at: http://localhost:8000/docs")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host="0.0.0.0", port=8000)