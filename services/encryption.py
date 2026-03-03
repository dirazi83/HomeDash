from cryptography.fernet import Fernet
from django.conf import settings

def get_cipher():
    key = settings.ENCRYPTION_KEY.encode()
    return Fernet(key)

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(value.encode())
    return encrypted_bytes.decode('utf-8')

def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    cipher = get_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_value.encode('utf-8'))
    return decrypted_bytes.decode('utf-8')
