from emmett import App
from emmett.sessions import SessionManager
from emmett.cache import Cache, RamCache

from .config import load_config
from .idp import Providers


app = App(__name__)
load_config(app)

cache = Cache(ram=RamCache())
idp = Providers(app.config.idp)
sessions = SessionManager.cookies(app.config.session_key, encryption_mode="modern")

from . import views
