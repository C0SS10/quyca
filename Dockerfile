FROM python:3.13-slim AS base

ENV \
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONPATH=/app \
	VIRTUAL_ENV=/venv \
	PATH="/venv/bin:$PATH"

WORKDIR /app

# Dependencies only: this layer is rebuilt only when pyproject.toml or poetry.lock change.
FROM base AS deps

ENV \
	PIP_NO_CACHE_DIR=1 \
	PIP_DISABLE_PIP_VERSION_CHECK=1 \
	POETRY_VERSION=2.5.1 \
	POETRY_NO_INTERACTION=1 \
	POETRY_VIRTUALENVS_CREATE=false

RUN pip install "poetry==$POETRY_VERSION" && python -m venv $VIRTUAL_ENV

COPY pyproject.toml poetry.lock ./

FROM deps AS deps-dev
RUN poetry install --no-root

FROM deps AS deps-prod
RUN poetry install --no-root --without dev

# Runtime images: no poetry, code is mounted over /app by docker-compose, config is read from .env.<ENVIRONMENT>.
FROM base AS development
ENV ENVIRONMENT=dev
COPY --from=deps-dev /venv /venv
COPY . .
CMD ["gunicorn"]

FROM base AS production
ENV ENVIRONMENT=prod
COPY --from=deps-prod /venv /venv
COPY . .
CMD ["gunicorn"]
