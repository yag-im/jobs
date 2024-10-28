# syntax=docker/dockerfile:1
FROM python:3.11-bookworm

ARG DEBIAN_FRONTEND=noninteractive

ARG APP_HOME_DIR=/opt/yag/jobs

RUN apt update \
    && apt install -y --no-install-recommends \
        gettext-base \
    && rm -rf /var/lib/apt/lists/*

COPY dist/*.whl /tmp/

RUN pip install --upgrade pip \
    && pip install /tmp/*.whl \
    && opentelemetry-bootstrap -a install \
    && rm -rf /tmp/*.whl

# bin folder contains:
#     cmd.sh: runs app
#     start.sh: handles graceful shutdown (wraps cmd.sh)
COPY runtime/bin ${APP_HOME_DIR}/bin

ENV APP_HOME_DIR=${APP_HOME_DIR}

CMD $APP_HOME_DIR/bin/start.sh
