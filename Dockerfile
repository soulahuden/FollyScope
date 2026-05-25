# syntax=docker/dockerfile:1.7
#
# Folliscope multi-stage Dockerfile.
#
# Build:  docker build -t folliscope .
# Run:    docker run --rm -p 8000:8000 folliscope
# Or:     docker compose up --build
#
# Honors $PORT so the same image deploys to Render / Railway / Fly /
# Cloud Run without changes.

############################################
# Stage 1: build wheels in an isolated env #
############################################
FROM python:3.12-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# Build deps for any pydantic / biopython C extensions that lack wheels
# on the target arch. Removed from the final image.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --prefix=/install --no-cache-dir -r requirements.txt


############################
# Stage 2: runtime image  #
############################
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    # Tell Bio.Entrez who's calling. Override in deploy env if you want
    # to use your own email for NCBI rate-limit accounting.
    FOLLISCOPE_ENTREZ_EMAIL="folliscope.education@example.com"

# curl is used by the Docker HEALTHCHECK below; ca-certificates is needed
# for the outbound HTTPS call to NCBI Entrez.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Run as an unprivileged user. UID 1000 matches the typical host user
# so volume mounts during dev don't end up root-owned.
RUN groupadd --system --gid 1000 app \
 && useradd  --system --uid 1000 --gid app --create-home --home-dir /home/app app

WORKDIR /app

# Copy installed Python packages from the build stage.
COPY --from=builder /install /usr/local

# Copy application source. .dockerignore excludes tests, docs, caches.
COPY --chown=app:app . .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:${PORT:-8000}/api/health || exit 1

# `sh -c` so $PORT expansion happens at container start (PaaS providers
# inject it dynamically). Single-process uvicorn keeps things simple;
# scale horizontally via the orchestrator, not workers in a single pod.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
