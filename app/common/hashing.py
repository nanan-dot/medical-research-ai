"""Streaming file hashing utilities."""

from hashlib import sha256
from pathlib import Path

HASH_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path, chunk_size: int = HASH_CHUNK_SIZE) -> str:
    """Hash a file in bounded chunks so large files are never loaded into memory."""
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()
