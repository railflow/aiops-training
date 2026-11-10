# Digest pinning and a bot to keep it fresh: see Day 24. Read the digest yourself with `docker buildx imagetools inspect`.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
ENV APP_VERSION=$APP_VERSION GIT_SHA=$GIT_SHA
USER 10001:10001
EXPOSE 8080
CMD ["python", "app.py"]
