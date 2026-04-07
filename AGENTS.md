# Agents Development Guide

## Cursor Cloud specific instructions

### Project overview

Polymarket Agents is a Python CLI/agent framework for autonomous AI trading on Polymarket prediction markets. It is a single Python application (no microservices, no database servers). See `README.md` for full architecture details.

### Python environment

- The repo targets Python 3.9 but works on Python 3.12 with the current `requirements.txt`.
- A virtualenv lives at `.venv`. Activate with `source .venv/bin/activate`.
- `setuptools<81` must be installed for `pkg_resources` (needed by `web3`). The update script handles this.
- Always set `PYTHONPATH="."` when running any script outside Docker so that `agents.*` imports resolve.

### Running tests

```
source .venv/bin/activate
PYTHONPATH="." python -m pytest tests/test.py -v
```

The test file is named `test.py` (not `test_*.py`), so pass the explicit path to pytest.

### Linting

The project uses Black via pre-commit. Run `black --check .` to verify formatting.

### Running the FastAPI dev server

```
source .venv/bin/activate
PYTHONPATH="." uvicorn scripts.python.server:app --host 0.0.0.0 --port 8000
```

This is a stub server with placeholder endpoints (`/`, `/items/{id}`, `/trades/{id}`, `/markets/{id}`).

### Running the CLI

```
source .venv/bin/activate
PYTHONPATH="." python scripts/python/cli.py --help
```

Most CLI commands (e.g. `get-all-markets`) require a valid `POLYGON_WALLET_PRIVATE_KEY` in `.env` because the `Polymarket()` class initializes the CLOB client at construction time.

### Gamma API (no credentials needed)

The `GammaMarketClient` in `agents/polymarket/gamma.py` can fetch market data without any API keys:

```python
from agents.polymarket.gamma import GammaMarketClient
gamma = GammaMarketClient()
markets = gamma.get_all_markets(limit=5)
```

### Environment variables

Copy `.env.example` to `.env`. At minimum `OPENAI_API_KEY` and `POLYGON_WALLET_PRIVATE_KEY` are needed for full functionality. The Gamma API works without any keys.
