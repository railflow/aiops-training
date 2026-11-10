# DO NOT DO THIS. Demonstrates why secrets must never be baked into an image.
# Build from a folder that contains a .env file you create in the lesson (fake values).
FROM alpine:3.20
ENV DB_PASSWORD=hunter2-demo-only
ARG API_TOKEN=demo-token-not-real
COPY .env /app/.env
CMD ["sh", "-c", "echo the app started; sleep 3600"]
