import csv
import time

from smtp_sender import send_email
from ai_engine import generate_cold_email
from config import DELAY_BETWEEN_EMAILS

# Django should already be configured by the time this module is imported


def run_campaign(use_csv_fallback=True):
    """Send uniquely generated cold emails to leads.
    Pulls leads from Django DB and optionally falls back to CSV.
    """
    from app.models import Lead

    leads = []
    # Try to get leads from the database
    try:
        db_leads = Lead.objects.all()
        if db_leads.exists():
            leads = [
                {
                    "name": lead.name or "",
                    "email": lead.email,
                    "niche": lead.niche or "",
                    "industry": lead.industry or "",
                    "phone": lead.phone or "",
                    "company": lead.company or "",
                }
                for lead in db_leads
            ]
    except Exception as e:
        print(f"Could not fetch leads from DB: {e}, falling back to CSV")

    # Fallback to CSV if DB is empty or unavailable
    if not leads and use_csv_fallback:
        try:
            with open("leads.csv") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    leads.append(row)
        except FileNotFoundError:
            print("No leads.csv file found and no leads in database")
            return
    elif not leads:
        print("No leads found in database; campaign not started")
        return

    for row in leads:
        solution = (row.get("niche") or "").strip()
        if not solution:
            print(f"Skipped {row.get('email', 'unknown')}: missing solution/niche")
            continue

        email_content = generate_cold_email(row)

        lines = email_content.split("\n")
        subject = lines[0].replace("Subject: ", "")
        body = "\n".join(lines[1:])

        send_email(row["email"], subject, body)

        print("Email sent to:", row["email"])

        time.sleep(DELAY_BETWEEN_EMAILS)
