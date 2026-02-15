import pandas as pd
import numpy as np
from sqlalchemy import create_engine

TOP_K = 5

def daily_topk(feats, score_col, filt_mask):
    tmp = feats[filt_mask].sort_values(["Date", score_col], ascending=[True, False])
    picks = tmp.groupby("Date").head(TOP_K).copy()
    return picks

def summarize(name, df):
    if df.empty:
        return pd.DataFrame([{
            "strategy": name, "days": 0, "mean_excess_5d": np.nan, "hit_rate_excess": np.nan
        }]), pd.DataFrame()

    daily = df.groupby("Date").agg(
        mean_excess_5d=("excess_fwd_r5", "mean"),
        hit_rate_excess=("excess_up5", "mean"),
        n_picks=("Ticker", "count")
    ).reset_index()

    return pd.DataFrame([{
        "strategy": name,
        "days": len(daily),
        "avg_picks_per_day": daily["n_picks"].mean(),
        "mean_excess_5d": daily["mean_excess_5d"].mean(),
        "hit_rate_excess": daily["hit_rate_excess"].mean(),
    }]), daily

def main():
    engine = create_engine("sqlite:///prices.db")
    feats = pd.read_sql("SELECT * FROM features", engine, parse_dates=["Date"])

    # need SPY for benchmark
    spy = pd.read_sql("SELECT Date, Close FROM prices WHERE Ticker='SPY'", engine, parse_dates=["Date"])
    
    if spy.empty:
        print("SPY data not found in database. Using first ticker as proxy benchmark.")
        spy = pd.read_sql("SELECT DISTINCT Ticker FROM prices LIMIT 1", engine)
        ticker = spy.iloc[0, 0]
        spy = pd.read_sql(f"SELECT Date, Close FROM prices WHERE Ticker='{ticker}'", engine, parse_dates=["Date"])
    
    spy = spy.sort_values("Date").copy()
    spy["spy_fwd_r5"] = spy["Close"].shift(-5) / spy["Close"] - 1
    spy = spy.dropna(subset=["spy_fwd_r5"])

    feats["score_meanrev"] = -feats["z_r5"]
    feats["score_momo"] = feats["r20"]

    # merge SPY forward return onto each row by date
    feats = feats.merge(spy[["Date", "spy_fwd_r5"]], on="Date", how="inner")

    feats["excess_fwd_r5"] = feats["fwd_r5"] - feats["spy_fwd_r5"]
    feats["excess_up5"] = (feats["excess_fwd_r5"] > 0).astype(int)

    # FILTERS
    meanrev_filter = (feats["z_r5"] <= -1.5)
    momo_filter = (feats["r20"] >= 0.10) & (feats["px_ma20"] > 0)

    meanrev_picks = daily_topk(feats, "score_meanrev", meanrev_filter)
    momo_picks = daily_topk(feats, "score_momo", momo_filter)

    meanrev_summary, meanrev_daily = summarize("meanrev_filtered", meanrev_picks)
    momo_summary, momo_daily = summarize("momo_filtered", momo_picks)

    out_summary = pd.concat([meanrev_summary, momo_summary], ignore_index=True)

    print("\n=== EXCESS RETURN SUMMARY (vs Benchmark, filtered, Top 5/day max) ===")
    print(out_summary)

    meanrev_daily.to_csv("bt_meanrev_excess_filtered_daily.csv", index=False)
    momo_daily.to_csv("bt_momo_excess_filtered_daily.csv", index=False)
    out_summary.to_csv("bt_excess_filtered_summary.csv", index=False)

    print("\nSaved: bt_excess_filtered_summary.csv and daily files")

if __name__ == "__main__":
    main()
