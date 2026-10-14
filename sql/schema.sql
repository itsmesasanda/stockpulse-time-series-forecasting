
CREATE TABLE IF NOT EXISTS stocks (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_prices (
    ticker VARCHAR(10) NOT NULL
        REFERENCES stocks(ticker),

    trading_date DATE NOT NULL,

    open_price DOUBLE PRECISION NOT NULL,
    high_price DOUBLE PRECISION NOT NULL,
    low_price DOUBLE PRECISION NOT NULL,
    close_price DOUBLE PRECISION NOT NULL,
    adjusted_close DOUBLE PRECISION,

    volume BIGINT NOT NULL,
    dividends DOUBLE PRECISION DEFAULT 0,
    stock_splits DOUBLE PRECISION DEFAULT 0,

    ingested_at TIMESTAMPTZ NOT NULL,

    PRIMARY KEY (ticker, trading_date),

    CONSTRAINT valid_prices CHECK (
        open_price > 0
        AND high_price > 0
        AND low_price > 0
        AND close_price > 0
        AND high_price >= low_price
        AND high_price >= GREATEST(open_price, close_price)
        AND low_price <= LEAST(open_price, close_price)
        AND volume >= 0
    )
);

INSERT INTO stocks (ticker, company_name)
VALUES
    ('AAPL', 'Apple'),
    ('MSFT', 'Microsoft'),
    ('NVDA', 'NVIDIA'),
    ('GOOGL', 'Alphabet'),
    ('AMZN', 'Amazon')
ON CONFLICT (ticker) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_stock_prices_date
ON stock_prices(trading_date);
