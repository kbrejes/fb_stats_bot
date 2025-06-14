"""
Security utilities for the application.
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config.settings import ENCRYPTION_KEY
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TokenEncryptor:
    """
    Handles encryption and decryption of sensitive data using Fernet.
    """

    def __init__(self, key: str = ENCRYPTION_KEY):
        """
        Initialize the encryptor with a key.

        Args:
            key: The encryption key (should be 32 url-safe base64-encoded bytes).
        """
        try:
            # Derive a key from the provided string
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"facebook_ads_bot_salt",  # Static salt for simplicity
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
            self.fernet = Fernet(derived_key)
        except Exception as e:
            logger.error(f"Failed to initialize TokenEncryptor: {str(e)}")
            raise ValueError("Invalid encryption key format") from e

    def encrypt(self, data: str) -> str:
        """
        Encrypt a string.

        Args:
            data: The string to encrypt.

        Returns:
            The encrypted string in base64 format.
        """
        if not data:
            return ""

        try:
            encrypted = self.fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            raise ValueError("Encryption failed") from e

    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted_data: The encrypted string in base64 format.

        Returns:
            The decrypted string.
        """
        if not encrypted_data:
            return ""

        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            raise ValueError("Decryption failed") from e


# Singleton instance
encryptor = TokenEncryptor()


def encrypt_token(token: str) -> str:
    """
    Encrypt a token.

    Args:
        token: The token to encrypt.

    Returns:
        The encrypted token.
    """
    return encryptor.encrypt(token)


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt a token.

    Args:
        encrypted_token: The encrypted token.

    Returns:
        The decrypted token.
    """
    return encryptor.decrypt(encrypted_token)
