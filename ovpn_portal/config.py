import json

from emmett import App, sdict

from .idp import Providers


def load_config(app: App):
    app.config_from_yaml("app.yml")
    app.config_from_yaml("vpn.yml", "vpn")

    idp = {}
    for key in set(
        (app.config.get("idp") or {}).keys()) & set(Providers.registry.keys()
    ):
        element = app.config.idp[key]
        if element and element.get("client_id") and element.get("client_secret"):
            idp[key] = element
    app.config.idp = idp

    app.config.certs = sdict(
        root=sdict(cert=app.config.pki.root_ca),
        intermediates=sdict()
    )
    for key, val in app.config.vpn.items():
        app.config.certs.intermediates[key] = sdict(
            cert=val.cert,
            key=val.key
        )
    _gen_cffsl_config(app)


def _gen_cffsl_config(app: App):
    data = {
        "signing": {
            "default": {"expiry": "24h"},
            "profiles": {
                "client": {
                    "expiry": app.config.pki.client.expiry,
                    "usages": [
                        "signing",
                        "digital signature",
                        "key encipherment",
                        "client auth"
                    ]
                }
            }
        }
    }
    with open(f"{app.root_path}/config/cfssl.json", "w") as f:
        f.write(json.dumps(data))
