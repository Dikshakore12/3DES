# crypto_utils.py
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
import hashlib, json, os
from datetime import datetime

# ---------- Constants ----------
PBKDF2_ITERATIONS = 200_000
KEY_SIZE = 32  # AES-256
SALT_SIZE = 16
NONCE_SIZE = 12  # AES-GCM recommended
TAG_SIZE = 16

# ---------- Password-based key derivation ----------
def derive_key_from_password(password: str, salt: bytes = None) -> bytes:
    """
    Derive a 256-bit AES key from a password using PBKDF2.
    Returns (key, salt). If salt is None, generates a new random salt.
    """
    if salt is None:
        salt = get_random_bytes(SALT_SIZE)
    key = PBKDF2(password.encode(), salt, dkLen=KEY_SIZE, count=PBKDF2_ITERATIONS, hmac_hash_module=SHA256)
    return key, salt

# ---------- File hashing ----------
def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# ---------- AES-GCM Encryption / Decryption ----------
def encrypt_file(input_path: str, output_path: str, key: bytes) -> None:
    cipher = AES.new(key, AES.MODE_GCM, nonce=get_random_bytes(NONCE_SIZE))
    nonce = cipher.nonce
    with open(input_path, "rb") as f:
        plaintext = f.read()
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    with open(output_path, "wb") as f:
        f.write(nonce + tag + ciphertext)

def decrypt_file(input_path: str, output_path: str, key: bytes) -> None:
    with open(input_path, "rb") as f:
        blob = f.read()
    nonce = blob[:NONCE_SIZE]
    tag = blob[NONCE_SIZE:NONCE_SIZE+TAG_SIZE]
    ciphertext = blob[NONCE_SIZE+TAG_SIZE:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    with open(output_path, "wb") as f:
        f.write(plaintext)

# ---------- Advanced Blockchain Implementation ----------
class Blockchain:
    def __init__(self):
        self.chain = []
        self.difficulty = 4  # Proof of work difficulty (number of leading zeros)
        self.pending_transactions = []
        self.create_block(data="Genesis Block", previous_hash="0")
        
    @staticmethod
    def _hash_block(block: dict) -> str:
        temp = dict(block)
        temp["hash"] = ""
        encoded = json.dumps(temp, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()
    
    def proof_of_work(self, block: dict) -> int:
        """Implements a simple proof of work algorithm"""
        nonce = 0
        block_copy = dict(block)
        
        while True:
            block_copy["nonce"] = nonce
            block_hash = self._hash_block(block_copy)
            if block_hash.startswith('0' * self.difficulty):
                return nonce
            nonce += 1
    
    def create_block(self, data, previous_hash: str):
        block = {
            "index": len(self.chain) + 1,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "data": data,
            "previous_hash": previous_hash,
            "nonce": 0,
            "hash": "",
            "transactions": self.pending_transactions.copy()
        }
        
        # Apply proof of work
        block["nonce"] = self.proof_of_work(block)
        block["hash"] = self._hash_block(block)
        
        # Reset pending transactions and add block to chain
        self.pending_transactions = []
        self.chain.append(block)
        return block
    
    def add_transaction(self, sender: str, recipient: str, file_info: dict):
        """Add a new transaction to the list of pending transactions"""
        transaction = {
            "sender": sender,
            "recipient": recipient,
            "file_info": file_info,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "signature": self._create_signature(sender, recipient, file_info)
        }
        self.pending_transactions.append(transaction)
        return self.last()["index"] + 1
    
    def _create_signature(self, sender: str, recipient: str, file_info: dict) -> str:
        """Create a digital signature for the transaction"""
        data = f"{sender}{recipient}{json.dumps(file_info, sort_keys=True)}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def last(self):
        return self.chain[-1]
    
    def verify_chain(self) -> bool:
        for i in range(1, len(self.chain)):
            prev = self.chain[i-1]
            curr = self.chain[i]
            
            # Verify previous hash reference
            if curr["previous_hash"] != prev["hash"]:
                return False
            
            # Verify block hash integrity
            if curr["hash"] != self._hash_block(curr):
                return False
            
            # Verify proof of work
            block_copy = dict(curr)
            if not curr["hash"].startswith('0' * self.difficulty):
                return False
        
        return True
    
    def contains_enc_hash(self, enc_hash: str) -> bool:
        # Check in main blocks
        for block in self.chain:
            data = block.get("data", {})
            if isinstance(data, dict) and data.get("enc_hash") == enc_hash:
                return True
            
            # Also check in transactions
            for tx in block.get("transactions", []):
                file_info = tx.get("file_info", {})
                if file_info.get("enc_hash") == enc_hash:
                    return True
        
        return False
    
    def get_file_history(self, filename: str) -> list:
        """Get the complete history of a file in the blockchain"""
        history = []
        
        for block in self.chain:
            # Check in block data
            data = block.get("data", {})
            if isinstance(data, dict) and data.get("filename") == filename:
                history.append({
                    "block_index": block["index"],
                    "timestamp": block["timestamp"],
                    "action": "file_encrypted",
                    "details": data
                })
            
            # Check in transactions
            for tx in block.get("transactions", []):
                file_info = tx.get("file_info", {})
                if file_info.get("filename") == filename:
                    history.append({
                        "block_index": block["index"],
                        "timestamp": block["timestamp"],
                        "action": "file_transferred",
                        "sender": tx.get("sender"),
                        "recipient": tx.get("recipient"),
                        "details": file_info
                    })
        
        return history
