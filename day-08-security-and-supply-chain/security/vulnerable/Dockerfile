# Deliberately OLD base image and dependencies so the scanner has something to find.
# Never deploy this. If the tag has been removed from Docker Hub, pick any old python:3.x-slim tag.
FROM python:3.8-slim-buster
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]
