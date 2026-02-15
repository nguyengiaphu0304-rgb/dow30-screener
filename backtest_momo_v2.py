import pandas as pd
from sqlalchemy import create_engine

TOP_K = 5

def to_monday_group(date_series: pd.Series) -> pd.Series:
    return date_series.dt.to_period("W-MON").astype(str)

def weekly_pick(feats: pd.DataFrame, score_col: str, filt_mask: pd.Series, name: str):
    tmp = feats[filt_mask].copy()
    tmp["week"] = to_monday_group(tmp["Date"])

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
    prices = pd.read_sql("SELECT Ticker, Date, Close FROM prices", engine, parse_dates=["Date"])

    # Build SPY r20 to compute relative momentum
    spy = prices[prices["Ticker"] == "SPY"].sort_values("Date").copy()
    spy["spy_r20"] = spy["Close"].pct_change(20)
    spy["spy_fwd_r5"] = spy["Close"].shift(-5) / spy["Close"] - 1
    spy = spy.dropna(subset=["spy_r20", "spy_fwd_r5"])

    feats["score_momo"] = feats["r20"]

    feats = feats.merge(spy[["Date", "spy_r20", "spy_fwd_r5"]], on="Date", how="inner")
    feats["rel20"] = feats["r20"] - feats["spy_r20"]
    feats["excess_fwd_r5"] = feats["fwd_r5"] - feats["spy_fwd_r5"]
    feats["excess_up5"] = (feats["excess_fwd_r5"] > 0).astype(int)

    # Momentum v1 (current) for comparison
    momo_v1 = (feats["r20"] >= 0.10) & (feats["px_ma20"] > 0)

    # Momentum v2: require beating SPY + cap volatility
    momo_v2 = (feats["r20"] >= 0.10) & (feats["px_ma20"] > 0) & (feats["rel20"] > 0) & (feats["vol20"] <= 0.03)

    s1, w1 = weekly_pick(feats, "score_momo", momo_v1, "momo_v1_weekly")
    s2, w2 = weekly_pick(feats, "score_momo", momo_v2, "momo_v2_weekly")

    summary = pd.concat([s1, s2], ignore_index=True)

    print("\n=== MOMENTUM V1 vs V2 (weekly, excess vs SPY) ===")
    print(summary)

    w1.to_csv("bt_momo_v1_weekly.csv", index=False)
    w2.to_csv("bt_momo_v2_weekly.csv", index=False)
    summary.to_csv("bt_momo_v1_v2_summary.csv", index=False)

    print("\nSaved: bt_momo_v1_v2_summary.csv, bt_momo_v1_weekly.csv, bt_momo_v2_weekly.csv")

if __name__ == "__main__":
    main()
