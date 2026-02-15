import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

TOP_K = 5
R20_TH = 0.15
PXMA_TH = 0.00

def to_week(date_series: pd.Series) -> pd.Series:
    return date_series.dt.to_period("W-MON").astype(str)

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

    feats["week"] = to_week(feats["Date"])

    # weekly selection on first trading day each week
    first_day = feats.groupby("week")["Date"].transform("min")
    candidates = feats[feats["Date"] == first_day].copy()

    # apply rule
    candidates = candidates[(candidates["r20"] >= R20_TH) & (candidates["px_ma20"] >= PXMA_TH)].copy()

    # pick top K per week
    picks = (
        candidates.sort_values(["week", "score_momo"], ascending=[True, False])
                  .groupby("week")
                  .head(TOP_K)
                  .copy()
    )

    weekly = picks.groupby("week").agg(
        start_date=("Date", "min"),
        mean_excess_5d=("excess_fwd_r5", "mean"),
        n_picks=("Ticker", "count")
    ).reset_index()

    # fill weeks with 0 when no picks (so chart continues)
    all_weeks = feats[["week"]].drop_duplicates().sort_values("week")
    weekly = all_weeks.merge(weekly, on="week", how="left")
    weekly["mean_excess_5d"] = weekly["mean_excess_5d"].fillna(0.0)
    weekly["n_picks"] = weekly["n_picks"].fillna(0)

    weekly["cum_excess"] = (1 + weekly["mean_excess_5d"]).cumprod() - 1

    # plot
    plt.figure(figsize=(12, 6))
    plt.plot(weekly["cum_excess"], linewidth=2)
    plt.title("Cumulative Excess Return vs SPY (Weekly Momentum Rule)", fontsize=14)
    plt.xlabel("Weeks", fontsize=12)
    plt.ylabel("Cumulative Excess Return", fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("cumulative_excess.png", dpi=150)
    print("Saved chart: cumulative_excess.png")

    weekly.to_csv("weekly_cum_excess_series.csv", index=False)
    print(f"Saved series: weekly_cum_excess_series.csv ({len(weekly)} weeks)")
    print(f"Final cumulative excess: {weekly['cum_excess'].iloc[-1]:.2%}")

if __name__ == "__main__":
    main()
