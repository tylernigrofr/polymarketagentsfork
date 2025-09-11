# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in the web_app directory.

## Development Setup

The web_app is a lightweight FastAPI-based web interface that provides AI-powered market analysis using only the Polymarket Gamma API.

### Prerequisites
- Python 3.9+
- OpenAI or OpenRouter API key for AI predictions
- Optional: NewsAPI and Tavily API keys for enhanced features

### Installation
```bash
cd web_app/
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## Common Commands

### Quick Start
```bash
python main.py          # Start the web app
python run.py           # Setup assistant and launcher
```

### Development Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing
```bash
python test_api.py      # Test Polymarket Gamma API connectivity
```

### API Documentation
Visit `http://localhost:8000/docs` when server is running for interactive OpenAPI documentation.

## Architecture Overview

### Simplified Architecture

The web_app uses a self-contained implementation with the Polymarket Gamma API:
- Minimal dependencies (no blockchain/CLOB libraries required)
- Read-only market data access via Gamma API
- No authentication required for market data
- Ideal for analysis and predictions without trading complexity

### Core Components

**Backend API (`main.py`)**
- FastAPI application with CORS middleware
- RESTful endpoints for markets, events, predictions, and news
- Pydantic models for request/response validation
- Background task support for long-running operations

**Frontend (`static/`)**
- `index.html` - Single-page application with tabbed interface
- `style.css` - Modern responsive CSS with dark theme
- `script.js` - Vanilla JavaScript for API interactions and UI logic

**Utilities**
- `run.py` - Setup checker and development launcher
- `test_api.py` - Gamma API connectivity testing
- `setup.py` - Environment setup utilities

### API Endpoints

**Market Data**
- `GET /markets` - Retrieve available markets with filtering
- `GET /events` - Retrieve events data
- `GET /market/{market_id}` - Get specific market details

**AI Features**
- `POST /predict` - Generate AI predictions for markets
- `POST /news` - Search relevant news articles
- `POST /analyze-market` - Comprehensive market analysis

**Frontend**
- `GET /` - Serve main web interface
- `GET /style.css` - CSS stylesheet
- `GET /script.js` - JavaScript application

### Key Data Models

**Market Representation**
- `MarketResponse` - API response format for market data
- `EventResponse` - Event data structure
- `PredictionRequest/Response` - AI prediction interfaces

**Configuration Models**
- Environment variables via `.env` file
- API client configurations for external services
- CORS and middleware settings

### External Integrations

**Polymarket Gamma API**
- No authentication required for market data
- Used in both deployment modes
- Provides real-time market and event information

**AI Services**
- OpenAI API for predictions and analysis
- Optional OpenRouter API as alternative
- LangChain integration for prompt management

**Optional Services**
- NewsAPI for news article retrieval
- Tavily API for web search functionality
- ChromaDB for vector storage (full mode only)

### Frontend Architecture

**Tabbed Interface**
- Markets: Browse and filter market data
- AI Predictions: Generate market outcome predictions
- News: Search and analyze relevant articles  
- Deep Analysis: Comprehensive multi-source analysis

**Responsive Design**
- Mobile-first CSS approach
- Font Awesome icons for UI elements
- Dark theme with modern styling
- Progressive enhancement for features

### Development Workflow

1. **Environment Setup**: Use `run.py` to check dependencies and create `.env`
2. **API Testing**: Run `test_api.py` to verify Gamma API connectivity
3. **Development**: Start server with `python main.py` or uvicorn
4. **Frontend**: Modify `static/` files for UI changes
5. **Backend**: Extend FastAPI endpoints for new functionality

### Configuration

**Required Environment Variables (choose one or both)**
- `OPENAI_API_KEY` - For AI predictions
- `OPENROUTER_API_KEY` - Alternative AI provider

**Optional Variables**  
- `TAVILY_API_KEY` - Web search functionality
- `NEWSAPI_API_KEY` - News article retrieval

**Application Settings**
- `ENVIRONMENT` - development/production
- `DEBUG` - Enable debug logging
- `USE_REAL_DATA` - Use live vs. mock data
- `DEFAULT_MODEL` - AI model selection