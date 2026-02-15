# Quick Start Guide

## 5-Minute Setup

### Prerequisites
- Windows 10/11 with Python 3.8+
- Git installed

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/dow30-screener.git
cd dow30-screener

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download data (first time only, takes 2-3 minutes)
python download_prices.py
python add_spy.py

# 5. Build features
python build_features.py

# Done! Now generate this week's picks:
python weekly_report.py
```

✅ **Output:** `weekly_opportunity_report.csv` with top 5 momentum stocks!

---

## What Each File Does

| File | Purpose | Run When? |
|---|---|---|
| `download_prices.py` | Get historical price data | First time only |
| `add_spy.py` | Add S&P 500 benchmark | First time only |
| `build_features.py` | Calculate indicators | Before weekly_report |
| `weekly_report.py` | **Generate picks** | Every Monday |
| `oos_test_momentum.py` | Validate accuracy | Curious about performance |
| `plot_cumulative_excess.py` | Show strategy performance | Want to see backtests |

---

## Weekly Workflow

Every Monday morning:
```bash
# Activate your environment
.venv\Scripts\activate

# Update data and features
python build_features.py

# Get this week's picks
python weekly_report.py

# Check the output
cat weekly_opportunity_report.csv
```

---

## Example Output

After running `python weekly_report.py`, you'll see:

```
Week: 2026-02-03/2026-02-09
Rebalance date: 2026-02-03

Top picks:
  rank Ticker    score      r20      r5  px_ma20   vol20   z_r5
  1    INTC      0.251    0.251    0.121  0.053    0.068  1.056
  Reason: Strong 20D momentum (r20=0.251), above MA20 (px_ma20=0.053)

Saved: weekly_opportunity_report.csv
```

---

## Understanding the Metrics

| Metric | Meaning | Example |
|--------|---------|---------|
| **score** | 20-day return (main signal) | 0.251 = +25.1% |
| **r20** | 20-day momentum | High = trending up |
| **r5** | 5-day return | Recent direction |
| **px_ma20** | % above 20-day MA | 0.053 = 5.3% above MA |
| **vol20** | 20-day volatility | Risk level |
| **z_r5** | Statistical significance | > 1.0 = significant |
| **rank** | Priority order | 1 = most bullish |

**Interpretation:**
- Stocks with **rank=1** are strongest performers
- Look at **reason** column to understand why it was picked
- **px_ma20 > 0** means price is above moving average (good sign)

---

## Backtesting / Validation

Want to see how the strategy performed historically?

```bash
# Out-of-sample test (2015-2021 vs 2022-2026)
python oos_test_momentum.py

# Parameter tuning (which thresholds work best?)
python tune_momentum.py

# Performance chart
python plot_cumulative_excess.py
```

---

## Troubleshooting

**Q: "ModuleNotFoundError: No module named 'pandas'"**  
A: Run `pip install -r requirements.txt`

**Q: "OSError: [Errno 2] No such file or directory: 'prices.db'"**  
A: First run `python download_prices.py`

**Q: Reports show "No picks this week under current rule"**  
A: This happens when no Dow30 stocks meet the r20 >= 0.15 threshold (rare but okay!)

**Q: It's taking a long time to download data**  
A: Normal on first run (fetching 11 years of data). On repeat runs, it's quick.

---

## Next Steps

1. **Run weekly:** Schedule `python weekly_report.py` for Mondays
2. **Share picks:** Copy `weekly_opportunity_report.csv` to your team
3. **Track performance:** Keep CSV files to measure if the picks actually work
4. **Customize:** Edit thresholds in `weekly_report.py` if needed
5. **Contribute:** Found a bug? Submit a PR on GitHub!

---

## More Info

- 📖 See **README.md** for full documentation
- 🚀 See **DEPLOYMENT.md** for cloud/automation setup
- 💻 See **CONTRIBUTING.md** to help improve the project

---

**Happy screening!** 📊
