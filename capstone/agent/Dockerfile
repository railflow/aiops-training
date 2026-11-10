# The agent image: the measure image (build.sh, trivy, gitleaks, language toolchains) plus the Claude Code CLI and our harness.
# Build from the repository root (aiops-training) after the measure image:  docker build -f capstone/agent/Dockerfile -t capstone-agent:1 .
# NOT built on the author's machine (no Docker). Claude Code is installed from npm; the version below is the one `claude --help` was read from.
ARG MEASURE_IMAGE=measure:1
FROM ${MEASURE_IMAGE}
ARG CLAUDE_CODE_VERSION=2.1.278
USER root
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" && claude --version
COPY capstone/agent/run-agent.sh capstone/agent/evaluate.sh capstone/agent/integrity_check.py /opt/agent/
COPY capstone/agent/prompts /opt/agent/prompts
COPY capstone/agent/bin/file_issue.py /usr/local/bin/file_issue.py
RUN chmod +x /opt/agent/*.sh /opt/agent/integrity_check.py /usr/local/bin/file_issue.py \
 && mkdir -p /work /tmp/home && chown -R 10001:10001 /work
USER 10001
WORKDIR /work
