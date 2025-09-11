# Polymarket AI Predictions Web App

A lightweight web interface that provides AI-powered market analysis and prediction capabilities using the Polymarket Gamma API.

## Features

- 📊 **Market Dashboard**: Browse and filter Polymarket data
- 🤖 **AI Predictions**: Get AI-powered predictions for market outcomes
- 📰 **News Integration**: Search and analyze relevant news articles
- 🔍 **Deep Analysis**: Comprehensive market analysis with multiple data sources
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### Prerequisites
- Python 3.9+
- OpenAI or OpenRouter API key for AI predictions
- Optional: NewsAPI and Tavily API keys for enhanced features

### Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. **Run the web app:**
```bash
python main.py
```

4. **Open your browser:**
```
http://localhost:8000
```

## API Endpoints

### Markets
- `GET /markets` - Get available markets
- `GET /events` - Get available events
- `GET /market/{market_id}` - Get market details

### AI Features
- `POST /predict` - Get AI prediction for a market
- `POST /news` - Search for relevant news
- `POST /analyze-market` - Comprehensive market analysis

## Project Structure

```
web_app/
├── main.py              # FastAPI backend server (Gamma API only)
├── run.py               # Setup checker and launcher
├── test_api.py          # API connectivity testing
├── static/
│   ├── index.html       # Main web interface
│   ├── style.css        # Modern CSS styling
│   └── script.js        # Frontend JavaScript
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md           # This file
```

## Usage Guide

### 1. Browse Markets
- Use the **Markets** tab to explore available Polymarket data
- Filter by volume, spread, or other criteria
- Click on any market to analyze it further

### 2. Get AI Predictions
- Switch to the **AI Predictions** tab
- Select a market or fill in the details manually
- Add possible outcomes (Yes/No, etc.)
- Click "Get AI Prediction" to receive analysis

### 3. Research with News
- Use the **News** tab to search for relevant articles
- Enter keywords related to your market of interest
- Review news sentiment and context

### 4. Deep Analysis
- The **Deep Analysis** tab provides comprehensive insights
- Combines AI predictions, news, and order book data
- Get the complete picture before making decisions

## Configuration

### Environment Variables
```bash
# Required (choose one or both)
OPENAI_API_KEY=your_openai_key
OPENROUTER_API_KEY=your_openrouter_key

# Optional
TAVILY_API_KEY=your_search_key
NEWSAPI_API_KEY=your_news_key

# Application settings
ENVIRONMENT=development
DEBUG=true
USE_REAL_DATA=true
DEFAULT_MODEL=anthropic/claude-3-haiku
```

### Customization
- Modify `static/style.css` for visual changes
- Update `static/script.js` for new features
- Extend `main.py` to add new API endpoints

## Development

### Running in Development Mode
```bash
# Install additional dev dependencies
pip install uvicorn[standard]

# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
When running, visit `http://localhost:8000/docs` for interactive API documentation.

## Deployment

### Docker Deployment
```bash
# Build the image
docker build -t polymarket-web .

# Run the container
docker run -p 8000:8000 polymarket-web
```

### Production Deployment
- Set `ENVIRONMENT=production` in your environment
- Use a production WSGI server like Gunicorn
- Set up proper CORS origins
- Configure SSL/TLS certificates

## Security Notes

- Never commit API keys to version control
- Use environment variables for sensitive data
- Implement proper authentication for production use
- Validate all user inputs on both frontend and backend

## Troubleshooting

### Common Issues

1. **"Failed to connect to server"**
   - Ensure the FastAPI server is running on port 8000
   - Check that CORS is properly configured

2. **"API key not found"**
   - Verify your `.env` file contains the required API keys
   - Restart the server after adding new environment variables

3. **"No markets found"**
   - Check your internet connection to access Gamma API
   - Gamma API requires no authentication for market data

### Debug Mode
```bash
# Run with debug logging
uvicorn main:app --reload --log-level debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project inherits the MIT License from the parent Polymarket Agents repository.