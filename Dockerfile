# syntax=docker/dockerfile:1

# ---------- Stage 1: dependencies ----------
# Installs the Python packages in a separate stage. The final image only copies
# the result, so it does not contain pip's cache or build files.
FROM python:3.12-slim AS deps
WORKDIR /install
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --prefix=/install/packages -r requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

LABEL org.opencontainers.image.title="events-holidays" \
      org.opencontainers.image.description="Event registration CLI (UNIBZ Continuous Integration)" \
      org.opencontainers.image.authors="Pedro David Ramos Salamanca"

# Layers are ordered from the least to the most frequently changed,
# so a code change only rebuilds the last layers.

# Layer: non-root user (almost never changes)
RUN useradd --create-home appuser
WORKDIR /app

# Layer: installed dependencies (changes only when requirements.txt changes)
COPY --from=deps /install/packages /usr/local

# Layers: application code, from the most stable to the most frequently edited
COPY Models ./Models
COPY States ./States
COPY Storage ./Storage
COPY Adapter.py DataSource.py ./
COPY eventsHolidays.py ./

USER appuser
ENTRYPOINT ["python", "eventsHolidays.py"]
CMD ["--help"]
