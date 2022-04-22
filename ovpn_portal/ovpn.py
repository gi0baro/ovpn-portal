from contextlib import asynccontextmanager
from typing import Tuple
from uuid import uuid4

from botocore.exceptions import ClientError

from . import app
from .pki import build_cert, build_revocation_list
from .s3 import delete_object, get_object, list_path_contents, put_object, s3bucket


class LockError(Exception):
    ...


class MissingSerialsError(Exception):
    ...


class StateAccessError(Exception):
    ...


class ConcurrentRevocationsError(Exception):
    ...


async def build_vpn_config(profile: str, cn: str) -> Tuple[str, str]:
    vpn_data = app.config.vpn[profile]
    cnu = f"{cn}-{uuid4().hex[:7]}"[:64]
    cert_data = build_cert(profile, cnu)
    vpn_config = app.templater.render(
        "openvpn.tpl",
        {
            "ca": cert_data["ca"],
            "cert": cert_data["cert"],
            "cipher": vpn_data.get("cipher", "AES-256-CBC"),
            "domain": vpn_data.get("domain"),
            "private_key": cert_data["key"],
            "port": vpn_data["port"],
            "remote": vpn_data["endpoint"],
            "extras": {**app.config.openvpn.config, **vpn_data.get("config", {})}
        }
    ).encode("utf8")
    await put_object(
        f"{app.config.object_storage.path_certs}/{cn}/{cert_data['serial']}",
        vpn_config
    )
    return cnu, vpn_config


@asynccontextmanager
async def crl_lock(profile):
    key = f"{app.config.object_storage.path_locks}/{profile}.lock"
    try:
        s3bucket.Object(key).load()
        raise LockError
    except ClientError as err:
        if err.response["Error"]["Code"] == "404":
            await put_object(key, b"")
        else:
            raise LockError
    yield
    await delete_object(key)


async def revoke_vpn_configs(profile: str, cn: str):
    serials = await list_path_contents(
        f"{app.config.object_storage.path_certs}/{cn}"
    )
    if not serials:
        raise MissingSerialsError
    try:
        async with crl_lock(profile):
            try:
                r = await get_object(
                    f"{app.config.object_storage.path_states}/{profile}"
                )
                all_serials = r.decode("utf8").splitlines()
            except ClientError as err:
                if err.response["Error"]["Code"] == "NoSuchKey":
                    all_serials = []
                else:
                    raise StateAccessError
            all_serials.extend(serials)
            all_serials = list(set(all_serials))
            crl = build_revocation_list(profile, all_serials)
            await put_object(
                f"{app.config.object_storage.path_states}/{profile}",
                "\n".join(all_serials).encode("utf8")
            )
            await put_object(f"{app.config.object_storage.path_crl}/{profile}", crl)
    except LockError:
        raise ConcurrentRevocationsError
