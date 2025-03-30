from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from Crypto.Cipher import DES3
from Crypto.Random import get_random_bytes
import os, smtplib, threading, time, mimetypes
from email.message import EmailMessage
from datetime import datetime

from dotenv import load_dotenv
load_dotenv('pass.env')  # Add the filename here



app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ENCRYPTED_FOLDER = 'encrypted'
DECRYPTED_FOLDER = 'decrypted'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ENCRYPTED_FOLDER, exist_ok=True)
os.makedirs(DECRYPTED_FOLDER, exist_ok=True)

# Generate encryption key with proper parity
key = DES3.adjust_key_parity(get_random_bytes(24))

# Encrypt the file using Triple DES
def encrypt_file(filepath, encrypted_path):
    cipher = DES3.new(key, DES3.MODE_EAX)
    with open(filepath, 'rb') as f:
        plaintext = f.read()
    nonce = cipher.nonce
    ciphertext = cipher.encrypt(plaintext)
    with open(encrypted_path, 'wb') as f:
        f.write(nonce + ciphertext)

# Decrypt the file using Triple DES
def decrypt_file(encrypted_path, decrypted_path):
    with open(encrypted_path, 'rb') as f:
        nonce = f.read(16)
        ciphertext = f.read()
    cipher = DES3.new(key, DES3.MODE_EAX, nonce=nonce)
    plaintext = cipher.decrypt(ciphertext)
    with open(decrypted_path, 'wb') as f:
        f.write(plaintext)

# Send email at a specific time with error handling
def send_email_later(to_email, subject, body, file_path, send_time):
    def send():
        try:
            now = datetime.now()
            delay = (send_time - now).total_seconds()
            if delay > 0:
                time.sleep(delay)

            msg = EmailMessage()
            msg['Subject'] = subject
            msg['From'] = 'korediksha30@gmail.com'
            msg['To'] = to_email
            msg.set_content(body)

            mime_type, _ = mimetypes.guess_type(file_path)
            mime_type, mime_subtype = mime_type.split('/')

            with open(file_path, 'rb') as f:
                msg.add_attachment(f.read(), maintype=mime_type, subtype=mime_subtype, filename=os.path.basename(file_path))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login('korediksha30@gmail.com', os.getenv("APP_PASSWORD"))
                smtp.send_message(msg)

            print("✅ Email sent successfully!")

        except Exception as e:
            print("❌ Error sending email:", e)

    threading.Thread(target=send).start()

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Encrypt file and schedule email
@app.route('/encrypt', methods=['POST'])
def encrypt():
    file = request.files['file']
    to_email = request.form['email']
    date = request.form['date']
    time_input = request.form['time']
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    encrypted_path = os.path.join(ENCRYPTED_FOLDER, 'enc_' + filename)
    encrypt_file(filepath, encrypted_path)

    send_time = datetime.strptime(date + ' ' + time_input, '%Y-%m-%d %H:%M')
    send_email_later(to_email, 'Encrypted File', 'Please find the encrypted file attached.', encrypted_path, send_time)

    return '✅ File encrypted and email scheduled!'

# Decrypt uploaded file
@app.route('/decrypt', methods=['POST'])
def decrypt():
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    decrypted_path = os.path.join(DECRYPTED_FOLDER, 'dec_' + filename)
    decrypt_file(filepath, decrypted_path)

    return send_file(decrypted_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
