# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import atexit
import os
from datetime import datetime
import base64
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

# ---------- Scheduler ----------
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ---------- Email Status Tracking ----------
email_status_db = {}

# ---------- Send Email via SendGrid ----------
def send_email(to_email, subject, body, attachments=[], job_id=None):
    """
    Send an email with optional attachments using SendGrid.
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        print("❌ Missing SENDGRID_API_KEY in environment variables")
        return False, "Missing API key"

    sender_email = "no-reply@paperprotection.app"  # Change if you have verified domain
    message = Mail(
        from_email=("Paper Protection System", sender_email),
        to_emails=to_email,
        subject=subject,
        plain_text_content=body
    )

    # Attach files (if any)
    for file_path in attachments:
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                data = f.read()
                encoded_file = base64.b64encode(data).decode()
            attached_file = Attachment(
                FileContent(encoded_file),
                FileName(os.path.basename(file_path)),
                FileType("application/octet-stream"),
                Disposition("attachment")
            )
            message.attachment = attached_file

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"✅ Email sent to {to_email} (status {response.status_code})")

        # Update email status
        if job_id and job_id in email_status_db:
            email_status_db[job_id].update({
                "sent_time": datetime.now().isoformat(),
                "status": "sent",
                "response_code": response.status_code
            })
        else:
            email_status_db[job_id] = {
                "to_email": to_email,
                "subject": subject,
                "sent_time": datetime.now().isoformat(),
                "status": "sent",
                "response_code": response.status_code
            }
        return True, response.status_code

    except Exception as e:
        print(f"❌ SendGrid error: {e}")
        if job_id and job_id in email_status_db:
            email_status_db[job_id].update({
                "sent_time": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
        else:
            email_status_db[job_id] = {
                "to_email": to_email,
                "subject": subject,
                "sent_time": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
        return False, str(e)


# ---------- Schedule Email ----------
def schedule_email(to_email, subject, body, attachment_path, send_time):
    """
    Schedule an email to be sent at a specific datetime using SendGrid.
    """
    import uuid
    job_id = str(uuid.uuid4())

    email_status_db[job_id] = {
        "to_email": to_email,
        "recipient": to_email,
        "subject": subject,
        "scheduled_time": send_time.isoformat(),
        "status": "scheduled",
        "attachment_path": attachment_path
    }

    trigger = DateTrigger(run_date=send_time)
    scheduler.add_job(send_email, trigger=trigger,
                      args=[to_email, subject, body, [attachment_path], job_id])

    return job_id


# ---------- Get Email Status ----------
def get_email_status(job_id):
    """
    Get the status of a scheduled email by job ID.
    """
    if job_id in email_status_db:
        data = email_status_db[job_id]
        if 'to_email' in data and 'recipient' not in data:
            data['recipient'] = data['to_email']
        return data

    job = scheduler.get_job(job_id)
    if job:
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        return {"status": "scheduled", "next_run": next_run}

    return {"status": "unknown", "message": "No email found with this job ID"}
