from typing import Any, Callable, Dict, List, Optional, Type
from urllib.parse import urlencode

from emmett import Pipe, request, session, redirect, abort, sdict, url
from httpx import AsyncClient
from jose import jwt


class IdentityProvider:
    url_authorize: str
    url_exchange: str

    def __init__(self, client_id: str, client_secret: str, **kwargs: Any):
        self.client_id = client_id
        self.client_secret = client_secret

    def authorize_params(self, redirect_url: str) -> Dict[str, str]:
        raise NotImplementedError

    def authorize(self, redirect_url: str):
        redirect(
            f"{self.url_authorize}?" +
            urlencode(self.authorize_params(redirect_url))
        )

    async def exchange(self, client: AsyncClient) -> Optional[str]:
        raise NotImplementedError

    async def fetch(self, client: AsyncClient, token: str) -> Any:
        raise NotImplementedError


class Providers:
    registry: Dict[str, Type[IdentityProvider]] = {}

    @classmethod
    def register(
        cls,
        key: str
    ) -> Callable[[Type[IdentityProvider]], Type[IdentityProvider]]:
        def deco(obj: Type[IdentityProvider]) -> Type[IdentityProvider]:
            cls.registry[key] = obj
            return obj
        return deco

    def __init__(self, config):
        self.idps: Dict[str, IdentityProvider] = {}
        for key in set(config.keys()) & set(self.registry.keys()):
            self.idps[key] = self.registry[key](**config[key])

    def get(self, key: str) -> Optional[IdentityProvider]:
        return self.idps.get(key)

    def available(self) -> List[str]:
        return list(self.idps.keys())


class ExchangePipe(Pipe):
    def __init__(self, provider: IdentityProvider):
        self.provider = provider

    async def pipe(self, next_pipe, **kwargs):
        async with AsyncClient() as client:
            token = await self.provider.exchange(client)
            if not token:
                abort(401)
            data = await self.provider.fetch(client, token)
            if not data.get("email"):
                abort(401)
            if not data.get("groups"):
                abort(401)
            kwargs.update(**data)
        return await next_pipe(**kwargs)


@Providers.register("dex")
class DexProvider(IdentityProvider):
    def __init__(self, client_id: str, client_secret: str, **kwargs: Any):
        super().__init__(client_id, client_secret, **kwargs)
        self.config = sdict(
            scopes=["openid", "email", "groups"]
        )
        self.config.update(**kwargs)
        assert self.config.endpoint
        self.url_authorize = f"{self.config.endpoint}/auth"
        self.url_exchange = f"{self.config.endpoint}/token"

    def authorize_params(self, redirect_url: str) -> Dict[str, str]:
        return {
            "client_id": self.client_id,
            "redirect_uri": redirect_url,
            "response_type": "code",
            "scope": " ".join(self.config.scopes)
        }

    async def exchange(self, client: AsyncClient) -> Optional[str]:
        ctx = session.idp_data or {}
        try:
            res = await client.post(
                self.url_exchange,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "authorization_code",
                    "code": request.query_params.code,
                    "redirect_uri": ctx.get("redirect_uri")
                },
                headers={
                    "accept": "application/json"
                }
            )
            token = res.json()["access_token"]
        except Exception:
            token = None
        return token

    async def fetch(self, client: AsyncClient, token: str) -> Dict[str, Any]:
        try:
            data = jwt.decode(
                token,
                {},
                options={
                    "verify_signature": False,
                    "verify_at_hash": False
                },
                audience=self.client_id,
                issuer=self.config.endpoint
            )
            rv = {key: data[key] for key in ["email", "groups"]}
        except:
            rv = {}
        return rv
