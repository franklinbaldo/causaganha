import tempfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from src.security_utils import (
    decrypt_file,
    encrypt_file,
    generate_key,
    verify_pdf_signature,
)


def test_encrypt_decrypt_roundtrip(tmp_path: Path):
    key = generate_key()
    original_file = tmp_path / "data.txt"
    original_file.write_text("secret-data")

    encrypt_file(original_file, key)
    # Ensure file was encrypted
    assert original_file.read_text() != "secret-data"

    decrypt_file(original_file, key)
    assert original_file.read_text() == "secret-data"


def test_verify_pdf_signature(tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"pdf-content")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    signature = private_key.sign(
        pdf.read_bytes(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256(),
    )

    pubkey = private_key.public_key()
    pubkey_path = tmp_path / "public.pem"
    pubkey_path.write_bytes(
        pubkey.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    sig_path = tmp_path / "sample.sig"
    sig_path.write_bytes(signature)

    assert verify_pdf_signature(pdf, sig_path, pubkey_path)
