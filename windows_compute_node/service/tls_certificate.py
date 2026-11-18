"""Generate a private self-signed LAN certificate using the Node's bundled Python dependencies.

Only called after the user has enabled LAN and configured web credentials.
The certificate is self-signed: browsers will show a trust warning until the
certificate is explicitly trusted. Never publish the private key.
"""

from __future__ import annotations

import datetime as dt
import ipaddress
import os
import secrets
from pathlib import Path


def ensure_lan_certificate(security_dir: Path, host: str) -> tuple[Path, Path]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    address = ipaddress.IPv4Address(host)
    security_dir = Path(security_dir)
    cert_path = security_dir / "lan_tls.crt"
    key_path = security_dir / "lan_tls.key"
    if cert_path.is_file() and key_path.is_file():
        try:
            cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
            key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
            if address in cert.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value.get_values_for_type(x509.IPAddress):
                # Validate that certificate and private key really match.
                if cert.public_key().public_numbers() == key.public_key().public_numbers():
                    if cert.not_valid_after_utc > dt.datetime.now(dt.UTC) + dt.timedelta(days=7):
                        return cert_path, key_path
        except (ValueError, OSError, TypeError, x509.ExtensionNotFound):
            pass

    security_dir.mkdir(parents=True, exist_ok=True)
    private_key = ec.generate_private_key(ec.SECP256R1())
    now = dt.datetime.now(dt.UTC)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "MediaHub Compute Node LAN")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(address)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    # Avoid .bak files and ensure the private key is not world-readable.
    key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_bytes = certificate.public_bytes(serialization.Encoding.PEM)
    suffix = secrets.token_hex(8)
    key_tmp = security_dir / ("lan_tls." + suffix + ".key.tmp")
    cert_tmp = security_dir / ("lan_tls." + suffix + ".crt.tmp")
    try:
        with key_tmp.open("xb") as f:
            f.write(key_bytes)
        with cert_tmp.open("xb") as f:
            f.write(cert_bytes)
        os.replace(key_tmp, key_path)
        os.replace(cert_tmp, cert_path)
    finally:
        key_tmp.unlink(missing_ok=True)
        cert_tmp.unlink(missing_ok=True)
    return cert_path, key_path
