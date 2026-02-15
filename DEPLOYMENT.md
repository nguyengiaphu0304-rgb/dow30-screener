# Deployment & GitHub Setup

## Publishing to GitHub

### 1. Create a GitHub Repository
1. Go to https://github.com/new
2. Repository name: `dow30-screener`
3. Description: "A weekly momentum screener for Dow 30 stocks with out-of-sample validation"
4. Choose **Public** (for open source)
5. Check "Add a README file" (optional, we have one)
6. Choose license: **MIT License**
7. Click "Create repository"

### 2. Push Your Local Code to GitHub
```bash
cd c:\Users\trann\Desktop\dow30-screener

# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit: Dow30 momentum screener with OOS validation"

# Add remote repository
git remote add origin https://github.com/YOUR_USERNAME/dow30-screener.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 3. Update GitHub Links
Edit these files and replace `YOUR_USERNAME`:
- `README.md` - GitHub links (already has placeholder)
- `pyproject.toml` - URLs in [project.urls]
- `CONTRIBUTING.md` - GitHub references

---

## Deployment Scenarios

### Scenario A: Personal Use / Self-Hosted
```bash
# Just clone and run on your machine
git clone https://github.com/YOUR_USERNAME/dow30-screener.git
cd dow30-screener
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python weekly_report.py
```

### Scenario B: Cloud Deployment (AWS Lambda / Google Cloud)
```bash
# Package as a function that runs weekly_report.py on a schedule
# Example: AWS Lambda with CloudWatch Events trigger

# 1. Create lambda_handler.py
# 2. Deploy with serverless framework or AWS SAM
# 3. Set trigger for Monday 9:00 AM ET
```

### Scenario C: Docker Containerization
Create `Dockerfile`:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "weekly_report.py"]
```

Build and run:
```bash
docker build -t dow30-screener .
docker run dow30-screener
```

### Scenario D: Scheduled Task (Windows Task Scheduler)
```bash
# Create batch file: run_weekly_screener.bat
@echo off
cd C:\Users\trann\Desktop\dow30-screener
.venv\Scripts\python.exe weekly_report.py

# Then schedule in Windows Task Scheduler for 9:00 AM every Monday
```

### Scenario E: GitHub Actions (Automated Reporting)
Create `.github/workflows/weekly-screener.yml`:
```yaml
name: Weekly Screener Report

on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday 9 AM UTC

jobs:
  screener:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: python download_prices.py
      - run: python build_features.py
      - run: python weekly_report.py
      - uses: actions/upload-artifact@v2
        with:
          name: weekly-reports
          path: |
            weekly_opportunity_report.csv
            cumulative_excess.png
```

---

## Pre-Release Checklist

- [ ] All scripts tested and working
- [ ] README.md finalized with your GitHub link
- [ ] LICENSE file in place (MIT)
- [ ] .gitignore configured
- [ ] requirements.txt up to date
- [ ] CONTRIBUTING.md ready for contributors
- [ ] pyproject.toml metadata complete
- [ ] No sensitive data in repo (API keys, personal info)
- [ ] Example output files included (or .gitignored)
- [ ] Backtests re-run and documented
- [ ] GitHub repo created and code pushed

---

## After Going Public

### 1. Add Documentation
- [ ] Add Jupyter notebook showing example usage
- [ ] Create QUICKSTART.md for fast onboarding
- [ ] Add sample output screenshots

### 2. Gather Feedback
- [ ] Star on GitHub (share with friends)
- [ ] Open issues section for feedback
- [ ] Create discussions for ideas

### 3. Expand
- [ ] Add CI/CD pipeline
- [ ] Set up automated testing
- [ ] Create releases with version tags
- [ ] Write blog post about the project

### 4. Monetization (Optional)
- [ ] Premium features (more indicators, more stocks)
- [ ] Patreon for continuous updates
- [ ] Consulting/advisory services

---

## GitHub Repository URLs

**Your repository will be at:**
```
https://github.com/YOUR_USERNAME/dow30-screener
```

**Clone command:**
```bash
git clone https://github.com/YOUR_USERNAME/dow30-screener.git
```

**Share this link to get others to use your screener!**

---

## Troubleshooting

**Problem:** GitHub says "fatal: 'origin' does not appear to be a 'git' repository"  
**Solution:** Run `git remote add origin <URL>` first

**Problem:** Files show as "Untracked" after push  
**Solution:** Check .gitignore is committed and correct

**Problem:** Large files (prices.db) won't push  
**Solution:** Use .gitignore to exclude, or set up Git LFS for binary files

---

## Security Notes

- ✅ Never commit API keys or credentials
- ✅ Keep dependencies updated
- ✅ Use requirements.txt with pinned versions
- ✅ Review code before merging PRs
- ✅ Set up branch protection rules on GitHub (Settings > Branches)

---

Questions? See CONTRIBUTING.md for community support.
