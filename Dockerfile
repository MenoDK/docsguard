# syntax=docker/dockerfile:1.7
# Stage 1: build a wheel. Stage 2: install only that wheel into a slim, non-root runtime.
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
