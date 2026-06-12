from __future__ import annotations

import random
import re
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse
import json
import threading
import webbrowser

ROOT = Path(__file__).parent


def clean_ticker(value: str) -> str:
    ticker = re.sub(r"[^A-Za-z0-9.-]", "", value or "").upper()
    return ticker[:12] or "DEMO"


def make_prices_for_ticker(ticker: str, days: int = 30) -> list[int]:
    """Create repeatable demo prices from a ticker symbol."""
    seed = sum((index + 1) * ord(char) for index, char in enumerate(ticker))
    rng = random.Random(seed)
    price = rng.randint(70, 160)
    prices = []

    for day in range(days):
        trend = 1 if day > days // 3 else -1
        move = rng.randint(-9, 12) + trend * rng.randint(0, 3)
        price = max(25, price + move)
        prices.append(price)

    return prices


def max_profit_divide_conquer(prices: list[int]) -> dict:
    steps = []

    def solve(low: int, high: int, depth: int = 0) -> tuple[int, int, int]:
        if low >= high:
            return 0, low, low

        mid = (low + high) // 2
        steps.append({
            "low": low,
            "high": high,
            "mid": mid,
            "depth": depth,
            "action": "split",
            "description": f"Split days {low+1}–{high+1} at midpoint day {mid+1}"
        })

        left_profit, left_buy, left_sell = solve(low, mid, depth + 1)
        right_profit, right_buy, right_sell = solve(mid + 1, high, depth + 1)

        min_left = min(range(low, mid + 1), key=lambda index: prices[index])
        max_right = max(range(mid + 1, high + 1), key=lambda index: prices[index])
        cross_profit = prices[max_right] - prices[min_left]

        steps.append({
            "low": low,
            "high": high,
            "mid": mid,
            "depth": depth,
            "action": "merge",
            "left_profit": left_profit,
            "right_profit": right_profit,
            "cross_profit": cross_profit,
            "cross_buy": min_left,
            "cross_sell": max_right,
            "winner": "cross" if cross_profit >= left_profit and cross_profit >= right_profit
                      else ("left" if left_profit >= right_profit else "right"),
            "description": (
                f"Merge days {low+1}–{high+1}: "
                f"Left=Rs.{left_profit}, Right=Rs.{right_profit}, Cross=Rs.{cross_profit} "
                f"→ {'Cross wins! Buy D'+str(min_left+1)+' sell D'+str(max_right+1) if cross_profit>=left_profit and cross_profit>=right_profit else ('Left wins' if left_profit>=right_profit else 'Right wins')}"
            )
        })

        if cross_profit >= left_profit and cross_profit >= right_profit:
            return cross_profit, min_left, max_right
        if left_profit >= right_profit:
            return left_profit, left_buy, left_sell
        return right_profit, right_buy, right_sell

    profit, buy_day, sell_day = solve(0, len(prices) - 1)
    return {
        "profit": profit,
        "buy_day": buy_day,
        "sell_day": sell_day,
        "buy_price": prices[buy_day],
        "sell_price": prices[sell_day],
        "steps": steps,
        "step_count": len(steps),
    }


def describe_result(ticker: str, prices: list[int], result: dict) -> str:
    return (
        f"{ticker} analyzed via Divide & Conquer. The array is recursively halved — "
        f"each half finds its best trade, then the algorithm checks the cross-boundary trade "
        f"(buy in left half, sell in right). Best action: buy on Day {result['buy_day'] + 1} "
        f"at Rs.{result['buy_price']}, sell on Day {result['sell_day'] + 1} at "
        f"Rs.{result['sell_price']} → profit Rs.{result['profit']}. "
        f"Algorithm made {result['step_count']} recursive steps (O(n log n))."
    )


def analyze_ticker(ticker: str) -> dict:
    ticker = clean_ticker(ticker)
    prices = make_prices_for_ticker(ticker)
    result = max_profit_divide_conquer(prices)
    return {
        "ticker": ticker,
        "prices": prices,
        "description": describe_result(ticker, prices, result),
        **result,
    }


def analyze_prices(data: dict) -> tuple[dict, int]:
    prices = data.get("prices", [])
    ticker = clean_ticker(data.get("ticker", "CUSTOM"))

    if len(prices) < 2:
        return {"error": "Need at least 2 prices"}, 400
    if not all(isinstance(price, (int, float)) for price in prices):
        return {"error": "Prices must be numbers"}, 400

    prices = [int(price) for price in prices]
    result = max_profit_divide_conquer(prices)
    return {
        "ticker": ticker,
        "prices": prices,
        "description": describe_result(ticker, prices, result),
        **result,
    }, 200


def get_source(name: str) -> tuple[dict, int]:
    allowed = {
        "backend": "app.py",
        "home": "index.html",
        "output": "result.html",
    }
    filename = allowed.get(name)
    if not filename:
        return {"error": "Unknown source file"}, 404

    path = ROOT / filename
    return {"name": filename, "code": path.read_text(encoding="utf-8")}, 200


class StockRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self.send_file("index.html", "text/html; charset=utf-8")
            return

        if path == "/output":
            self.send_file("result.html", "text/html; charset=utf-8")
            return

        if path.startswith("/api/analyze/"):
            ticker = unquote(path.rsplit("/", 1)[-1])
            self.send_json(analyze_ticker(ticker))
            return

        if path == "/generate":
            ticker = clean_ticker((query.get("ticker") or ["DEMO"])[0])
            self.send_json({"ticker": ticker, "prices": make_prices_for_ticker(ticker)})
            return

        if path.startswith("/api/source/"):
            key = unquote(path.rsplit("/", 1)[-1])
            payload, status = get_source(key)
            self.send_json(payload, status)
            return

        self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if urlparse(self.path).path != "/analyze":
            self.send_json({"error": "Not found"}, 404)
            return

        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        response, status = analyze_prices(payload)
        self.send_json(response, status)

    def send_file(self, filename: str, content_type: str):
        path = ROOT / filename
        if not path.exists():
            self.send_json({"error": "File not found"}, 404)
            return

        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, payload: dict, status: int = 200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 5000), StockRequestHandler)
    url = "http://127.0.0.1:5000"
    print(f"Stock Analyzer running at {url}")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStock Analyzer stopped.")
    finally:
        server.server_close()
