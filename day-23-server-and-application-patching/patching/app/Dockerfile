# Pinned by tag AND digest. The digest was read from Docker Hub on 2026-11-05 and WILL be out of date:
# read the current one yourself (see Day 24) and let Renovate keep it fresh.
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
ENV APP_VERSION=$APP_VERSION GIT_SHA=$GIT_SHA
USER 10001
EXPOSE 8080
CMD ["python", "app.py"]
