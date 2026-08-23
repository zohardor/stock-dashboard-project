"""
סקריפט סקרינר מניות עצמאי - רץ דרך GitHub Action.

קריטריונים:
1. מניה אמריקאית
2. ווליום ממוצע (20 יום) מעל 2 מיליון
3. SMA20 חצה כלפי מעלה את SMA50 (crossover, לא רק "מעל")
4. מחיר מעל SMA200
5. מחיר בטווח 10% מתחת לשיא 52 שבועות
6. RSI(14) מתחת ל-60

התוצאות נכתבות לטבלת screener_results ב-Supabase (מוחק ומחליף את סריקת היום הקודמת).
"""

import os
import sys
import time
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import yfinance as yf
import pandas as pd

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

NASDAQ_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
SP500_LIST_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"

MIN_AVG_VOLUME = 2_000_000
MAX_PCT_BELOW_52W_HIGH = 10.0  # אחוזים
RSI_MAX = 60
CROSSOVER_LOOKBACK_DAYS = 3  # "חצה כלפי מעלה" בטווח כמה ימי מסחר אחרונים, לא רק היום ממש
MAX_WORKERS = 12  # הרצה מקבילית כדי לעמוד בזמן סביר על אלפי טיקרים


def get_universe():
    """מחזיר רשימת טיקרים לסריקה: כל הנאסד"ק + NYSE/AMEX (ללא קרנות/ETF)."""
    try:
        tickers = set()

        nas = pd.read_csv(NASDAQ_LISTED_URL, sep="|")
        nas = nas[nas["Test Issue"] == "N"]
        if "ETF" in nas.columns:
            nas = nas[nas["ETF"] == "N"]
        tickers.update(nas["Symbol"].dropna().tolist())

        other = pd.read_csv(OTHER_LISTED_URL, sep="|")
        other = other[other["Test Issue"] == "N"]
        if "ETF" in other.columns:
            other = other[other["ETF"] == "N"]
        sym_col = "ACT Symbol" if "ACT Symbol" in other.columns else "Symbol"
        tickers.update(other[sym_col].dropna().tolist())

        tickers = {t.replace(".", "-") for t in tickers if isinstance(t, str) and t.strip() and "$" not in t}
        tickers = sorted(tickers)
        if len(tickers) > 200:
            return tickers
        raise ValueError("universe too small, falling back")
    except Exception as e:
        print(f"Failed to fetch full market list ({e}), falling back to S&P 500", file=sys.stderr)
        try:
            df = pd.read_csv(SP500_LIST_URL)
            return df["Symbol"].str.replace(".", "-", regex=False).tolist()
        except Exception as e2:
            print(f"Failed to fetch S&P 500 list too: {e2}", file=sys.stderr)
            return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def evaluate_ticker(ticker: str):
    try:
        hist = yf.Ticker(ticker).history(period="15mo", interval="1d")
        if hist.empty or len(hist) < 210:
            return None

        close = hist["Close"]
        volume = hist["Volume"]

        sma20 = close.rolling(20).mean()
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean()
        rsi = compute_rsi(close, 14)
        avg_vol_20 = volume.rolling(20).mean()
        high_52w = close.rolling(252, min_periods=100).max()

        last_price = close.iloc[-1]
        last_sma20 = sma20.iloc[-1]
        last_sma50 = sma50.iloc[-1]
        last_sma200 = sma200.iloc[-1]
        last_rsi = rsi.iloc[-1]
        last_avg_vol = avg_vol_20.iloc[-1]
        last_high = high_52w.iloc[-1]

        prev_sma20 = sma20.iloc[-2]
        prev_sma50 = sma50.iloc[-2]

        if any(pd.isna(v) for v in [last_price, last_sma20, last_sma50, last_sma200,
                                     last_rsi, last_avg_vol, last_high, prev_sma20, prev_sma50]):
            return None

        pct_from_high = ((last_high - last_price) / last_high) * 100

        # crossover: SMA20 מעל SMA50 עכשיו, וב-CROSSOVER_LOOKBACK_DAYS האחרונים היה מתחת בשלב כלשהו
        # (ולא רק אתמול-להיום, כדי להתאים יותר להתנהגות סקרינרים כמו Finviz)
        recent20 = sma20.iloc[-(CROSSOVER_LOOKBACK_DAYS + 1):]
        recent50 = sma50.iloc[-(CROSSOVER_LOOKBACK_DAYS + 1):]
        was_below = (recent20.iloc[:-1] <= recent50.iloc[:-1]).any()
        crossed_up = was_below and (last_sma20 > last_sma50)

        conditions = [
            last_avg_vol >= MIN_AVG_VOLUME,
            crossed_up,
            last_price > last_sma200,
            pct_from_high <= MAX_PCT_BELOW_52W_HIGH,
            last_rsi < RSI_MAX,
        ]

        if all(conditions):
            return {
                "ticker": ticker,
                "price": round(float(last_price), 2),
                "sma20": round(float(last_sma20), 2),
                "sma50": round(float(last_sma50), 2),
                "sma200": round(float(last_sma200), 2),
                "rsi14": round(float(last_rsi), 2),
                "avg_volume_20": int(last_avg_vol),
                "pct_from_52w_high": round(float(pct_from_high), 2),
                "scan_date": date.today().isoformat(),
            }
        return None

    except Exception as e:
        print(f"Error on {ticker}: {e}", file=sys.stderr)
        return None


def push_to_supabase(results):
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }

    # מוחקים את תוצאות היום (אם רץ פעמיים) לפני כתיבה מחדש
    today = date.today().isoformat()
    requests.delete(
        f"{SUPABASE_URL}/rest/v1/screener_results?scan_date=eq.{today}",
        headers=headers,
    )

    if not results:
        print("No matching tickers today.")
        return

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/screener_results",
        headers=headers,
        json=results,
    )
    res.raise_for_status()
    print(f"Pushed {len(results)} tickers to Supabase.")


def main():
    universe = get_universe()
    print(f"Scanning {len(universe)} tickers...")

    matches = []
    done = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(evaluate_ticker, t): t for t in universe}
        for future in as_completed(futures):
            ticker = futures[future]
            done += 1
            try:
                result = future.result()
            except Exception as e:
                print(f"Error on {ticker}: {e}", file=sys.stderr)
                result = None
            if result:
                matches.append(result)
                print(f"  MATCH: {ticker}")
            if done % 200 == 0:
                print(f"  ...{done}/{len(universe)}")

    print(f"Found {len(matches)} matching tickers.")
    push_to_supabase(matches)


if __name__ == "__main__":
    main()
