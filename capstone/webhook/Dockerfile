# docker build -f capstone/webhook/Dockerfile -t capstone-webhook:1 .     (from the repository root; load into kind with: kind load docker-image capstone-webhook:1 --name ai-ops-training)
FROM python:3.12-slim
WORKDIR /app
COPY capstone/webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY capstone/webhook/app.py .
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
