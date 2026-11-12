FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app


COPY --from=ghcr.io/astral-sh/uv:0.5.14 /uv /usr/local/bin/uv

# Sprint 11: local speech/translation models are opt-in (heavy): --build-arg INSTALL_LOCAL_ML=true
ARG INSTALL_LOCAL_ML=false

COPY pyproject.toml uv.lock ./
RUN if [ "$INSTALL_LOCAL_ML" = "true" ]; then       uv sync --locked --no-dev --extra local-ml;     else       uv sync --locked --no-dev;     fi

COPY . .

RUN chmod +x /app/scripts/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
