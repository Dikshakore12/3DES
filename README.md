# Paper Protection System (PPS)

Securely encrypt, schedule, and deliver documents with blockchain-backed integrity. PPS is a Flask application that combines modern UI, email scheduling, and a simple blockchain ledger to verify files.

## Features
- Encrypt and schedule delivery of files via email (PDF/DOCX/TXT).
- Blockchain verification of encrypted files (hash recorded on-chain in-app).
- Status tracking for scheduled emails by `job_id`.
- Cancel scheduled deliveries with immediate cancellation notice email.
- Upcoming deliveries panel sourced from a server endpoint.
- Modern dashboard UI with dark/light theme toggle and animated stats.

## Quick Start (Windows)
1. Clone or open this folder in your IDE.
2. Create a virtual environment (optional if `.venv` already exists):
   - `python -m venv .venv`
   - Activate: `./.venv/Scripts/Activate.ps1`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Configure email credentials in `pass.env` (Gmail account with App Password recommended):
   ```
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_app_password
   ```
5. Run the app:
   - Using Flask CLI: `./.venv/Scripts/flask.exe --app app run`
   - Or Python directly: `./.venv/Scripts/python.exe app.py`
6. Open the app at `http://127.0.0.1:5000/`.

## Usage
### Encrypt & Schedule
- Go to “Encrypt & Schedule”, select a file, set a password, recipient email, date and time (e.g., 10 days later), then submit.
- You’ll receive a `job_id` for tracking.

### Check Status
- In “History”, enter the `job_id` and click “Check Status”.
- The status card shows `scheduled`, `sent`, or `failed` and relevant timestamps.

### Cancel a Scheduled Delivery
- If a paper is postponed or cancelled, use “Cancel Scheduled Delivery”.
- Enter the `job_id` and optional reason, then “Cancel Delivery & Notify”.
- The future send is removed and an immediate cancellation email is sent to the recipient.

### Upcoming Deliveries
- The dashboard shows an “Upcoming Deliveries” card listing jobs that are scheduled.
- Click “Cancel” next to an item to prefill the cancellation form.

### Theme Toggle
- Use the top-nav button to switch between dark and light themes.
- Preference persists via `localStorage` (`pps-theme`).

## API Endpoints
- `POST /encrypt` — Encrypt and schedule a file (handled by the UI form).
- `POST /decrypt` — Decrypt a previously encrypted file.
- `GET /download/<filename>` — Download a decrypted file.
- `GET /email-status/<job_id>` — Check status for a scheduled email.
- `POST /cancel-email` — Cancel a scheduled email and notify recipient; body `{job_id, reason?}`.
- `GET /upcoming` — List upcoming scheduled deliveries.
- `GET /blockchain` — Inspect the in-app blockchain.
- `GET /health` — Health check.

## Project Structure
```
app.py               # Flask routes and app wiring
scheduler.py         # APScheduler setup, email send, status, and cancellation
crypto_utils.py      # Key derivation, encrypt/decrypt, file hashing, Blockchain
templates/index.html # UI layout (Dashboard, Encrypt, Decrypt, History)
static/style.css     # Styles, themes, grid layout, progress bars
static/script.js     # UI interactions, status checks, upcoming panel, theme toggle
pass.env             # Email credentials (loaded on startup)
uploads/             # Uploaded originals
encrypted/           # Encrypted files and .salt files
decrypted/           # Decrypted outputs
```

## Configuration
- Email: PPS uses Gmail SMTP (`smtp.gmail.com:587`). Set `EMAIL_USER` and `EMAIL_PASS` in `pass.env`.
- Scheduler: APScheduler runs in background; jobs exist in memory. A persistence layer can be added if needed.

## Security Notes
- Use strong passwords for encryption.
- Prefer Gmail App Passwords over plain account passwords.
- The in-app blockchain demonstrates integrity verification but isn’t a public chain; do not treat it as a tamper-proof distributed ledger.

## Troubleshooting
- “Missing salt for decryption”: Ensure the `.salt` file exists next to the encrypted file.
- Emails not sending: Verify `pass.env` values and allow SMTP/App Password for the account.
- Upcoming list empty: Only shows jobs scheduled during the current server session (in-memory). Add persistence if you need it to survive restarts.

## Roadmap Ideas
- Reschedule endpoint and UI (postponements).
- Persistent job store (SQLite/JSON).
- Role-based access and audit logs.