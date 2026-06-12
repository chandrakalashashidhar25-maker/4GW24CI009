# Stock Analyzer — Divide & Conquer

A self-contained Python web app that finds the optimal stock buy/sell window using the **Divide & Conquer** algorithm, with a rich interactive output page.

## Features

- Deterministic 30-day price generation from any ticker symbol (no API keys needed)
- Divide & Conquer max-profit algorithm with O(n log n) complexity
- Step-by-step **SPLIT** and **MERGE** cards with winner highlighting
- Interactive chart with hover tooltips and permanent **Buy/Sell callout boxes**
- Complexity comparison: D&C vs Brute Force
- Tabbed source code viewer (backend, home page, output page)

## How to Run

```bash
python app.py
```

Then open: [http://127.0.0.1:5000](http://127.0.0.1:5000)

The browser opens automatically.

## Files

| File | Purpose |
|------|---------|
| `app.py` | HTTP server + D&C algorithm + price generator |
| `index.html` | Ticker input landing page |
| `result.html` | Output page: chart, steps, complexity, code viewer |
| `requirements.txt` | No external packages needed |
| `README.md` | This file |

## Algorithm

The Divide & Conquer approach:
1. **Split** the price array at midpoint
2. Recursively find best trade in **left half**
3. Recursively find best trade in **right half**
4. Find best **cross-boundary** trade (buy in left, sell in right)
5. **Merge** — return the maximum of the three

**Time Complexity:** O(n log n)  
**Space Complexity:** O(log n) stack depth

## Sample Tickers

Try: `AAPL`, `TSLA`, `MSFT`, `INFY`, `AMZN`, `NVDA`

Each ticker produces consistent, reproducible results since prices are seeded from the ticker string.
