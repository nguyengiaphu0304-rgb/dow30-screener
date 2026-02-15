import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///prices.db")
df = pd.read_sql("SELECT Ticker, COUNT(*) as n FROM prices GROUP BY Ticker ORDER BY n DESC", engine)
print(df.head(10))
print("Tickers:", len(df))
