
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf
from sqlalchemy import text

from src.database.load_prices import engine, UPSERT_SQL
from src.ingestion.fetch_prices import (
    TICKERS,
    COLUMN_NAMES,
    validate_prices,
)


def get_latest_date(ticker):
    query = text("""
        SELECT MAX(trading_date)
        FROM stock_prices
        WHERE ticker = :ticker
    """)

    with engine.connect() as conn:
        return conn.execute(
            query, {"ticker": ticker}
        ).scalar()


def fetch_incremental_prices(ticker, latest_date):
    if latest_date is None:
        start_date = datetime.now(timezone.utc).date() - timedelta(days=365 * 5 + 7)
    else:
        start_date = latest_date - timedelta(days=7)

    end_date = datetime.now(timezone.utc).date() + timedelta(days=1)

    df = yf.Ticker(ticker).history(
        start=start_date.isoformat(),
        end=end_date.isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=True,
    )

    if df.empty:
        return pd.DataFrame()

    df = df.reset_index().rename(columns=COLUMN_NAMES)

    df["date"] = pd.to_datetime(
        df["date"], utc=True
    ).dt.date

    df["ticker"] = ticker
    df["ingested_at"] = datetime.now(timezone.utc)

    df = df.drop_duplicates(
        subset=["ticker", "date"],
        keep="last"
    )

    return df


def upsert_prices(df):
    if df.empty:
        return 0

    validate_prices(df)

    df = df.rename(columns={
        "date": "trading_date",
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
        "adj_close": "adjusted_close",
    })

    columns = [
        "ticker", "trading_date",
        "open_price", "high_price", "low_price",
        "close_price", "adjusted_close",
        "volume", "dividends", "stock_splits",
        "ingested_at",
    ]

    records = (
        df[columns]
        .astype(object)
        .where(pd.notna(df[columns]), None)
        .to_dict(orient="records")
    )

    with engine.begin() as conn:
        for i in range(0, len(records), 500):
            conn.execute(UPSERT_SQL, records[i:i + 500])

    return len(records)


def main():
    failed = []

    for ticker in TICKERS:
        try:
            latest_date = get_latest_date(ticker)

            print(f"\nProcessing {ticker}")
            print(f"Latest stored date: {latest_date}")

            df = fetch_incremental_prices(ticker, latest_date)

            if df.empty:
                print("No records returned")
                continue

            count = upsert_prices(df)
            print(f"Successfully processed {count} records")

        except Exception as exc:
            failed.append(ticker)
            print(f"FAILED {ticker}: {exc}")

    if failed:
        raise RuntimeError(
            f"Incremental pipeline failed for: {', '.join(failed)}"
        )

    print("\nIncremental pipeline completed")


if __name__ == "__main__":
    main()
