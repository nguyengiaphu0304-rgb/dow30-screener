import pandas as pd
from sqlalchemy import create_engine, inspect

engine = create_engine("sqlite:///prices.db")

# Get database inspector
inspector = inspect(engine)

# List all tables
tables = inspector.get_table_names()
print(f"Tables in database: {tables}\n")

# Get schema for prices table
if 'prices' in tables:
    columns = inspector.get_columns('prices')
    print("Schema for 'prices' table:")
    for col in columns:
        print(f"  - {col['name']}: {col['type']}")
    
    # Get row counts
    df_count = pd.read_sql("SELECT COUNT(*) as total_rows FROM prices", engine)
    print(f"\nTotal rows: {df_count.iloc[0, 0]}")
    
    # Get date range
    df_dates = pd.read_sql("SELECT MIN(Date) as min_date, MAX(Date) as max_date FROM prices", engine)
    print(f"Date range: {df_dates.iloc[0, 0]} to {df_dates.iloc[0, 1]}")
    
    # Check for NULL values
    df_nulls = pd.read_sql("""
    SELECT 
        SUM(CASE WHEN Ticker IS NULL THEN 1 ELSE 0 END) as null_Ticker,
        SUM(CASE WHEN Date IS NULL THEN 1 ELSE 0 END) as null_Date,
        SUM(CASE WHEN Open IS NULL THEN 1 ELSE 0 END) as null_Open,
        SUM(CASE WHEN High IS NULL THEN 1 ELSE 0 END) as null_High,
        SUM(CASE WHEN Low IS NULL THEN 1 ELSE 0 END) as null_Low,
        SUM(CASE WHEN Close IS NULL THEN 1 ELSE 0 END) as null_Close,
        SUM(CASE WHEN Volume IS NULL THEN 1 ELSE 0 END) as null_Volume
    FROM prices
    """, engine)
    print("\nNULL value counts:")
    for col in df_nulls.columns:
        print(f"  {col}: {df_nulls.iloc[0][col]}")
    
    # Sample rows
    print("\nSample rows:")
    df_sample = pd.read_sql("SELECT * FROM prices LIMIT 5", engine)
    print(df_sample)
