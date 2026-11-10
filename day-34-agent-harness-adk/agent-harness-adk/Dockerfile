# Build from the repository root (aiops-training):  docker build -f day-34-agent-harness-adk/agent-harness-adk/Dockerfile -t agent-harness:dev .
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY day-34-agent-harness-adk/agent-harness-adk/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY capstone/gen /capstone/gen
COPY day-34-agent-harness-adk/agent-harness-adk/ /app/
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 GEN_SCRIPT=/capstone/gen/generate.py
USER 10001
CMD ["python", "-m", "hand_rolled.agent_loop"]
