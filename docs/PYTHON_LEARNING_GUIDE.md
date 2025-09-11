# Python Learning Guide for AI Development Managers

## Using Polymarket Agents as Real-World Examples

This guide teaches Python fundamentals using the Polymarket Agents repository as practical examples. Perfect for managers who want to effectively collaborate with AI coding assistants.

---

## Table of Contents
1. [Python Fundamentals](#python-fundamentals)
2. [Code Organization & Structure](#code-organization--structure)
3. [Error Handling Patterns](#error-handling-patterns)
4. [Configuration & Environment Management](#configuration--environment-management)
5. [Testing Approaches](#testing-approaches)
6. [DevOps with AI](#devops-with-ai)
7. [Writing Effective AI Specifications](#writing-effective-ai-specifications)
8. [Best Practices for AI-Assisted Development](#best-practices-for-ai-assisted-development)

---

## Python Fundamentals

### Variables, Data Types, and Basic Operations

**Example from Polymarket Agents:**

```python
# From agents/application/executor.py
import os
import json
import ast
import re
from typing import List, Dict, Any

import math

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
```

**Key Concepts:**
- **Import statements**: Bring in external libraries and modules
- **Type hints**: `List`, `Dict`, `Any` help AI understand expected data types
- **Constants**: Variables that don't change (often in ALL_CAPS)

### Functions and Methods

**Example from the Trading Class:**

```python
class Trader:
    def __init__(self):
        self.polymarket = Polymarket()
        self.gamma = Gamma()
        self.agent = Agent()

    def one_best_trade(self) -> None:
        """
        one_best_trade is a strategy that evaluates all events, markets, and orderbooks
        leverages all available information sources accessible to the autonomous agent
        then executes that trade without any human intervention
        """
        try:
            self.pre_trade_logic()
            # ... trading logic
        except Exception as e:
            print(f"Error {e} \n \n Retrying")
            self.one_best_trade()
```

**Key Concepts:**
- **Instance methods**: Functions that belong to a class
- **Docstrings**: Multi-line comments explaining what functions do
- **Self parameter**: References the current instance of the class
- **Return type hints**: `-> None` indicates no return value

### Classes and Object-Oriented Programming

**Example Class Structure:**

```python
class Executor:
    def __init__(self, default_model='gpt-3.5-turbo-16k') -> None:
        load_dotenv()
        max_token_model = {'gpt-3.5-turbo-16k':15000, 'gpt-4-1106-preview':95000}
        self.token_limit = max_token_model.get(default_model)
        self.prompter = Prompter()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.llm = ChatOpenAI(
            model=default_model,
            temperature=0,
        )
```

**Key Concepts:**
- **Constructor**: `__init__` method initializes the object
- **Instance variables**: `self.token_limit`, `self.llm`
- **Encapsulation**: Data and methods bundled together

---

## Code Organization & Structure

### Modular Architecture

**Polymarket Agents Structure:**
```
agents/
├── application/     # Business logic layer
│   ├── trade.py    # Main trading strategies
│   ├── executor.py # AI/LLM interactions
│   └── prompts.py  # AI prompt templates
├── connectors/      # External service integrations
│   ├── chroma.py   # Vector database for RAG
│   ├── news.py     # News API integration
│   └── search.py   # Web search capabilities
├── polymarket/     # Core API integrations
│   ├── polymarket.py # Main API client
│   └── gamma.py    # Gamma API client
└── utils/          # Shared utilities
    ├── objects.py  # Data models
    └── utils.py    # Helper functions
```

**Key Principles:**
- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Injection**: Classes receive dependencies rather than creating them
- **Interface Segregation**: Small, focused interfaces

### Import Patterns

**Absolute Imports:**
```python
from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.connectors.chroma import PolymarketRAG as Chroma
```

**Relative Imports:**
```python
from .objects import SimpleEvent, SimpleMarket
from ..utils.objects import SimpleMarket
```

---

## Error Handling Patterns

### Try-Except Blocks

**Example from Trading Logic:**

```python
def one_best_trade(self) -> None:
    try:
        self.pre_trade_logic()
        events = self.polymarket.get_all_tradeable_events()
        # ... complex trading logic
    except Exception as e:
        print(f"Error {e} \n \n Retrying")
        self.one_best_trade()  # Recursive retry
```

**Common Patterns:**
- **Broad Exception Handling**: `except Exception as e`
- **Specific Exceptions**: `except ValueError`, `except ConnectionError`
- **Finally Blocks**: Code that always runs
- **Context Managers**: `with` statements for resource management

### Graceful Degradation

```python
def get_market_data(self, market_id: str):
    try:
        return self.api_client.get_market(market_id)
    except ConnectionError:
        logger.warning("API unavailable, using cached data")
        return self.get_cached_market_data(market_id)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None
```

---

## Configuration & Environment Management

### Environment Variables

**`.env` File Structure:**
```bash
POLYGON_WALLET_PRIVATE_KEY=""
OPENAI_API_KEY=""
TAVILY_API_KEY=""
NEWSAPI_API_KEY=""
```

**Loading Configuration:**
```python
from dotenv import load_dotenv
import os

class Config:
    def __init__(self):
        load_dotenv()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.wallet_key = os.getenv("POLYGON_WALLET_PRIVATE_KEY")

    @property
    def is_production(self) -> bool:
        return os.getenv("ENVIRONMENT") == "production"
```

### Configuration Classes

```python
@dataclass
class TradingConfig:
    max_position_size: float = 0.1  # 10% of portfolio
    min_liquidity: int = 10000     # Minimum market liquidity
    risk_tolerance: str = "medium"  # low, medium, high
    strategy_type: str = "conservative"
```

---

## Testing Approaches

### Unit Testing Structure

**Example Test File:**
```python
import pytest
from unittest.mock import Mock, patch
from agents.application.trade import Trader

class TestTrader:
    def setup_method(self):
        self.trader = Trader()

    def test_pre_trade_logic(self):
        """Test that pre-trade setup works correctly"""
        self.trader.pre_trade_logic()
        # Assert that local databases are cleared

    @patch('agents.polymarket.polymarket.Polymarket.get_all_tradeable_events')
    def test_one_best_trade_success(self, mock_get_events):
        """Test successful trade execution"""
        mock_events = [Mock()]  # Mock event objects
        mock_get_events.return_value = mock_events

        self.trader.one_best_trade()

        # Assert that trade was attempted
        # Assert that proper cleanup occurred
```

### Mocking External Dependencies

```python
@patch('agents.connectors.chroma.PolymarketRAG')
@patch('agents.polymarket.gamma.GammaMarketClient')
def test_with_mocked_dependencies(self, mock_gamma, mock_chroma):
    # Configure mock behavior
    mock_gamma.get_current_events.return_value = []
    mock_chroma.events.return_value = []

    trader = Trader()
    result = trader.one_best_trade()

    # Assert expected behavior
```

---

## DevOps with AI

### Docker Configuration

**Dockerfile Example:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set environment variables
ENV PYTHONPATH="."
ENV ENVIRONMENT="production"

CMD ["python", "scripts/python/cli.py", "run-autonomous-trader"]
```

### CI/CD Pipeline

**GitHub Actions Example:**
```yaml
name: CI/CD Pipeline

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: pip install -r requirements.txt
    - name: Run tests
      run: pytest tests/
    - name: Build Docker image
      run: docker build -t polymarket-agents .
```

### Environment Management

**Development vs Production:**
```python
class EnvironmentManager:
    @staticmethod
    def get_database_config():
        if os.getenv("ENVIRONMENT") == "production":
            return ProductionDatabaseConfig()
        else:
            return DevelopmentDatabaseConfig()

    @staticmethod
    def get_ai_model():
        if os.getenv("ENVIRONMENT") == "production":
            return "gpt-4"  # More expensive but better
        else:
            return "gpt-3.5-turbo"  # Faster for development
```

---

## Writing Effective AI Specifications

### Clear Task Definition

**❌ Bad Specification:**
"Add error handling to the trading function"

**✅ Good Specification:**
"Add comprehensive error handling to the `one_best_trade()` method in `agents/application/trade.py`:

**Requirements:**
1. Handle network timeouts when calling Polymarket API
2. Handle insufficient balance errors
3. Handle invalid market data responses
4. Implement exponential backoff for retries (max 3 attempts)
5. Log all errors with appropriate severity levels
6. Return graceful fallback values when possible

**Acceptance Criteria:**
- Function should not crash on any error condition
- All errors should be logged with context
- Function should retry failed operations appropriately
- Return type should be consistent regardless of error state"

### Context and Examples

**Providing Context:**
```python
# Current implementation
def one_best_trade(self) -> None:
    events = self.polymarket.get_all_tradeable_events()
    # ... rest of implementation

# Expected behavior
def one_best_trade(self) -> Optional[TradeResult]:
    """Execute one profitable trade with error handling"""
```

**Including Examples:**
```python
# Example usage after implementation
trader = Trader()
try:
    result = trader.one_best_trade()
    if result:
        print(f"Trade executed: {result}")
    else:
        print("No suitable trade found")
except Exception as e:
    print(f"Trading failed: {e}")
```

### Breaking Down Complex Tasks

**Instead of:** "Implement a complete trading strategy"

**Use:** "Implement trading strategy in phases:

**Phase 1: Data Collection**
- Create method to fetch market data
- Add data validation
- Handle API rate limits

**Phase 2: Analysis Engine**
- Implement market filtering logic
- Add risk assessment
- Create position sizing algorithm

**Phase 3: Execution Layer**
- Add order placement logic
- Implement trade confirmation
- Add position monitoring"

---

## Best Practices for AI-Assisted Development

### Quality Assurance Checklist

**Before Merging AI-Generated Code:**

```python
# ✅ Code Review Checklist
def review_ai_code(code):
    checks = {
        "error_handling": has_try_except_blocks(code),
        "type_hints": has_type_annotations(code),
        "documentation": has_docstrings(code),
        "tests": has_corresponding_tests(code),
        "edge_cases": handles_edge_cases(code),
        "performance": no_obvious_performance_issues(code),
        "security": no_security_vulnerabilities(code)
    }
    return all(checks.values())
```

### Iterative Development Process

**1. Spec Phase:**
```python
# Write detailed specification
spec = {
    "task": "Add user authentication",
    "requirements": ["JWT tokens", "password hashing", "role-based access"],
    "constraints": ["Use existing user model", "Maintain API compatibility"],
    "examples": ["Login flow", "Protected endpoint access"]
}
```

**2. Implementation Phase:**
```python
# AI generates initial implementation
# You review and provide feedback
# AI iterates based on your feedback
```

**3. Testing Phase:**
```python
# AI generates tests
# You add integration tests
# Manual testing for edge cases
```

### Debugging AI-Generated Code

**Common Issues and Solutions:**

```python
# Issue: AI missed edge case
def fix_edge_case():
    # Original AI code
    if user_input:
        process(user_input)

    # Fixed version
    if user_input and isinstance(user_input, str) and len(user_input.strip()) > 0:
        process(user_input.strip())
    else:
        raise ValueError("Invalid input")

# Issue: AI used wrong library
def fix_import_issues():
    # AI might suggest
    import requests

    # But project uses
    import httpx  # As specified in requirements.txt

# Issue: AI ignored existing patterns
def fix_consistency():
    # AI might create
    def new_function(self):
        pass

    # Should match existing pattern
    def new_function(self) -> None:
        """Docstring describing function"""
        pass
```

### Documentation Standards

**For AI Collaboration:**

```python
class DocumentedClass:
    """
    Class for handling trading operations.

    This class provides methods for:
    - Executing trades on Polymarket
    - Managing trading positions
    - Risk assessment and position sizing

    Attributes:
        max_position_size (float): Maximum position size as % of portfolio
        risk_tolerance (str): Risk level (low/medium/high)

    Example:
        trader = Trader()
        trader.execute_trade(market_id, amount)
    """

    def execute_trade(self, market_id: str, amount: float) -> Optional[TradeResult]:
        """
        Execute a trade on the specified market.

        Args:
            market_id: Unique identifier for the market
            amount: Trade amount in USDC

        Returns:
            TradeResult if successful, None if failed

        Raises:
            InsufficientFundsError: If wallet balance is insufficient
            MarketUnavailableError: If market is not tradable

        Example:
            result = trader.execute_trade("0x123...", 100.0)
            if result:
                print(f"Trade successful: {result.tx_hash}")
        """
        pass
```

### Managing AI Development Workflow

**Project Management for AI Teams:**

```python
class AIDevelopmentManager:
    def __init__(self):
        self.tasks = []
        self.completed = []

    def create_task_spec(self, description: str) -> dict:
        """Create detailed specification for AI"""
        return {
            "description": description,
            "context": self.get_project_context(),
            "constraints": self.get_project_constraints(),
            "examples": self.get_similar_examples(),
            "acceptance_criteria": self.define_acceptance_criteria()
        }

    def review_ai_output(self, code: str, spec: dict) -> list:
        """Review AI-generated code against specification"""
        issues = []
        if not self.meets_acceptance_criteria(code, spec):
            issues.append("Does not meet acceptance criteria")
        if not self.follows_project_patterns(code):
            issues.append("Does not follow project conventions")
        return issues

    def iterate_with_ai(self, code: str, feedback: str) -> str:
        """Send feedback to AI for iteration"""
        improved_spec = {
            "original_code": code,
            "feedback": feedback,
            "additional_requirements": self.get_additional_requirements()
        }
        return improved_spec
```

---

## Key Takeaways for AI Development Managers

### Your Role in AI-Assisted Development:

1. **Spec Writer**: Craft clear, detailed requirements
2. **Quality Gate**: Review and test AI-generated code
3. **Architecture Guide**: Ensure consistency with system design
4. **Integration Expert**: Handle complex interdependencies

### Essential Skills:

- **Technical Writing**: Clear specification writing
- **Code Review**: Identifying issues in AI-generated code
- **System Architecture**: Understanding how components fit together
- **Testing Strategy**: Ensuring reliability of AI-generated features

### Best Practices:

- **Break Down Tasks**: Complex features → smaller, verifiable tasks
- **Provide Context**: Include examples, constraints, and acceptance criteria
- **Iterate Collaboratively**: Use AI for initial implementation, you for refinement
- **Maintain Standards**: Ensure AI follows your project's conventions
- **Document Everything**: Clear docs enable future AI-assisted maintenance

### Quality Assurance:

- **Review Checklists**: Systematic evaluation of AI-generated code
- **Testing Requirements**: Comprehensive test coverage
- **Edge Case Handling**: Consider failure scenarios
- **Performance Monitoring**: Ensure efficiency and scalability

Remember: AI is a powerful coding assistant, but you provide the vision, quality control, and strategic direction that ensures the final product meets your requirements and maintains high standards.