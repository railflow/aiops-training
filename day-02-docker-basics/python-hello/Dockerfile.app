FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY hello.py hello_db.py appwrite_hello.py greeter.py api.py ./

# Default: the REST API. One-shot tools override the command (e.g. python hello_db.py).
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--access-logfile", "-", "api:app"]
