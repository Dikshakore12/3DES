# app.py
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv("pass.env")  # expects EMAIL_USER, EMAIL_PASS

from crypto_utils import (
    derive_key_from_password,
    encrypt_file,
    decrypt_file,
    hash_file,
    Blockchain,
)
from scheduler import schedule_email, scheduler  # <- scheduler object

# ---------- Flask setup ----------
app = Flask(__name__)
BASE = os.path.dirname(os.path.abspath(__file__))

UPLOADS = os.path.join(BASE, "uploads")
ENCRYPTED = os.path.join(BASE, "encrypted")
DECRYPTED = os.path.join(BASE, "decrypted")
os.makedirs(UPLOADS, exist_ok=True)
os.makedirs(ENCRYPTED, exist_ok=True)
os.makedirs(DECRYPTED, exist_ok=True)

# ---------- Blockchain ----------
chain = Blockchain()

@app.route("/")
def index():
    return render_template("index.html")

# ---------- File History ----------
@app.route("/file-history/<filename>")
def file_history(filename):
    history = chain.get_file_history(filename)
    return jsonify({"history": history})

# ---------- Schedule email ----------
@app.route("/encrypt", methods=["POST"])
def route_encrypt():
    try:
        f = request.files.get("file")
        password = request.form.get("password", "").strip()
        to_email = request.form.get("email", "").strip()
        date_str = request.form.get("date", "")
        time_str = request.form.get("time", "")

        if not (f and password and to_email and date_str and time_str):
            return jsonify({"status": "error", "message": "Missing inputs"}), 400

        # ✅ derive key + generate random salt
        key, salt = derive_key_from_password(password)

        filename = secure_filename(f.filename)
        src_path = os.path.join(UPLOADS, filename)
        f.save(src_path)

        enc_name = f"enc_" + filename
        enc_path = os.path.join(ENCRYPTED, enc_name)
        encrypt_file(src_path, enc_path, key)

        # store salt alongside encrypted file
        with open(enc_path + ".salt", "wb") as sf:
            sf.write(salt)

        # blockchain record
        enc_hash = hash_file(enc_path)
        chain.create_block(
            data={
                "filename": filename,
                "encrypted_file": enc_name,
                "enc_hash": enc_hash,
                "email": to_email,
                "scheduled_for": f"{date_str} {time_str}"
            },
            previous_hash=chain.last()["hash"]
        )

        # schedule email
        send_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        subject = "Encrypted File (Blockchain Verified)"
        body = f"""Your encrypted file is attached.

Blockchain:
 - Hash: {enc_hash}
 - Filename: {enc_name}
 - Scheduled For: {send_time}

(This email was auto-sent by PPS)
"""
        job_id = schedule_email(to_email, subject, body, enc_path, send_time)

        return jsonify({
            "status": "success",
            "message": f"Encrypted, recorded on blockchain, and scheduled email (job: {job_id})",
            "file": enc_name,
            "job_id": job_id,
            "email_status_url": f"/email-status/{job_id}"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Exception: {e}"}), 500


# ---------- Decrypt ----------
@app.route("/decrypt", methods=["POST"])
def route_decrypt():
    try:
        f = request.files.get("file")
        password = request.form.get("password", "").strip()

        if not (f and password):
            return jsonify({"status": "error", "message": "Missing file or password"}), 400

        filename = secure_filename(f.filename)
        src_path = os.path.join(UPLOADS, filename)
        f.save(src_path)

        # read corresponding salt file
        salt_path = os.path.join(ENCRYPTED, filename + ".salt")
        if not os.path.exists(salt_path):
            return jsonify({"status": "error", "message": "Missing salt for decryption"}), 400

        with open(salt_path, "rb") as sf:
            salt = sf.read()

        key, _ = derive_key_from_password(password, salt)

        # verify blockchain
        enc_hash = hash_file(src_path)
        if not chain.contains_enc_hash(enc_hash):
            return jsonify({"status": "error", "message": "File integrity could not be verified on blockchain!"}), 400

        dec_name = f"dec_" + filename
        dec_path = os.path.join(DECRYPTED, dec_name)

        decrypt_file(src_path, dec_path, key)

        return jsonify({
            "status": "success",
            "message": "File decrypted successfully",
            "download_url": f"/download/{dec_name}"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"Decryption failed / Exception: {e}"}), 500



# ---------- Download decrypted file ----------
@app.route("/download/<filename>")
def download_file(filename):
    path = os.path.join(DECRYPTED, filename)
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "❌ File not found", 404

# ---------- Email Status ----------
@app.route("/email-status/<job_id>")
def email_status(job_id):
    """Get the status of a scheduled email"""
    from scheduler import get_email_status
    status = get_email_status(job_id)
    return jsonify(status)

# ---------- Inspect chain ----------
@app.route("/blockchain", methods=["GET"])
def route_chain():
    ok = chain.verify_chain()
    return jsonify({"valid": ok, "length": len(chain.chain), "chain": chain.chain})

@app.route("/health")
def health():
    return "OK", 200
    app.run(debug=True)
