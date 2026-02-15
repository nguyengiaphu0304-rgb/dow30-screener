import pandas as pd
import numpy as np
from sqlalchemy import create_engine

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("Date").copy()

    # daily return
    df["r1"] = df["Close"].pct_change()

    # momentum
    df["r5"] = df["Close"].pct_change(5)
    df["r20"] = df["Close"].pct_change(20)

    # moving avg distance
    ma20 = df["Close"].rolling(20).mean()
    df["px_ma20"] = df["Close"] / ma20 - 1

    # volatility
    df["vol20"] = df["r1"].rolling(20).std()

    # z-score of 5-day return over ~1 trading year
    mu = df["r5"].rolling(252).mean()
    sigma = df["r5"].rolling(252).std()
    df["z_r5"] = (df["r5"] - mu) / sigma

    # labels: forward 5-day return
    df["fwd_r5"] = df["Close"].shift(-5) / df["Close"] - 1
    df["fwd_up5"] = (df["fwd_r5"] > 0).astype(int)

    return df

def main():
    engine = create_engine("sqlite:///prices.db")
    prices = pd.read_sql("SELECT * FROM prices", engine, parse_dates=["Date"])
    prices = prices.drop_duplicates(subset=["Ticker", "Date"])

    out = []
    for ticker, g in prices.groupby("Ticker"):
        f = add_features(g)
        out.append(f)

    feats = pd.concat(out, ignore_index=True)

    # keep rows where features and labels exist
    feats = feats.dropna(subset=["r5", "r20", "px_ma20", "vol20", "z_r5", "fwd_r5"])

    feats.to_sql("features", engine, if_exists="replace", index=False)
    print("Saved table: features")
    print("Rows:", len(feats))
    print(feats[["Ticker","Date","r5","r20","z_r5","fwd_r5"]].tail(10))

if __name__ == "__main__":
    main()
