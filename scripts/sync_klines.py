#!/usr/bin/env python3
"""
Download CFD kline data from the Gate.io TradFi public API (no API key required).

Examples:
    python scripts/sync_klines.py --symbol XAUUSD --timeframe 5m
    python scripts/sync_klines.py --symbol XAUUSD --timeframe 1h --out data/xauusd_1h.csv
    python scripts/sync_klines.py --symbol EURUSD --timeframe 1d

Valid timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d
(8h / 12h / 3d / 1w / 1M are rejected by the endpoint)
"""
import argparse
import csv
import datetime as dt
import os
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://api.gateio.ws/api/v4/tradfi/symbols/{symbol}/klines"
VALID_TF = {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}
PAGE = 500          # API page size limit
PAUSE = 0.25        # polite rate limit (seconds between requests)


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[502, 503, 504],
                  allowed_methods=["GET"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


def fetch_page(session, symbol, tf, end_time=None):
    params = {"kline_type": tf, "limit": PAGE}
    if end_time:
        params["end_time"] = end_time
    for attempt in range(5):
        try:
            r = session.get(BASE_URL.format(symbol=symbol), params=params, timeout=20)
            return r.status_code, (r.json() if r.status_code == 200 else r.text[:200])
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(1.0 * (attempt + 1))


def sync(symbol: str, tf: str, out_path: str) -> int:
    if tf not in VALID_TF:
        sys.exit(f"Invalid timeframe '{tf}'. Valid: {sorted(VALID_TF)}")

    session = make_session()
    status, data = fetch_page(session, symbol, tf, end_time=int(time.time()))
    if status != 200:
        sys.exit(f"API error HTTP {status}: {data}")

    rows = data.get("data", {}).get("list", [])
    if not rows:
        sys.exit("No data returned.")

    seen, records = set(), []
    def collect(batch):
        for b in batch:
            t = int(b["t"])
            if t not in seen:
                seen.add(t)
                ts = dt.datetime.fromtimestamp(t, dt.timezone.utc)
                records.append([t, ts.strftime("%Y-%m-%d %H:%M:%S"),
                                b["o"], b["h"], b["l"], b["c"]])

    collect(rows)
    end_time = int(rows[0]["t"]) - 1
    batches = 1

    while True:
        time.sleep(PAUSE)
        status, data = fetch_page(session, symbol, tf, end_time=end_time)
        if status != 200:
            break
        batch = data.get("data", {}).get("list", [])
        if not batch:
            break
        collect(batch)
        batches += 1
        new_end = int(batch[0]["t"]) - 1
        if new_end == end_time or len(batch) < PAGE:
            break
        end_time = new_end
        if batches % 50 == 0:
            print(f"  ... batch {batches}, {len(records)} bars")

    records.sort(key=lambda x: x[0])
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "datetime_utc", "open", "high", "low", "close"])
        w.writerows(records)

    print(f"[OK] {symbol} {tf}: {len(records)} bars "
          f"({records[0][1]} ~ {records[-1][1]} UTC, {batches} batches) -> {out_path}")
    return len(records)


def main():
    ap = argparse.ArgumentParser(description="Gate.io TradFi kline downloader")
    ap.add_argument("--symbol", default="XAUUSD", help="e.g. XAUUSD, EURUSD, XAGUSD")
    ap.add_argument("--timeframe", default="5m", help="1m/5m/15m/30m/1h/4h/1d")
    ap.add_argument("--out", default=None, help="output CSV path")
    args = ap.parse_args()

    out = args.out or os.path.join("data", f"{args.symbol.lower()}_{args.timeframe}.csv")
    sync(args.symbol, args.timeframe, out)


if __name__ == "__main__":
    main()
