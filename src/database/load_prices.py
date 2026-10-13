import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv()

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "5433")),
    database=os.getenv("DB_NAME"),
)

engine = create_engine(database_url)

DATA_DIR = Path("data/raw")

UPSERT_SQL = text("""
    INSERT INTO stock_prices (
        ticker, trading_date, open_price, high_price,
        low_price, close_price, adjusted_close,
        volume, dividends, stock_splits, ingested_at
    )
    VALUES (
        :ticker, :trading_date, :open_price, :high_price,
        :low_price, :close_price, :adjusted_close,
        :volume, :dividends, :stock_splits, :ingested_at
    )
    ON CONFLICT (ticker, trading_date)
    DO UPDATE SET
        open_price = EXCLUDED.open_price,
        high_price = EXCLUDED.high_price,
        low_price = EXCLUDED.low_price,
        close_price = EXCLUDED.close_price,
        adjusted_close = EXCLUDED.adjusted_close,
        volume = EXCLUDED.volume,
        dividends = EXCLUDED.dividends,
        stock_splits = EXCLUDED.stock_splits,
        ingested_at = EXCLUDED.ingested_at;
""")


def load_prices(file_path):
    df = pd.read_parquet(file_path)

    df = df.rename(columns={
        "date": "trading_date",
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
        "adj_close": "adjusted_close",
    })

    df["trading_date"] = pd.to_datetime(
        df["trading_date"]
    ).dt.date

    df = df.drop_duplicates(
        subset=["ticker", "trading_date"],
        keep="last"
    )

    columns = [
        "ticker", "trading_date",
        "open_price", "high_price", "low_price",
        "close_price", "adjusted_close",
        "volume", "dividends", "stock_splits",
        "ingested_at"
    ]

    records = (
        df[columns]
        .astype(object)
        .where(pd.notna(df[columns]), None)
        .to_dict(orient="records")
    )

    with engine.begin() as connection:
        for start in range(0, len(records), 500):
            connection.execute(
                UPSERT_SQL,
                records[start:start + 500]
            )

    print(f"Loaded {len(records)} rows from {file_path.name}")


def main():
    files = sorted(DATA_DIR.glob("*.parquet"))

    if not files:
        raise FileNotFoundError(
            "No Parquet files found in data/raw/"
        )

    for file_path in files:
        load_prices(file_path)


if __name__ == "__main__":
    main()
