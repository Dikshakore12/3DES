# scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
import atexit
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
from datetime import datetime

# ---------- Scheduler ----------
scheduler = BackgroundScheduler()
scheduler.start()  # start background scheduler
atexit.register(lambda: scheduler.shutdown())  # graceful shutdown on exit

# ---------- Schedule email ----------
def schedule_email(to_email, subject, body, attachment_path, send_time):
    """
    Schedule an email to be sent at a specific datetime.
    
    :param to_email: Recipient email
    :param subject: Email subject
    :param body: Email body text
    :param attachment_path: Path to the file to attach
    :param send_time: datetime object for when to send
    :return: job id
    """
    # Generate a unique job ID first
    import uuid
    job_id = str(uuid.uuid4())
    
    # Store job information immediately so users can track scheduled emails
    email_status_db[job_id] = {
        "to_email": to_email,
        "recipient": to_email,  # For frontend consistency
        "subject": subject,
        "scheduled_time": send_time.isoformat(),
        "status": "scheduled",
        "attachment_path": attachment_path
    }
    
    trigger = DateTrigger(run_date=send_time)
    job = scheduler.add_job(send_email, trigger=trigger,
                            args=[to_email, subject, body, [attachment_path], job_id])
    
    return job_id

# ---------- Email Status Tracking ----------
email_status_db = {}

# ---------- Send email ----------
def send_email(to_email, subject, body, attachments=[], job_id=None):
    """
    Sends an email with optional attachments and tracks delivery status.
    """
    sender_email = os.getenv("EMAIL_USER")      # load from .env
    sender_password = os.getenv("EMAIL_PASS")   # load from .env

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # Add message ID for tracking
    message_id = f"<{job_id or os.urandom(16).hex()}@securefiletransfer.app>"
    msg['Message-ID'] = message_id
    
    # Add delivery receipt request
    msg['Disposition-Notification-To'] = sender_email
    msg['Return-Receipt-To'] = sender_email

    # Body
    msg.attach(MIMEText(body, 'plain'))

    # Attach files
    for file_path in attachments:
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
                part['Content-Disposition'] = f'attachment; filename="%s"' % os.path.basename(file_path)
                msg.attach(part)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
            # Update status database - preserve existing info and add sent details
            if job_id and job_id in email_status_db:
                # Preserve existing job info (like scheduled_time, recipient, etc.)
                email_status_db[job_id].update({
                    "sent_time": datetime.now().isoformat(),
                    "status": "sent",
                    "delivery_confirmed": False,
                    "message_id": message_id
                })
            else:
                # Fallback for jobs not in database
                status_info = {
                    "to_email": to_email,
                    "subject": subject,
                    "sent_time": datetime.now().isoformat(),
                    "status": "sent",
                    "delivery_confirmed": False,
                    "message_id": message_id
                }
                if job_id:
                    email_status_db[job_id] = status_info
                
            print(f"✅ Email sent successfully to {to_email}")
            return True, message_id
    except Exception as e:
        error_msg = f"❌ Error sending email: {e}"
        print(error_msg)
        
        # Update status database with error - preserve existing info
        if job_id and job_id in email_status_db:
            # Preserve existing job info and add error details
            email_status_db[job_id].update({
                "sent_time": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
        elif job_id:
            # Fallback for jobs not in database
            email_status_db[job_id] = {
                "to_email": to_email,
                "subject": subject,
                "sent_time": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            }
            
        return False, error_msg

# ---------- Get email status ----------
def get_email_status(job_id):
    """
    Get the status of a scheduled email by job ID.
    """
    # First check if we have a record in our status database
    if job_id in email_status_db:
        status_data = email_status_db[job_id]
        # Make sure recipient field is set for frontend consistency
        if 'to_email' in status_data and 'recipient' not in status_data:
            status_data['recipient'] = status_data['to_email']
        return status_data
    
    # Check if job exists in scheduler
    job = scheduler.get_job(job_id)
    if job:
        next_run = job.next_run_time.isoformat() if job.next_run_time else None
        return {
            "status": "scheduled",
            "next_run": next_run
        }
    
    # If we get here, the job ID is not recognized
    return {"status": "unknown", "message": "No email found with this job ID"}

def cancel_scheduled_email(job_id, reason=None):
    """
    Cancel a scheduled email before it is sent and notify the recipient.
    Returns a dict describing the outcome.
    """
    # Look up job information
    job = scheduler.get_job(job_id)
    record = email_status_db.get(job_id)

    # If the email has already been sent, cannot cancel
    if record and record.get("status") == "sent":
        return {
            "status": "already_sent",
            "message": "Email was already sent and cannot be cancelled.",
            "job_id": job_id
        }

    # Remove the scheduled job if it exists
    if job:
        try:
            scheduler.remove_job(job_id)
        except Exception as e:
            # Proceed to mark as cancelled even if removal raises
            pass

    # Update local status record
    if record:
        record.update({
            "status": "cancelled",
            "cancelled_time": datetime.now().isoformat(),
            "cancellation_reason": reason or "Cancelled by sender"
        })
    else:
        # Create minimal record if none exists
        email_status_db[job_id] = {
            "status": "cancelled",
            "cancelled_time": datetime.now().isoformat(),
            "cancellation_reason": reason or "Cancelled by sender"
        }

    # Send a cancellation notice immediately (do not attach files)
    to_email = record.get("to_email") if record else None
    scheduled_time = record.get("scheduled_time") if record else None
    if to_email:
        subject = "Cancellation Notice: Encrypted File Delivery"
        body_lines = [
            "Dear recipient,",
            "",
            "The previously scheduled encrypted file delivery has been cancelled.",
        ]
        if scheduled_time:
            body_lines.append(f"Originally scheduled for: {scheduled_time}")
        if reason:
            body_lines.append(f"Reason: {reason}")
        body_lines.append("")
        body_lines.append("If this was a postponement, a new schedule will be shared.")
        body = "\n".join(body_lines)

        # Send without referencing the original job_id to avoid status override
        send_ok, _ = send_email(to_email, subject, body, attachments=[], job_id=None)
        email_status_db[job_id]["notification_sent"] = bool(send_ok)
        email_status_db[job_id]["notification_time"] = datetime.now().isoformat()

    return {
        "status": "cancelled",
        "message": "Scheduled email cancelled and recipient notified.",
        "job_id": job_id
    }
