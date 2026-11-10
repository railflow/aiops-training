# Temporal worker image. Pinned by tag AND digest; the digest was read on 2026-11-05 and WILL be stale: refresh it (Day 24).
FROM python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY models.py activities.py workflow.py worker.py starter.py ./
ARG GIT_SHA=unknown
ENV GIT_SHA=$GIT_SHA
USER 10001
EXPOSE 9000
CMD ["python", "worker.py"]
