# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

This repository requires Python 3.9. To set up the development environment:

1. Create and activate virtual environment:
   ```bash
   virtualenv --python=python3.9 .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables by copying `.env.example` to `.env` and adding:
   - `POLYGON_WALLET_PRIVATE_KEY=""` (for trading functionality)
   - `OPENAI_API_KEY=""` (for LLM features)
   - `TAVILY_API_KEY=""` (for web search)
   - `NEWSAPI_API_KEY=""` (for news data)

4. Set PYTHONPATH when running outside docker:
   ```bash
   export PYTHONPATH="."
   ```

## Common Commands

### CLI Interface
The primary user interface is the CLI tool:
```bash
python scripts/python/cli.py <command> [options]
```

Key CLI commands:
- `get-all-markets --limit 5 --sort-by spread` - Retrieve markets sorted by spread
- `get-all-events --limit 5 --sort-by number_of_markets` - Retrieve events
- `get-relevant-news "keywords"` - Query news articles

### Trading
Direct trading execution:
```bash
python agents/application/trade.py
```

### Testing
Run the basic test suite:
```bash
python tests/test.py
```

### Code Quality
Pre-commit hooks are configured with Black formatter:
```bash
pre-commit install
```

### Docker
Development with Docker:
```bash
./scripts/bash/build-docker.sh
./scripts/bash/run-docker-dev.sh
```

## Architecture Overview

### Core Components

**agents/application/** - Main application logic
- `trade.py` - Entry point for autonomous trading, implements `Trader` class with `one_best_trade()` strategy
- `executor.py` - Core `Executor` class for market analysis and trade execution logic
- `creator.py` - Agent creation utilities
- `prompts.py` - LLM prompt templates and management

**agents/polymarket/** - Polymarket API integration
- `polymarket.py` - Main `Polymarket` class for API interactions, market data, and trade execution
- `gamma.py` - `GammaMarketClient` for Gamma API integration and market metadata

**agents/connectors/** - External data sources
- `chroma.py` - Vector database integration (`PolymarketRAG`) for news and data vectorization
- `news.py` - NewsAPI integration for relevant article retrieval
- `search.py` - Web search functionality

**agents/utils/** - Shared utilities
- `objects.py` - Pydantic data models for markets, events, trades
- `utils.py` - Common utility functions

### Key Workflows

1. **Market Analysis Flow**: `Trader.one_best_trade()` → get events → filter with RAG → map to markets → analyze → execute
2. **Data Pipeline**: External APIs → Chroma vectorization → LLM analysis → trading decisions
3. **CLI Commands**: Direct API queries for markets, events, and news with customizable filters

### Data Models
The codebase uses Pydantic models in `objects.py` for type-safe representations of:
- Markets and market metadata
- Events and event data  
- Trade orders and execution data
- API responses

### External Dependencies
- **LangChain**: For LLM orchestration and RAG implementation
- **Chroma**: Vector database for semantic search
- **py-clob-client**: Polymarket trading client
- **FastAPI**: Web framework (in `scripts/python/server.py`)
- **Typer**: CLI framework for user commands