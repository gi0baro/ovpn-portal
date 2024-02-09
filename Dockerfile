FROM ghcr.io/gi0baro/poetry-bin:3.9-1.3 as deps

COPY pyproject.toml .
COPY poetry.lock .
RUN poetry install --no-dev

FROM alpine:3 as fetcher

RUN apk add --no-cache curl
RUN curl -sSL -o cfssl https://github.com/cloudflare/cfssl/releases/download/v1.6.1/cfssl_1.6.1_linux_amd64 && \
    chmod +x cfssl

FROM docker.io/library/node:16 as css

COPY fe/css wrk/fe/css
COPY ovpn_portal/templates wrk/ovpn_portal/templates
WORKDIR /wrk/fe/css

ENV NODE_ENV production

RUN npm ci --also=dev && npx tailwindcss -i src/tailwind.css -c tailwind.config.js -o dist/main.css --minify

FROM docker.io/library/python:3.9-slim

COPY --from=deps /.venv /.venv
COPY --from=fetcher /cfssl /.venv/bin/cfssl
ENV PATH /.venv/bin:$PATH
ENV FORWARDED_ALLOW_IPS *

WORKDIR /app
COPY ovpn_portal app
COPY --from=css /wrk/fe/css/dist/main.css app/static/bundled/main.css

EXPOSE 8000

ENTRYPOINT [ "gunicorn" ]
CMD [ "app:app", "-k", "emmett.asgi.workers.EmmettWorker", "-b", "0.0.0.0:8000", "-w", "1", "--access-logfile", "-" ]
