import pandas as pd
from sqlalchemy import create_engine

TOP_K = 5

# Chosen rule from tuning
R20_TH = 0.15
PXMA_TH = 0.00

def to_monday_group(date_series: pd.Series) -> pd.Series:
    return date_series.dt.to_period("W-MON").astype(str)

def weekly_eval(feats: pd.DataFrame, name: str):
    feats = feats.copy()
    feats["week"] = to_monday_group(feats["Date"])

    first_day = feats.groupby("week")["Date"].transform("min")
    candidates = feats[feats["Date"] == first_day].copy()

    picks = (
        candidates.sort_values(["week", "score_momo"], ascending=[True, False])
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
        "period": name,
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

    # SPY benchmark forward 5d
    spy = prices[prices["Ticker"] == "SPY"].sort_values("Date").copy()
    spy["spy_fwd_r5"] = spy["Close"].shift(-5) / spy["Close"] - 1
    spy = spy.dropna(subset=["spy_fwd_r5"])

    feats["score_momo"] = feats["r20"]
    feats = feats.merge(spy[["Date", "spy_fwd_r5"]], on="Date", how="inner")
    feats["excess_fwd_r5"] = feats["fwd_r5"] - feats["spy_fwd_r5"]
    feats["excess_up5"] = (feats["excess_fwd_r5"] > 0).astype(int)

    # apply the chosen rule
    feats = feats[(feats["r20"] >= R20_TH) & (feats["px_ma20"] >= PXMA_TH)].copy()

    # split periods
    train = feats[(feats["Date"] >= "2015-01-01") & (feats["Date"] <= "2021-12-31")].copy()
    test  = feats[(feats["Date"] >= "2022-01-01") & (feats["Date"] <= "2026-12-31")].copy()

    s_train, w_train = weekly_eval(train, "2015-2021 (in-sample)")
    s_test,  w_test  = weekly_eval(test,  "2022-2026 (out-of-sample)")

    summary = pd.concat([s_train, s_test], ignore_index=True)

    print("\n=== OOS TEST: Momentum Rule r20>=0.15, px_ma20>=0.00 (weekly, excess vs SPY) ===")
    print(summary)

    w_train.to_csv("oos_momo_train_weekly.csv", index=False)
    w_test.to_csv("oos_momo_test_weekly.csv", index=False)
    summary.to_csv("oos_momo_summary.csv", index=False)
    print("\nSaved: oos_momo_summary.csv, oos_momo_train_weekly.csv, oos_momo_test_weekly.csv")

if __name__ == "__main__":
    main()
