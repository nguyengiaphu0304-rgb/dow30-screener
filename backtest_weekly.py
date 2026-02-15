import pandas as pd
import numpy as np
from sqlalchemy import create_engine

TOP_K = 5

def to_monday_group(date_series: pd.Series) -> pd.Series:
    # group dates by week (Monday as start)
    return date_series.dt.to_period("W-MON").astype(str)

def weekly_backtest(feats: pd.DataFrame, score_col: str, filt_mask: pd.Series, name: str):
    tmp = feats[filt_mask].copy()
    tmp["week"] = to_monday_group(tmp["Date"])

    # pick top_k per week using first available trading day of that week
    # we do: within each week, take earliest date, then rank that date only
    first_day = tmp.groupby("week")["Date"].transform("min")
    candidates = tmp[tmp["Date"] == first_day].copy()

    picks = (
        candidates.sort_values(["week", score_col], ascending=[True, False])
                  .groupby("week")
                  .head(TOP_K)
                  .copy()
    )

    weekly = picks.groupby("week").agg(
        start_date=("Date", "min"),
        mean_excess_5d=("excess_fwd_r5", "mean"),
        hit_rate_excess=("excess_up5", "mean"),
        n_picks=("Ticker", "count"),
    ).reset_index()

    summary = pd.DataFrame([{
        "strategy": name,
        "weeks": len(weekly),
        "avg_picks_per_week": weekly["n_picks"].mean(),
        "mean_excess_5d": weekly["mean_excess_5d"].mean(),
        "hit_rate_excess": weekly["hit_rate_excess"].mean(),
    }])

    return summary, weekly

def main():
    engine = create_engine("sqlite:///prices.db")
    feats = pd.read_sql("SELECT * FROM features", engine, parse_dates=["Date"])

    spy = pd.read_sql("SELECT Date, Close FROM prices WHERE Ticker='SPY'", engine, parse_dates=["Date"])
    spy = spy.sort_values("Date").copy()
    spy["spy_fwd_r5"] = spy["Close"].shift(-5) / spy["Close"] - 1
    spy = spy.dropna(subset=["spy_fwd_r5"])

    feats["score_meanrev"] = -feats["z_r5"]
    feats["score_momo"] = feats["r20"]

    feats = feats.merge(spy[["Date", "spy_fwd_r5"]], on="Date", how="inner")
    feats["excess_fwd_r5"] = feats["fwd_r5"] - feats["spy_fwd_r5"]
    feats["excess_up5"] = (feats["excess_fwd_r5"] > 0).astype(int)

    # Filters (giữ y như cũ để so sánh apples-to-apples)
    meanrev_filter = (feats["z_r5"] <= -1.5)
    momo_filter = (feats["r20"] >= 0.10) & (feats["px_ma20"] > 0)

    s1, w1 = weekly_backtest(feats, "score_meanrev", meanrev_filter, "meanrev_weekly")
    s2, w2 = weekly_backtest(feats, "score_momo", momo_filter, "momo_weekly")

    summary = pd.concat([s1, s2], ignore_index=True)

    print("\n=== WEEKLY SUMMARY (Top 5 each week, hold ~5 trading days, excess vs SPY) ===")
    print(summary)

    w1.to_csv("bt_meanrev_weekly.csv", index=False)
    w2.to_csv("bt_momo_weekly.csv", index=False)
    summary.to_csv("bt_weekly_summary.csv", index=False)

    print("\nSaved: bt_weekly_summary.csv, bt_meanrev_weekly.csv, bt_momo_weekly.csv")

if __name__ == "__main__":
    main()
