import pandas as pd
import numpy as np
from sqlalchemy import create_engine

TOP_K = 5
R20_GRID = [0.05, 0.10, 0.15]
PXMA_GRID = [0.00, 0.02, 0.05]

def to_monday_group(date_series: pd.Series) -> pd.Series:
    return date_series.dt.to_period("W-MON").astype(str)

def weekly_summary(feats: pd.DataFrame, filt_mask: pd.Series, name: str):
    tmp = feats[filt_mask].copy()
    if tmp.empty:
        return None

    tmp["week"] = to_monday_group(tmp["Date"])
    first_day = tmp.groupby("week")["Date"].transform("min")
    candidates = tmp[tmp["Date"] == first_day].copy()

    picks = (
        candidates.sort_values(["week", "score_momo"], ascending=[True, False])
                  .groupby("week")
                  .head(TOP_K)
                  .copy()
    )

    weekly = picks.groupby("week").agg(
        mean_excess_5d=("excess_fwd_r5", "mean"),
        hit_rate_excess=("excess_up5", "mean"),
        n_picks=("Ticker", "count"),
    ).reset_index()

    return {
        "name": name,
        "weeks": len(weekly),
        "avg_picks_per_week": weekly["n_picks"].mean(),
        "mean_excess_5d": weekly["mean_excess_5d"].mean(),
        "hit_rate_excess": weekly["hit_rate_excess"].mean(),
    }

def main():
    engine = create_engine("sqlite:///prices.db")
    feats = pd.read_sql("SELECT * FROM features", engine, parse_dates=["Date"])
    prices = pd.read_sql("SELECT Ticker, Date, Close FROM prices", engine, parse_dates=["Date"])

    spy = prices[prices["Ticker"] == "SPY"].sort_values("Date").copy()
    spy["spy_fwd_r5"] = spy["Close"].shift(-5) / spy["Close"] - 1
    spy = spy.dropna(subset=["spy_fwd_r5"])

    feats["score_momo"] = feats["r20"]
    feats = feats.merge(spy[["Date", "spy_fwd_r5"]], on="Date", how="inner")
    feats["excess_fwd_r5"] = feats["fwd_r5"] - feats["spy_fwd_r5"]
    feats["excess_up5"] = (feats["excess_fwd_r5"] > 0).astype(int)

    results = []
    for r20_th in R20_GRID:
        for px_th in PXMA_GRID:
            filt = (feats["r20"] >= r20_th) & (feats["px_ma20"] >= px_th)
            name = f"r20>={r20_th:.2f}, px_ma20>={px_th:.2f}"
            s = weekly_summary(feats, filt, name)
            if s is not None:
                results.append(s)

    out = pd.DataFrame(results)
    out = out.sort_values("mean_excess_5d", ascending=False).reset_index(drop=True)

    print("\n=== MOMENTUM THRESHOLD TUNING (weekly, excess vs SPY) ===")
    print(out)

    out.to_csv("tune_momentum_results.csv", index=False)
    print("\nSaved: tune_momentum_results.csv")

if __name__ == "__main__":
    main()
