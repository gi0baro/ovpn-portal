from emmett import request, response, session, url

from .. import app, idp
from ..idp import ExchangePipe
from ..ovpn import build_vpn_config
from . import views
from ._pipes import VPNAuthPipe


@views.route("/")
async def index():
    return {}


@views.route()
async def exchange():
    return {"code": request.query_params.code}


exchange_pipeline = []

if dex_idp_provider := idp.get("dex"):
    @views.route()
    async def dex():
        scheme = request.headers.get("x-forwarded-proto") or request.scheme
        redirect_url = url(".exchange", scheme=scheme)
        session.idp_data = {"redirect_uri": redirect_url}
        dex_idp_provider.authorize(redirect_url)

    exchange_pipeline.append(ExchangePipe(dex_idp_provider))

exchange_pipeline.append(VPNAuthPipe(app.config.vpn, app.config.default_vpn))


@views.route(pipeline=exchange_pipeline, output="bytes")
async def _exchange(vpn_profile, vpn_cn):
    cn, vpn_config = await build_vpn_config(vpn_profile, vpn_cn)
    response.headers["content-disposition"] = f'attachment; filename="{cn}.ovpn"'
    return vpn_config
