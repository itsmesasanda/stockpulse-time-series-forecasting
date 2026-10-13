
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]
OUTPUT_DIR = Path("data/raw")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COLUMN_NAMES = {
    "Date": "date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividends",
    "Stock Splits": "stock_splits",
}


def fetch_stock_prices(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Download historical stock prices for a ticker."""
    df = yf.Ticker(ticker).history(
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=True,
    )

    if df.empty:
        raise ValueError(f"No data returned for {ticker}")

    df = df.reset_index()
    df = df.rename(columns=COLUMN_NAMES)

    df["date"] = pd.to_datetime(df["date"], utc=True).dt.date
    df["ticker"] = ticker
    df["ingested_at"] = datetime.now(timezone.utc)

    df = df.drop_duplicates(subset=["ticker", "date"])
    df = df.sort_values("date").reset_index(drop=True)

    return df


def validate_prices(df: pd.DataFrame) -> None:
    """Check basic data quality before storage."""
    required = [
        "ticker", "date", "open", "high",
        "low", "close", "volume"
    ]

    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if df[required].isnull().any().any():
        raise ValueError("Required fields contain null values")

    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("Invalid non-positive stock prices")

    if (df["volume"] < 0).any():
        raise ValueError("Invalid negative trading volume")

    if (df["high"] < df["low"]).any():
        raise ValueError("High price is below low price")


def save_raw_data(df: pd.DataFrame, ticker: str) -> Path:
    """Persist an initial extract as a Parquet file."""
    output_path = OUTPUT_DIR / f"{ticker}.parquet"
    df.to_parquet(output_path, index=False)
    return output_path


def main():
    for ticker in TICKERS:
        try:
            print(f"\nFetching {ticker}...")

            df = fetch_stock_prices(ticker)
            validate_prices(df)
            output_path = save_raw_data(df, ticker)

            print(f"Rows: {len(df)}")
            print(f"Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"Saved: {output_path}")

        except Exception as error:
            print(f"FAILED: {ticker} - {error}")


if __name__ == "__main__":
    main()
