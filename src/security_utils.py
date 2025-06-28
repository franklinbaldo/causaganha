"""Utility functions for basic security tasks."""

from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def generate_key() -> bytes:
    """Return a new random key for symmetric encryption."""
    return Fernet.generate_key()


def encrypt_file(
    file_path: Path, key: bytes, output_path: Optional[Path] = None
) -> Path:
    """Encrypt a file in-place or to a new location using Fernet."""
    output_path = output_path or file_path
    f = Fernet(key)
    data = file_path.read_bytes()
    output_path.write_bytes(f.encrypt(data))
    return output_path


def decrypt_file(
    file_path: Path, key: bytes, output_path: Optional[Path] = None
) -> Path:
    """Decrypt a file encrypted with :func:`encrypt_file`."""
    output_path = output_path or file_path
    f = Fernet(key)
    data = file_path.read_bytes()
    output_path.write_bytes(f.decrypt(data))
    return output_path


def verify_pdf_signature(
    pdf_path: Path, signature_path: Path, public_key_path: Path
) -> bool:
    """Verify an RSA signature for a PDF file."""
    data = pdf_path.read_bytes()
    signature = signature_path.read_bytes()
    public_key = serialization.load_pem_public_key(public_key_path.read_bytes())
    try:
        public_key.verify(
            signature,
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
