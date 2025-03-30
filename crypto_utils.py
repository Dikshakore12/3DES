from Crypto.Cipher import DES3
from Crypto.Random import get_random_bytes
import base64

def pad(text):
    while len(text) % 8 != 0:
        text += ' '
    return text

# Use a fixed key for now (24 bytes)
key = DES3.adjust_key_parity(get_random_bytes(24))

def encrypt_3des(data, key):
    cipher = DES3.new(key, DES3.MODE_ECB)
    padded_data = pad(data)
    encrypted = cipher.encrypt(padded_data.encode('utf-8'))
    return base64.b64encode(encrypted).decode('utf-8')
