import pandas as pd
from sqlalchemy import create_engine

TOP_K = 5
R20_TH = 0.15
PXMA_TH = 0.00

def to_week(date_series: pd.Series) -> pd.Series:
    return date_series.dt.to_period("W-MON").astype(str)

def main():
    engine = create_engine("sqlite:///prices.db")
    feats = pd.read_sql("SELECT * FROM features", engine, parse_dates=["Date"])

    feats["score_momo"] = feats["r20"]
    feats["week"] = to_week(feats["Date"])

    latest_week = feats["week"].max()
    wk = feats[feats["week"] == latest_week].copy()

    # use earliest trading day of the week
    start_date = wk["Date"].min()
    wk = wk[wk["Date"] == start_date].copy()

    # apply rule
    wk = wk[(wk["r20"] >= R20_TH) & (wk["px_ma20"] >= PXMA_TH)].copy()

    if wk.empty:
        print("No picks this week under current rule.")
        return

    picks = wk.sort_values("score_momo", ascending=False).head(TOP_K).copy()
    picks["rank"] = range(1, len(picks) + 1)

    # simple reason strings
    picks["reason"] = (
        "Strong 20D momentum (r20=" + picks["r20"].round(3).astype(str) + ")"
        + ", above MA20 (px_ma20=" + picks["px_ma20"].round(3).astype(str) + ")"
    )

    report = picks[["rank","Ticker","Date","score_momo","r20","r5","px_ma20","vol20","z_r5","reason"]].copy()
    report = report.rename(columns={"score_momo":"score"})

    report.to_csv("weekly_opportunity_report.csv", index=False)

    print("Week:", latest_week)
    print("Rebalance date:", start_date.date())
    print("\nTop picks:")
    print(report)
    print("\nSaved: weekly_opportunity_report.csv")

if __name__ == "__main__":
    main()
