# Contributing to Dow30 Weekly Screener

Thanks for your interest in contributing! This is an open-source project and we welcome improvements.

## How to Contribute

### 1. Fork and Clone
```bash
git clone https://github.com/YOUR_USERNAME/dow30-screener.git
cd dow30-screener
```

### 2. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 3. Set Up Development Environment
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Make Your Changes
- Keep code style consistent with existing files
- Add comments for complex logic
- Test your changes with real data

### 5. Test Your Work
```bash
# Example: test a script manually
python weekly_report.py

# Or test backtests
python oos_test_momentum.py
```

### 6. Commit and Push
```bash
git add .
git commit -m "feat: describe your changes clearly"
git push origin feature/your-feature-name
```

### 7. Create a Pull Request
- Describe what your change does
- Link any related issues
- Show backtest results if algorithm changes

## Ideas for Contribution

- [ ] Add sector rotation logic
- [ ] Implement portfolio optimizer
- [ ] Add transaction cost model
- [ ] Support for other indices
- [ ] Improve documentation
- [ ] Add unit tests
- [ ] Performance optimizations
- [ ] New feature indicators

## Code Style

- Use descriptive variable names
- Add docstrings to functions
- Keep functions focused and small
- Use type hints where helpful
- Comment "why" not "what"

## Reporting Issues

Found a bug or have an idea? Open an issue with:
- Clear description of the problem
- Steps to reproduce (if bug)
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

## Questions?

Open a discussion or issue on GitHub. We're here to help!

---

**License:** MIT - see LICENSE file
