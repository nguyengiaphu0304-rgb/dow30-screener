import pandas as pd
from sqlalchemy import create_engine

e = create_engine('sqlite:///prices.db')
result = pd.read_sql("SELECT Ticker, COUNT(*) as n FROM prices WHERE Ticker='SPY'", e)
print(result)
