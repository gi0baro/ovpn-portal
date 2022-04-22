import json
import os
import subprocess

from typing import Dict, List
from uuid import uuid4

from . import app


class CFSSLError(Exception):
    ...


def _build_cert_csr(cn: str) -> bytes:
    return json.dumps({
        "CN": cn,
        "key": {
            "algo": app.config.pki.client.key.algo,
            "size": app.config.pki.client.key.size
        },
        "names": [app.config.pki.client.names]
    }).encode("utf8")


def _build_crl_data(serials: List[str]) -> bytes:
    return b"\n".join([
        el.encode("utf8") for el in serials
    ])


def build_cert(profile: str, cn: str) -> Dict[str, str]:
    cfssl_config_path = os.path.join(
        app.root_path, 'config', 'cfssl_config.json'
    )
    ca_data = app.config.certs.intermediates[profile]
    try:
        proc = subprocess.run(
            " ".join([
                "cfssl gencert -loglevel 5",
                "-ca env:VPN_CA -ca-key env:VPN_CAKEY",
                f"-config {cfssl_config_path} -profile client",
                "-"
            ]),
            shell=True,
            check=True,
            capture_output=True,
            input=_build_cert_csr(cn),
            env={
                "PATH": os.environ.get("PATH"),
                "VPN_CA": ca_data.cert,
                "VPN_CAKEY": ca_data.key
            }
        )
        cert_data = json.loads(proc.stdout)
        proc = subprocess.run(
            "cfssl certinfo -loglevel 5 -cert -",
            shell=True,
            check=True,
            capture_output=True,
            input=cert_data["cert"].encode("utf8"),
            env={
                "PATH": os.environ.get("PATH")
            }
        )
        cert_info = json.loads(proc.stdout)
    except subprocess.CalledProcessError as e:
        raise CFSSLError
    return {
        "ca": "\n".join([app.config.certs.root.cert, ca_data.cert]),
        "cert": cert_data["cert"][:-1],
        "key": cert_data["key"][:-1],
        "serial": cert_info["serial_number"],
        "subject_key": cert_info["subject_key_id"]
    }


def build_revocation_list(profile: str, cert_serials: List[str]) -> str:
    ca_data = app.config.certs.intermediates[profile]
    req = uuid4().hex
    crt_path = os.path.join("/tmp", f"{req}.crt")
    key_path = os.path.join("/tmp", f"{req}.key")
    with open(crt_path, "w") as f:
        f.write(ca_data.cert)
    with open(key_path, "w") as f:
        f.write(ca_data.key)
    try:
        proc = subprocess.run(
            " ".join([
                "cfssl gencrl -loglevel 5",
                "-",
                crt_path,
                key_path,
                app.config.pki.crl.expiry
            ]),
            shell=True,
            check=True,
            capture_output=True,
            input=_build_crl_data(cert_serials),
            env={
                "PATH": os.environ.get("PATH")
            }
        )
        crl = proc.stdout.decode("utf8")[:-1]
    except subprocess.CalledProcessError as e:
        raise CFSSLError
    try:
        os.unlink(crt_path)
        os.unlink(key_path)
    except Exception:
        pass
    lines = [crl[idx:idx + 64] for idx in range(0, len(crl), 64)]
    lines.insert(0, "-----BEGIN X509 CRL-----")
    lines.append("-----END X509 CRL-----")
    return "\n".join(lines)
