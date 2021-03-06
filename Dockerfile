FROM python:3.8-alpine3.10

# enables proper stdout flushing
ENV PYTHONUNBUFFERED=yes

# pip optimizations
ENV PIP_NO_CACHE_DIR=yes
ENV PIP_DISABLE_PIP_VERSION_CHECK=yes

WORKDIR /code

COPY requirements/package.txt requirements.txt

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    make \
    musl-dev \
    && pip install -r requirements.txt \
    && apk del .build-deps

COPY . .

RUN addgroup -S modbay \
    && adduser -S modbay -G modbay \
    && chown -R modbay:modbay /code

USER modbay

ARG GIT_COMMIT=undefined
ENV GIT_COMMIT=${GIT_COMMIT}
LABEL GIT_COMMIT=${GIT_COMMIT}

ENTRYPOINT ["python", "-m", "job_runner"]
