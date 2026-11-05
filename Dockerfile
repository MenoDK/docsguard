# syntax=docker/dockerfile:1.7
# Stage 1: build a wheel. Stage 2: install only that wheel into a slim, non-root runtime. Stage 3: the lab, on top of it.
FROM python:3.12-slim AS build
WORKDIR /src
RUN pip install --no-cache-dir build==1.2.2.post1
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m build --wheel --outdir /dist

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
# No git in the image: it would triple the size and only `check --staged` uses it (that rule then reports an explicit skip).
RUN useradd --system --uid 10001 --create-home guard
COPY --from=build /dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl
USER guard
WORKDIR /workspace
HEALTHCHECK --interval=30s --timeout=5s CMD ["docsguard", "--version"]
ENTRYPOINT ["docsguard"]
CMD ["check", "--root", "/workspace"]

# The lab: the landing page and a small standard-library server around the real guards. Not part of the installed package,
# and not the default target of a plain build: `docker compose` names the target it wants.
FROM runtime AS playground
ENV DG_BIND=0.0.0.0 DG_PORT=8200 PYTHONPATH=/app
WORKDIR /app
COPY --chown=guard:guard playground ./playground
COPY --chown=guard:guard site ./site
EXPOSE 8200
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8200/api/health', timeout=3)"]
ENTRYPOINT ["python", "-m", "playground"]
CMD []
