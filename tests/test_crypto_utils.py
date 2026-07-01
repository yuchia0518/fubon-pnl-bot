import pytest
from src.crypto_utils import encrypt, decrypt


def test_encrypt_decrypt():
    master_key_hex = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    original_text = "F123456789"

    encrypted = encrypt(original_text, master_key_hex)
    assert encrypted != original_text

    decrypted = decrypt(encrypted, master_key_hex)
    assert decrypted == original_text
