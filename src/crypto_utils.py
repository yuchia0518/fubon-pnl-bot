import base64
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding


def _get_key_bytes(key_hex: str) -> bytes:
    return bytes.fromhex(key_hex)


def encrypt(plain_text: str, key_hex: str) -> str:
    key = _get_key_bytes(key_hex)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plain_text.encode('utf-8')) + padder.finalize()

    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    combined = iv + ciphertext
    return base64.b64encode(combined).decode('utf-8')


def decrypt(cipher_text_b64: str, key_hex: str) -> str:
    key = _get_key_bytes(key_hex)
    combined = base64.b64decode(cipher_text_b64.encode('utf-8'))
    iv = combined[:16]
    ciphertext = combined[16:]

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()

    decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    decrypted = unpadder.update(decrypted_padded) + unpadder.finalize()
    return decrypted.decode('utf-8')
