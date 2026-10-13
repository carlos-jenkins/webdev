# Copyright (C) 2026 KuraLabs S.R.L <info@kuralabs.io>
# Copyright (C) 2015-2016 Carlos Jenkins <carlos@jenkins.co.cr>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
Optional self-signed TLS certificate generation for ``--https``.

If the user provides ``--cert``/``--key`` those are used directly. Otherwise a
throwaway self-signed certificate is generated into a temporary directory. We
avoid adding a hard cryptography dependency: generation uses the ``cryptography``
package when present, falling back to the system ``openssl`` binary. If neither
is available a clear error asks the user to pass ``--cert``/``--key``.
"""

from __future__ import annotations

import datetime
import subprocess
import tempfile
from pathlib import Path


class TLSUnavailableError(Exception):
    """Raised when a self-signed certificate cannot be generated."""


def _generate_with_cryptography(cert_path: Path, key_path: Path) -> bool:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ModuleNotFoundError:
        return False

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return True


def _generate_with_openssl(cert_path: Path, key_path: Path) -> bool:
    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-keyout",
                str(key_path),
                "-out",
                str(cert_path),
                "-days",
                "365",
                "-nodes",
                "-subj",
                "/CN=localhost",
            ],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return cert_path.is_file() and key_path.is_file()


def ensure_tls_files(cert: str | None, key: str | None) -> tuple[str, str]:
    """
    Return a ``(cert_path, key_path)`` pair for HTTPS.

    If both *cert* and *key* are provided they are returned as-is. Otherwise a
    self-signed certificate is generated into a temporary directory.
    """
    if cert and key:
        return cert, key

    tmp = Path(tempfile.mkdtemp(prefix="webdev-tls-"))
    cert_path = tmp / "cert.pem"
    key_path = tmp / "key.pem"

    if _generate_with_cryptography(cert_path, key_path):
        return str(cert_path), str(key_path)
    if _generate_with_openssl(cert_path, key_path):
        return str(cert_path), str(key_path)

    raise TLSUnavailableError(
        "Could not generate a self-signed certificate: install the "
        "'cryptography' package or the 'openssl' binary, or pass --cert/--key."
    )
