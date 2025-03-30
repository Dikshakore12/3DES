
from apscheduler.schedulers.background import BackgroundScheduler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import datetime
import os

scheduler = BackgroundScheduler()
scheduler.start()

def send_email(content, to_email):
    # Save the encrypted content to a file
    filename = "encrypted_paper.txt"
    with open(filename, "w") as f:
        f.write(content)

    # Construct the email
    msg = MIMEMultipart()
    msg['Subject'] = 'Encrypted Paper'
    msg['From'] = 'your-email@gmail.com'
    msg['To'] = to_email

    # Attach a simple message
    body = MIMEText("Please find the encrypted paper attached.", "plain")
    msg.attach(body)

    # Attach the file
    with open(filename, "rb") as f:
        part = MIMEApplication(f.read(), Name=filename)
        part['Content-Disposition'] = f'attachment; filename="{filename}"'
        msg.attach(part)

    # Send email
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('your-email@gmail.com', 'your-password')  # Use app password for security
        smtp.send_message(msg)

    # Clean up file
    os.remove(filename)

def schedule_email(content, to_email, datetime_str):
    run_time = datetime.datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M')
    scheduler.add_job(send_email, 'date', run_date=run_time, args=[content, to_email])
