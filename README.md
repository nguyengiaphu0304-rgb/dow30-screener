# Dow30 Weekly Opportunity Screener (Momentum vs SPY)

A small, reproducible ML/data project that generates a weekly "opportunity list" for Dow 30 stocks using a simple momentum signal, and evaluates performance out-of-sample against SPY.

This is not "predicting tomorrow's price." It is a screening tool: each week it ranks Dow constituents and outputs the strongest candidates, plus a backtest showing excess return vs a benchmark.

---

## What it does

Each week (rebalance on the first trading day of the week):

1. Pulls historical OHLCV price data for Dow 30 stocks + SPY
2. Builds features per ticker per date (returns, moving average distance, volatility, z-scores)
3. Applies a momentum opportunity rule:
   - **r20 >= 0.15** (20-trading-day return at least +15%)
   - **px_ma20 >= 0.00** (price above / not below its 20D moving average)
4. Ranks candidates and outputs:
   - `weekly_opportunity_report.csv` (Top picks + reasons)
5. Evaluates the rule using walk-forward style out-of-sample testing and benchmark-relative returns.

---

## Key idea

Most stock "ML" projects fail because:
- random train/test splits leak time information
- they measure raw returns (market beta) instead of alpha
- they skip baselines and out-of-sample checks

This project avoids that by:
- using time-aware evaluation
- measuring **excess return vs SPY**
- separating in-sample vs out-of-sample periods

---

## Results (excess return vs SPY)

**Out-of-sample evaluation**
- In-sample: 2015–2021
- Out-of-sample: 2022–2026

From `oos_momo_summary.csv`:

| Period | Weeks | Avg picks/week | Mean excess 5D return | Excess hit rate |
|---|---:|---:|---:|---:|
| 2015–2021 (in-sample) | 174 | 1.61 | 0.2123% | 54.28% |
| 2022–2026 (out-of-sample) | 154 | 1.77 | 0.4155% | 52.71% |

**Cumulative Excess Return:** +27.94% over full 11-year backtest period

Results are saved in:
- `cumulative_excess.png` – visual chart
- `weekly_cum_excess_series.csv` – week-by-week data

---

## Project structure

- **`download_prices.py`**  
  Downloads Dow30 daily OHLCV and saves to `prices.db`

- **`add_spy.py`**  
  Adds SPY benchmark to `prices.db`

- **`build_features.py`**  
  Creates `features` table with engineered features + forward 5D labels

- **`screener.py`**  
  Prints and exports daily Top 5 mean reversion and momentum lists (baseline)

- **`backtest_simple.py`**  
  Daily baseline backtest (Top 5 vs random)

- **`backtest_weekly.py`**  
  Weekly rebalance backtest (Top 5/week vs SPY)

- **`backtest_excess_filtered.py`**  
  Tests filtered strategies with excess returns vs benchmark

- **`backtest_momo_v2.py`**  
  Compares momentum variants (baseline vs enhanced)

- **`tune_momentum.py`**  
  Grid search for optimal momentum thresholds (9 combinations tested)

- **`oos_test_momentum.py`**  
  In-sample vs out-of-sample evaluation (critical for validation)

- **`weekly_report.py`** ⭐ **Main script for operational use**  
  Generates `weekly_opportunity_report.csv` with ranked picks + reasons

- **`plot_cumulative_excess.py`**  
  Generates performance visualization and time series

---

## How to run (Windows)

### 1) Setup environment
```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install pandas numpy yfinance sqlalchemy matplotlib
```

### 2) Get data (one-time setup)
```bash
# Download Dow30 + SPY price history (2015-present)
python download_prices.py
python add_spy.py

# Verify data was loaded
python check_db.py
```

### 3) Build features
```bash
python build_features.py
python check_features.py
```

### 4) Run backtests (exploratory analysis)
```bash
# Simple daily backtest: momentum vs mean reversion vs random
python backtest_simple.py

# Weekly rebalancing backtest
python backtest_weekly.py

# Find best momentum parameters
python tune_momentum.py

# Validate performance out-of-sample
python oos_test_momentum.py
```

### 5) Generate weekly picks (operational)
```bash
# Generates weekly_opportunity_report.csv
python weekly_report.py
```

### 6) Visualize performance
```bash
python plot_cumulative_excess.py
# Creates: cumulative_excess.png
```

---

## Output files

| File | Purpose |
|---|---|
| `prices.db` | SQLite database with Dow30 + SPY daily OHLCV |
| `weekly_opportunity_report.csv` | **Current week's top 5 picks with reasons** |
| `cumulative_excess.png` | Chart of strategy's cumulative excess return |
| `weekly_cum_excess_series.csv` | Weekly performance breakdown |
| `tune_momentum_results.csv` | Grid search results for parameter tuning |
| `oos_momo_summary.csv` | In-sample vs out-of-sample performance |
| `bt_*.csv` | Various backtest results |

---

## Key insights from analysis

1. **Momentum outperforms mean reversion**
   - Simple momentum (r20 ≥ 10%) adds +0.07% alpha/week
   - Mean reversion rule had negative alpha

2. **Higher threshold is better**
   - r20 ≥ 15% beats r20 ≥ 10% (+0.31% vs +0.07%)
   - More selective → higher quality picks

3. **No overfitting detected**
   - Out-of-sample (2022–2026) beats in-sample (2015–2021)
   - Rule generalizes to recent volatile markets

4. **Modest but consistent edge**
   - ~52–54% hit rate (slightly better than 50% by chance)
   - Cumulative +27.94% excess over 11 years

---

## Usage example

```bash
# Weekly workflow:
# Step 1: Pull latest data (if needed)
python add_spy.py

# Step 2: Rebuild features with latest data
python build_features.py

# Step 3: Generate this week's picks
python weekly_report.py

# Output: weekly_opportunity_report.csv
# Ticker: INTC, Reason: Strong 20D momentum (r20=0.251), above MA20
```

---

## Limitations & Disclaimers

- **Not financial advice.** This is an educational screener, not a trading system.
- **Past performance ≠ future results.** Backtests use survivorship-bias-free Dow30 data, but market regimes change.
- **Transaction costs ignored.** Model doesn't account for slippage, commissions, or market impact.
- **Micro-cap risk.** All positions are equal-weighted; larger positions may face liquidity constraints.
- **5-day horizon.** Strategy targets short-term momentum. Longer holding periods may show different results.
- **Data quality:** Depends on yfinance data accuracy. Spot-check against Bloomberg/Yahoo Finance if using commercially.

---

## Next steps / Improvements

- [ ] Add portfolio optimizer (risk parity, max Sharpe)
- [ ] Include transaction cost model
- [ ] Test on other indices (S&P 500, Russell 2000)
- [ ] Live paper trading integration
- [ ] Machine learning layer on top (XGBoost for feature importance)
- [ ] Sector rotation rules

---

## Author notes

Built February 2026 as a reproducible stock screening framework. See backtests and validation results for evidence of edge.

**Key files to review:**
1. `oos_test_momentum.py` – Shows how strategy generalizes
2. `tune_momentum.py` – Demonstrates parameter search (avoid overfitting!)
3. `weekly_report.py` – Operational script for real-world use
