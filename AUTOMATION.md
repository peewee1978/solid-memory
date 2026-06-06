# Daily Automation & Cheat Sheet

This folder contains scripts and GitHub Actions workflow to:
- Train a placeholder model daily
- Fetch daily games using free scrapers
- Generate a cheat-sheet with moneyline picks
- Email the cheat-sheet to marionstozier15@gmail.com

Files added:
- src/tasks/train_model.py - trains a synthetic model and saves to models/
- src/tasks/generate_and_send.py - runs tests, trains, builds cheat-sheet, and emails results
- .github/workflows/daily_cheatsheet.yml - scheduled GitHub Actions workflow (12:00 PM Central)
- .env.example - environment variables you must populate
- requirements-automation.txt - extra Python packages

Setup steps:
1. Create a SendGrid account and verify your sender email (MAIL_FROM).
2. In your GitHub repo: Settings → Secrets and variables → Actions → New repository secret, add:
   - SENDGRID_API_KEY: your SendGrid API key
   - MAIL_FROM: the verified sender email
   - NOTIFY_EMAIL: marionstozier15@gmail.com
   - (optional) ESPN_API_KEY, RAPID_API_KEY
3. (Optional) Test locally:
   - python -m venv venv
   - source venv/bin/activate  # Windows: venv\Scripts\activate
   - pip install -r requirements.txt
   - pip install -r requirements-automation.txt
   - Copy .env.example to .env and fill in keys
   - python src/tasks/generate_and_send.py

Notes:
- The pipeline uses free scrapers (ESPN & Sports Reference). These may be brittle; for production, integrate paid APIs.
- SendGrid free tier supports low-volume daily emails; verify your sender in SendGrid.
