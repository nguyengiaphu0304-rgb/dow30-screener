import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine

def main():
    engine = create_engine("sqlite:///prices.db")

    df = yf.download("SPY", start="2015-01-01", interval="1d", auto_adjust=False, progress=False)
    
    # Flatten MultiIndex columns
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    
    df = df.reset_index()
    df["Ticker"] = "SPY"
    df = df[["Ticker","Date","Open","High","Low","Close","Volume"]]

    # tránh trùng nếu chạy lại
    existing = pd.read_sql("SELECT Date FROM prices WHERE Ticker='SPY'", engine, parse_dates=["Date"])
    if not existing.empty:
        df = df[~df["Date"].isin(existing["Date"])]

    df.to_sql("prices", engine, if_exists="append", index=False)
    print("Inserted SPY rows:", len(df))

if __name__ == "__main__":
    main()
