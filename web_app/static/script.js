// Polymarket AI Predictions - Frontend JavaScript

// API Configuration
const API_BASE_URL = window.location.origin.includes('localhost')
    ? 'http://localhost:8000'
    : window.location.origin;

// Global variables
let allMarkets = [];
let allEvents = [];

// DOM Content Loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Load initial data
    loadMarkets();
    loadEvents();

    // Set up form handlers
    setupFormHandlers();

    console.log('🚀 Polymarket AI Predictions App Initialized');
}

// Tab Navigation
function showTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));

    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Show selected tab
    const selectedTab = document.getElementById(tabName + '-tab');
    if (selectedTab) {
        selectedTab.classList.add('active');
    }

    // Add active class to clicked button
    const clickedButton = document.querySelector(`[onclick="showTab('${tabName}')"]`);
    if (clickedButton) {
        clickedButton.classList.add('active');
    }

    // Load tab-specific data
    if (tabName === 'predictions') {
        populateMarketSelect();
    } else if (tabName === 'analysis') {
        populateAnalysisMarketSelect();
    }
}

// API Helper Functions
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showError(`Failed to connect to server: ${error.message}`);
        throw error;
    }
}

// Loading States
function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const spinnerText = overlay.querySelector('p');
    spinnerText.textContent = message;
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'none';
}

// Error Handling
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;

    // Remove existing errors
    const existingErrors = document.querySelectorAll('.error');
    existingErrors.forEach(error => error.remove());

    // Add new error to the top of the active tab
    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
        activeTab.insertBefore(errorDiv, activeTab.firstChild);
    }

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

function showSuccess(message) {
    const successDiv = document.createElement('div');
    successDiv.className = 'success';
    successDiv.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;

    const activeTab = document.querySelector('.tab-content.active');
    if (activeTab) {
        activeTab.insertBefore(successDiv, activeTab.firstChild);
    }

    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.remove();
        }
    }, 3000);
}

// Markets Functions
async function loadMarkets() {
    try {
        showLoading('Loading markets...');

        const sortBy = document.getElementById('sort-select').value;
        const limit = document.getElementById('limit-input').value;

        const markets = await apiRequest(`/markets?sort_by=${sortBy}&limit=${limit}`);
        allMarkets = markets;

        displayMarkets(markets);
        showSuccess(`Loaded ${markets.length} markets`);

    } catch (error) {
        console.error('Failed to load markets:', error);
        showError('Failed to load markets. Please try again.');
    } finally {
        hideLoading();
    }
}

function displayMarkets(markets) {
    const container = document.getElementById('markets-container');

    if (markets.length === 0) {
        container.innerHTML = '<div class="loading">No markets found</div>';
        return;
    }

    const marketsHTML = markets.map(market => `
        <div class="market-card" onclick="selectMarket('${market.id}')">
            <h3>${market.question}</h3>
            <p>${market.description.substring(0, 150)}...</p>
            <div class="market-stats">
                <div class="stat">
                    <div class="stat-value">${market.spread ? market.spread.toFixed(3) : 'N/A'}</div>
                    <div class="stat-label">Spread</div>
                </div>
                <div class="stat">
                    <div class="stat-value">${market.volume ? market.volume.toLocaleString() : 'N/A'}</div>
                    <div class="stat-label">Volume</div>
                </div>
                <div class="stat">
                    <div class="stat-value">${market.active ? 'Active' : 'Inactive'}</div>
                    <div class="stat-label">Status</div>
                </div>
            </div>
        </div>
    `).join('');

    container.innerHTML = marketsHTML;
}

function selectMarket(marketId) {
    // Find the market
    const market = allMarkets.find(m => m.id === parseInt(marketId));
    if (!market) return;

    // Switch to predictions tab
    showTab('predictions');

    // Populate the prediction form
    document.getElementById('prediction-question').value = market.question;
    document.getElementById('prediction-description').value = market.description;

    // Parse outcomes
    const outcomes = market.outcomes.replace(/[\[\]']/g, '').split(', ');
    const outcomeInputs = document.querySelectorAll('.outcome-input');
    outcomes.forEach((outcome, index) => {
        if (outcomeInputs[index]) {
            outcomeInputs[index].value = outcome.trim();
        }
    });

    showSuccess('Market selected for AI prediction');
}

// Events Functions
async function loadEvents() {
    try {
        const events = await apiRequest('/events?limit=50');
        allEvents = events;
    } catch (error) {
        console.error('Failed to load events:', error);
    }
}

// Prediction Functions
function populateMarketSelect() {
    const select = document.getElementById('market-select');
    select.innerHTML = '<option value="">Choose a market...</option>';

    allMarkets.forEach(market => {
        const option = document.createElement('option');
        option.value = market.id;
        option.textContent = market.question.substring(0, 80) + '...';
        select.appendChild(option);
    });
}

function populatePredictionForm() {
    const select = document.getElementById('market-select');
    const marketId = select.value;

    if (!marketId) return;

    const market = allMarkets.find(m => m.id === parseInt(marketId));
    if (!market) return;

    document.getElementById('prediction-question').value = market.question;
    document.getElementById('prediction-description').value = market.description;

    // Parse outcomes
    const outcomes = market.outcomes.replace(/[\[\]']/g, '').split(', ');
    const outcomeInputs = document.querySelectorAll('.outcome-input');
    outcomes.forEach((outcome, index) => {
        if (outcomeInputs[index]) {
            outcomeInputs[index].value = outcome.trim();
        }
    });
}

function addOutcome() {
    const container = document.getElementById('outcomes-container');
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'outcome-input';
    input.placeholder = `Outcome ${container.querySelectorAll('.outcome-input').length + 1}`;

    // Insert before the add button
    const addButton = container.querySelector('.add-outcome-btn');
    container.insertBefore(input, addButton);
}

async function getPrediction() {
    const question = document.getElementById('prediction-question').value.trim();
    const description = document.getElementById('prediction-description').value.trim();
    const outcomeInputs = document.querySelectorAll('.outcome-input');
    const outcomes = Array.from(outcomeInputs)
        .map(input => input.value.trim())
        .filter(outcome => outcome.length > 0);

    if (!question || !description || outcomes.length < 2) {
        showError('Please fill in the question, description, and at least 2 outcomes');
        return;
    }

    try {
        showLoading('Getting AI prediction...');

        const predictionData = {
            market_id: document.getElementById('market-select').value || 'unknown',
            question: question,
            description: description,
            outcomes: outcomes
        };

        const result = await apiRequest('/predict', {
            method: 'POST',
            body: JSON.stringify(predictionData)
        });

        displayPrediction(result);

    } catch (error) {
        console.error('Prediction failed:', error);
        showError('Failed to get AI prediction. Please try again.');
    } finally {
        hideLoading();
    }
}

function displayPrediction(result) {
    const resultDiv = document.getElementById('prediction-result');
    const contentDiv = resultDiv.querySelector('.prediction-content');

    contentDiv.innerHTML = `
        <div style="margin-bottom: 15px;">
            <strong>AI Prediction:</strong><br>
            ${result.prediction}
        </div>
        <div style="margin-bottom: 15px;">
            <strong>Confidence Level:</strong>
            <span style="color: ${result.confidence > 0.7 ? '#10b981' : result.confidence > 0.5 ? '#f59e0b' : '#ef4444'}; font-weight: bold;">
                ${(result.confidence * 100).toFixed(1)}%
            </span>
        </div>
        <div>
            <strong>Reasoning:</strong><br>
            ${result.reasoning}
        </div>
    `;

    resultDiv.style.display = 'block';
    resultDiv.scrollIntoView({ behavior: 'smooth' });

    showSuccess('AI prediction generated successfully!');
}

// News Functions
async function searchNews() {
    const keywords = document.getElementById('news-keywords').value.trim();

    if (!keywords) {
        showError('Please enter keywords to search for news');
        return;
    }

    try {
        showLoading('Searching news...');

        const newsData = {
            keywords: keywords,
            limit: 10
        };

        const news = await apiRequest('/news', {
            method: 'POST',
            body: JSON.stringify(newsData)
        });

        displayNews(news);

    } catch (error) {
        console.error('News search failed:', error);
        showError('Failed to search news. Please try again.');
    } finally {
        hideLoading();
    }
}

function displayNews(news) {
    const container = document.getElementById('news-container');

    if (news.length === 0) {
        container.innerHTML = `
            <div class="news-placeholder">
                <i class="fas fa-search"></i>
                <p>No news articles found for your search</p>
            </div>
        `;
        return;
    }

    const newsHTML = news.map(article => `
        <div class="news-item">
            <h4>${article.title}</h4>
            <p>${article.description || 'No description available'}</p>
            <div class="news-meta">
                <span><i class="fas fa-newspaper"></i> ${article.source}</span>
                <span><i class="fas fa-calendar"></i> ${new Date(article.published_at).toLocaleDateString()}</span>
                ${article.url ? `<a href="${article.url}" target="_blank" class="news-link">Read More <i class="fas fa-external-link-alt"></i></a>` : ''}
            </div>
        </div>
    `).join('');

    container.innerHTML = newsHTML;
    showSuccess(`Found ${news.length} news articles`);
}

// Deep Analysis Functions
function populateAnalysisMarketSelect() {
    const select = document.getElementById('analysis-market-select');
    select.innerHTML = '<option value="">Choose a market...</option>';

    allMarkets.forEach(market => {
        const option = document.createElement('option');
        option.value = market.id;
        option.textContent = market.question.substring(0, 80) + '...';
        select.appendChild(option);
    });
}

async function performDeepAnalysis() {
    const marketId = document.getElementById('analysis-market-select').value;

    if (!marketId) {
        showError('Please select a market for analysis');
        return;
    }

    const market = allMarkets.find(m => m.id === parseInt(marketId));
    if (!market) {
        showError('Selected market not found');
        return;
    }

    try {
        showLoading('Performing deep analysis...');

        const analysisData = {
            market_id: marketId,
            question: market.question,
            description: market.description,
            outcomes: market.outcomes.replace(/[\[\]']/g, '').split(', ')
        };

        const result = await apiRequest('/analyze-market', {
            method: 'POST',
            body: JSON.stringify(analysisData)
        });

        displayAnalysis(result);

    } catch (error) {
        console.error('Deep analysis failed:', error);
        showError('Failed to perform deep analysis. Please try again.');
    } finally {
        hideLoading();
    }
}

function displayAnalysis(result) {
    const resultDiv = document.getElementById('analysis-result');
    const contentDiv = resultDiv.querySelector('.analysis-content');

    contentDiv.innerHTML = `
        <div style="margin-bottom: 20px;">
            <h4>Market Data</h4>
            <p><strong>Question:</strong> ${result.market_data.question}</p>
            <p><strong>Description:</strong> ${result.market_data.description}</p>
        </div>

        <div style="margin-bottom: 20px;">
            <h4>AI Prediction</h4>
            <p>${result.ai_prediction}</p>
        </div>

        ${result.relevant_news && result.relevant_news.length > 0 ? `
        <div style="margin-bottom: 20px;">
            <h4>Related News (${result.relevant_news.length} articles)</h4>
            <ul>
                ${result.relevant_news.map(article =>
                    `<li><a href="${article.url}" target="_blank">${article.title}</a></li>`
                ).join('')}
            </ul>
        </div>
        ` : ''}

        <div style="margin-bottom: 20px;">
            <h4>Order Book Summary</h4>
            <pre style="background: #f8fafc; padding: 10px; border-radius: 4px; overflow-x: auto;">${JSON.stringify(result.order_book, null, 2)}</pre>
        </div>
    `;

    resultDiv.style.display = 'block';
    resultDiv.scrollIntoView({ behavior: 'smooth' });

    showSuccess('Deep analysis completed!');
}

// Form Setup
function setupFormHandlers() {
    // Allow Enter key to submit forms
    document.getElementById('news-keywords').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchNews();
        }
    });

    // Auto-resize textareas
    const textareas = document.querySelectorAll('textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
}

// Utility Functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatTime(dateString) {
    return new Date(dateString).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Export functions for global access
window.showTab = showTab;
window.loadMarkets = loadMarkets;
window.selectMarket = selectMarket;
window.getPrediction = getPrediction;
window.addOutcome = addOutcome;
window.searchNews = searchNews;
window.performDeepAnalysis = performDeepAnalysis;