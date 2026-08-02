"""Application-key encryption with read-compatible key rotation."""

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from app.common.exceptions import ConflictError
from app.core.config import settings


class SecretCipher:
    def __init__(self, keys: str | None = None):
        values = [
            value.strip().encode()
            for value in (
                keys if keys is not None else settings.MODEL_CONFIG_ENCRYPTION_KEYS
            ).split(",")
            if value.strip()
        ]
        if not values:
            raise ConflictError("Model configuration encryption key is not configured")
        try:
            self.cipher = MultiFernet([Fernet(value) for value in values])
        except (ValueError, TypeError) as exc:
            raise ConflictError("Model configuration encryption key is invalid") from exc

    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        try:
            return self.cipher.decrypt(value.encode()).decode()
        except (InvalidToken, ValueError) as exc:
            raise ConflictError(
                "Stored model key cannot be decrypted; check rotated application keys"
            ) from exc

    def rotate(self, value: str) -> str:
        try:
            return self.cipher.rotate(value.encode()).decode()
        except InvalidToken as exc:
            raise ConflictError("Stored model key cannot be rotated") from exc
