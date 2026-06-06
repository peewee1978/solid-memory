#!/usr/bin/env python3
"""
Daily pipeline:
- run tests (pytest)
- train model (train_model.py)
- fetch today's games, create simple predictions
- send email via SendGrid to marionstozier15@gmail.com
"""
import os
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from src.data_fetcher import DataAggregator
from src.props_calculator import PropsCalculator
import joblib
import logging

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
MAIL_FROM = os.getenv("MAIL_FROM")
NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "marionstozier15@gmail.com")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("daily_pipeline")

MODEL_PATH = "models/props_model.pkl"
SCALER_PATH = "models/scaler.pkl"

def run_tests():
    try:
        subprocess.run(["pytest", "tests/"], check=True)
        logger.info("Tests passed")
    except subprocess.CalledProcessError:
        logger.warning("Some tests failed — continuing pipeline")

def train_model():
    try:
        subprocess.run(["python", "src/tasks/train_model.py"], check=True)
    except subprocess.CalledProcessError:
        logger.exception("Training script failed")

def load_model():
    if os.path.exists(MODEL_PATH):
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH) if os.path.exists(SCALER_PATH) else None
        return model, scaler
    return None, None

def build_cheat_sheet(model=None, scaler=None):
    agg = DataAggregator()
    props = PropsCalculator()

    today = datetime.now().strftime("%Y%m%d")
    picks = []

    for sport in agg.SUPPORTED_SPORTS:
        try:
            data = agg.get_daily_props_data(sport, today)
            games = (data or {}).get("games") or {}
            events = games.get("events") if isinstance(games, dict) else None
            if not events:
                continue
            for ev in events:
                comp = ev.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue
                home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
                away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1] if len(competitors) > 1 else competitors[0])
                home_team = home.get("team", {}).get("displayName", "Home")
                away_team = away.get("team", {}).get("displayName", "Away")

                # placeholders for stats; in future replace with real team/player stats
                home_stats = {"name": home_team, "ppg": 100, "def_ppg": 100}
                away_stats = {"name": away_team, "ppg": 100, "def_ppg": 100}

                # moneyline via PropsCalculator.MoneyLineCalculator (or PropsCalculator.moneyline-like behavior)
                from src.props_calculator import MoneyLineCalculator
                ml_calc = MoneyLineCalculator()
                ml = ml_calc.calculate_moneyline(home_stats, away_stats, sport=sport)
                picks.append({
                    "sport": sport,
                    "type": "moneyline",
                    "home": home_team,
                    "away": away_team,
                    "prediction": ml["prediction"],
                    "confidence": round(ml["home_win_probability"] if ml["prediction"]=="HOME" else ml["away_win_probability"], 3)
                })
        except Exception:
            logger.exception(f"Error processing sport {sport}")

    # sort by confidence
    picks_sorted = sorted(picks, key=lambda p: p.get("confidence", 0), reverse=True)
    return picks_sorted

def format_email(picks):
    subject = f"Daily Cheat Sheet — {datetime.utcnow().date().isoformat()}"
    text_lines = [f"Daily Cheat Sheet ({datetime.utcnow().date().isoformat()})", ""]
    for p in picks[:30]:
        text_lines.append(f"{p['sport'].upper()}: {p['home']} vs {p['away']} — {p['prediction']} ({p['confidence']:.2f})")
    html = "<h2>Daily Cheat Sheet</h2><ul>" + "".join([f"<li>{line}</li>" for line in text_lines[1:]]) + "</ul>"
    return subject, "\n".join(text_lines), html

def send_email(subject, html_content, to_email):
    if not SENDGRID_API_KEY or not MAIL_FROM or not to_email:
        logger.warning("SendGrid or emails not configured; skipping send.")
        return
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        message = Mail(from_email=MAIL_FROM, to_emails=to_email, subject=subject, html_content=html_content)
        resp = sg.send(message)
        logger.info(f"Email sent: status {resp.status_code}")
    except Exception:
        logger.exception("Failed to send email")

def main():
    run_tests()
    train_model()
    model, scaler = load_model()
    picks = build_cheat_sheet(model, scaler)
    if not picks:
        logger.info("No picks generated")
        return
    subject, text, html = format_email(picks)
    send_email(subject, html, NOTIFY_EMAIL)
    logger.info("Pipeline completed")

if __name__ == "__main__":
    main()
