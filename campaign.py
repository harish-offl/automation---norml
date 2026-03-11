import csv
import time

from smtp_sender import send_email
from personalization import personalize_email
from config import DELAY_BETWEEN_EMAILS

def run_campaign():
    with open("templates/email_template.txt") as f:
        template = f.read()
    
    with open("leads.csv") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            email_content = personalize_email(template, row)
            
            lines = email_content.split("\n")
            subject = lines[0].replace("Subject: ", "")
            body = "\n".join(lines[1:])
            
            send_email(row["email"], subject, body)
            
            print("Email sent to:", row["email"])
            
            time.sleep(DELAY_BETWEEN_EMAILS)
