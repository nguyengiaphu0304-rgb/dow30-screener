import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("sqlite:///prices.db")
df = pd.read_sql("SELECT COUNT(*) as n FROM features", engine)
print(df)

df2 = pd.read_sql("SELECT Ticker, COUNT(*) as n FROM features GROUP BY Ticker ORDER BY n DESC", engine)
print(df2.head(10))
print("Tickers:", len(df2))
