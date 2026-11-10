FROM python:3.12-slim

# Flush print() output immediately so `docker logs` / `kubectl logs` show it.
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY hello.py .

CMD ["python", "hello.py"]
