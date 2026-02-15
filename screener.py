import pandas as pd
from sqlalchemy import create_engine

def main():
    engine = create_engine("sqlite:///prices.db")
    feats = pd.read_sql("SELECT * FROM features", engine, parse_dates=["Date"])

    # Lấy ngày mới nhất có dữ liệu
    latest_date = feats["Date"].max()
    latest = feats[feats["Date"] == latest_date].copy()

    # Score 1: Mean Reversion (oversold -> score cao)
    latest["score_meanrev"] = -latest["z_r5"]

    # Score 2: Momentum (mạnh -> score cao)
    latest["score_momo"] = latest["r20"]

    # Top 5 each
    top_meanrev = latest.sort_values("score_meanrev", ascending=False).head(5)
    top_momo = latest.sort_values("score_momo", ascending=False).head(5)

    # Chọn cột để show
    cols_meanrev = ["Ticker","Date","score_meanrev","z_r5","r5","r20","vol20","px_ma20"]
    cols_momo = ["Ticker","Date","score_momo","r20","r5","vol20","px_ma20","z_r5"]

    out_meanrev = top_meanrev[cols_meanrev].reset_index(drop=True)
    out_momo = top_momo[cols_momo].reset_index(drop=True)

    out_meanrev.to_csv("top5_mean_reversion.csv", index=False)
    out_momo.to_csv("top5_momentum.csv", index=False)

    print("Latest date:", latest_date.date())
    print("\nTop 5 Mean Reversion (oversold bounce candidates):")
    print(out_meanrev)

    print("\nTop 5 Momentum (trend continuation candidates):")
    print(out_momo)

    print("\nSaved files: top5_mean_reversion.csv, top5_momentum.csv")

if __name__ == "__main__":
    main()
