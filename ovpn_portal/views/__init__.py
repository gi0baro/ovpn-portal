from .. import app, sessions

views = app.module(__name__, "views")
views.pipeline = [sessions]


@app.route(methods="get", output="bytes")
async def _health():
    return b""


from . import main
