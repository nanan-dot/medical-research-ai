from hashlib import sha256

from app.common.hashing import sha256_file


def test_sha256_file_reads_large_input_in_chunks(tmp_path):
    content = b"0123456789abcdef" * 200_000
    path = tmp_path / "large.pdf"
    path.write_bytes(content)
    assert sha256_file(path, chunk_size=4096) == sha256(content).hexdigest()
