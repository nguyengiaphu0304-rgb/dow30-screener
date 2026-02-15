import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine

DOW30 = [
    "AAPL","MSFT","AMZN","NVDA","JPM","V","UNH","HD","PG","MA",
    "DIS","CRM","GS","MCD","NKE","VZ","KO","CAT","BA","IBM",
    "MMM","HON","CVX","WMT","TRV","AXP","MRK","CSCO","INTC","JNJ"
]

def main():
    engine = create_engine("sqlite:///prices.db")

    all_rows = 0
    first_ticker = True
    for ticker in DOW30:
        try:
            df = yf.download(ticker, start="2015-01-01", interval="1d", auto_adjust=False, progress=False)

            if df.empty:
                print(f"Skip {ticker} (no data)")
                continue

            # Flatten MultiIndex columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [col[0] for col in df.columns]
            
            df = df.reset_index()
            df["Ticker"] = ticker
            
            # Select only the columns we need
            df = df[["Ticker","Date","Open","High","Low","Close","Volume"]]

            if_exists = "replace" if first_ticker else "append"
            df.to_sql("prices", engine, if_exists=if_exists, index=False)
            first_ticker = False
            all_rows += len(df)
            print(f"{ticker}: {len(df)} rows")
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue

    print(f"Done. Total rows inserted: {all_rows}")
    print("Saved to prices.db (table: prices)")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
