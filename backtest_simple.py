import pandas as pd
import numpy as np
from sqlalchemy import create_engine

def backtest_group(feats: pd.DataFrame, score_col: str, top_k: int = 5) -> pd.DataFrame:
    # mỗi ngày chọn top_k theo score_col, lấy fwd_r5 để tính performance
    picks = (
        feats.sort_values(["Date", score_col], ascending=[True, False])
            .groupby("Date")
            .head(top_k)
            .copy()
    )
    daily = picks.groupby("Date").agg(
        avg_fwd_r5=("fwd_r5", "mean"),
        hit_rate=("fwd_up5", "mean")
    ).reset_index()
    daily["strategy"] = score_col
    return daily

def backtest_random(feats: pd.DataFrame, top_k: int = 5, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    rows = []
    for d, g in feats.groupby("Date"):
        if len(g) < top_k:
            continue
        idx = rng.choice(g.index.to_numpy(), size=top_k, replace=False)
        sample = g.loc[idx]
        rows.append({
            "Date": d,
            "avg_fwd_r5": sample["fwd_r5"].mean(),
            "hit_rate": sample["fwd_up5"].mean()
        })

    daily = pd.DataFrame(rows).sort_values("Date")
    daily["strategy"] = "random"
    return daily

def summarize(daily: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame([{
        "strategy": daily["strategy"].iloc[0],
        "days": len(daily),
        "mean_5d_return": daily["avg_fwd_r5"].mean(),
        "hit_rate": daily["hit_rate"].mean()
    }])

def main():
    engine = create_engine("sqlite:///prices.db")
    feats = pd.read_sql("SELECT * FROM features", engine, parse_dates=["Date"])

    # tạo 2 score giống screener
    feats["score_meanrev"] = -feats["z_r5"]
    feats["score_momo"] = feats["r20"]

    # optional: bỏ giai đoạn đầu ít data
    feats = feats.sort_values("Date")

    meanrev_daily = backtest_group(feats, "score_meanrev", top_k=5)
    momo_daily = backtest_group(feats, "score_momo", top_k=5)
    rand_daily = backtest_random(feats, top_k=5, seed=42)

    summary = pd.concat([
        summarize(meanrev_daily),
        summarize(momo_daily),
        summarize(rand_daily)
    ], ignore_index=True)

    print("\n=== SUMMARY (Top 5 each day, forward 5-day return) ===")
    print(summary)

    # save detailed series
    meanrev_daily.to_csv("bt_meanrev_daily.csv", index=False)
    momo_daily.to_csv("bt_momo_daily.csv", index=False)
    rand_daily.to_csv("bt_random_daily.csv", index=False)
    summary.to_csv("bt_summary.csv", index=False)

    print("\nSaved: bt_summary.csv, bt_meanrev_daily.csv, bt_momo_daily.csv, bt_random_daily.csv")

if __name__ == "__main__":
    main()
