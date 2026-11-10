---
title: aiops-training
description: "Scripts, Dockerfiles, manifests and sample code for the AI Ops Academy course, one folder per lesson day."
template: splash
hero:
  tagline: The files behind the AI Ops Academy lessons, explained file by file.
  actions:
    - text: Getting started
      link: /getting-started/
      icon: right-arrow
    - text: Shared tools
      link: /tools/
      variant: minimal
---

This repository holds everything the course lessons use **except the lesson text**: scripts, Dockerfiles, Kubernetes manifests, charts, sample programs, configuration and sample data. There is one folder per lesson day (`day-01-getting-started`, `day-02-docker-basics`, and so on, plus `capstone`). Shared helpers live in `tools/`.

The lessons themselves, with all the explanations, are on the course site. These docs answer a different question: *what is this file, how do I run it, what should I see, and how does it relate to the rest?* Each day has a page with a file-by-file guide and the day's homework.

- Folder names match the lesson names, so `day-05-kubernetes-jobs/` is the folder for Day 5.
- Paths in the lessons are relative to the repo root (`~/aiops-training`).
- Every data value, address and account in the files is fictional. No file contains a real secret; the lessons tell you to create secrets yourself, on your own machine.

## All days

| Day | Topic | Files |
|---|---|---|
| [Capstone](/days/capstone/) | Capstone: the AI agent army | 74 |
| [Day 1](/days/day-01-getting-started/) | Getting started | 0 |
| [Day 2](/days/day-02-docker-basics/) | Docker basics | 18 |
| [Day 3](/days/day-03-kind-kubernetes/) | kind Kubernetes | 9 |
| [Day 4](/days/day-04-data-services-and-appwrite/) | Data services and Appwrite | 12 |
| [Day 5](/days/day-05-kubernetes-jobs/) | Kubernetes Jobs | 5 |
| [Day 6](/days/day-06-networking-and-network-policy/) | Namespaces, Services, and NetworkPolicy | 6 |
| [Day 7](/days/day-07-traefik-ingress/) | Traefik, one front door for your apps | 13 |
| [Day 8](/days/day-08-security-and-supply-chain/) | Vulnerabilities and the software supply chain | 6 |
| [Day 9](/days/day-09-build-tools-and-tests/) | Build tools, tests, and coverage | 2 |
| [Day 10](/days/day-10-local-platform/) | A local enterprise-like platform (Forgejo and Nexus) | 63 |
| [Day 11](/days/day-11-first-ci-and-kubectl/) | Your first CI pipeline, and how kubectl really works | 2 |
| [Day 12](/days/day-12-understanding-dependencies/) | Understanding dependencies | 24 |
| [Day 13](/days/day-13-ci-at-scale-build-sh/) | CI at scale with a central build.sh | 3 |
| [Day 14](/days/day-14-secrets-detection/) | Secrets, part 1: never commit them, and catch them when you do | 5 |
| [Day 15](/days/day-15-guard-rails-and-opa/) | Guard rails and policy as code with OPA | 8 |
| [Day 16](/days/day-16-secrets-management-openbao/) | Secrets, part 2: where secrets live (OpenBao), how apps get them, and rotation | 6 |
| [Day 17](/days/day-17-observability/) | Observability: logs, metrics and traces with OpenTelemetry and ClickHouse | 17 |
| [Day 18](/days/day-18-monitoring-your-kubernetes-cluster/) | Monitoring your Kubernetes cluster: limits, layers and cluster metrics in ClickHouse | 24 |
| [Day 19](/days/day-19-observability-dashboards/) | Observability: dashboards as code with Grafana and ClickHouse | 17 |
| [Day 20](/days/day-20-alerting-with-keep/) | Alerting and incident management with Keep | 35 |
| [Day 21](/days/day-21-is-my-app-up-gatus/) | Is my app up and OK? Health endpoints, probes and Gatus | 4 |
| [Day 22](/days/day-22-progressive-delivery-flux-flagger/) | Release risk, GitOps with Flux, and progressive delivery with Flagger | 12 |
| [Day 23](/days/day-23-server-and-application-patching/) | Server and application patching | 35 |
| [Day 24](/days/day-24-container-patching/) | Container patching and hardening | 0 |
| [Day 25](/days/day-25-internal-platform/) | Building an internal platform for hosting apps and APIs | 0 |
| [Day 26](/days/day-26-appwrite-hands-on/) | Appwrite hands-on - functions, databases and a laptop-built app | 0 |
| [Day 27](/days/day-27-durable-workflows-temporal/) | Durable workflows with Temporal | 30 |
| [Day 28](/days/day-28-write-good-docs/) | Writing good docs (and keeping them true) | 33 |
| [Day 29](/days/day-29-ai-tools-foundations/) | AI tools for DevEx, foundations | 47 |
| [Day 30](/days/day-30-ai-agents-and-sandboxes/) | Agents and sandboxes | 0 |
| [Day 31](/days/day-31-ai-quality-specs-evals-decisions/) | Quality: specs, evals and decision models | 0 |
| [Day 32](/days/day-32-incident-to-reviewed-pr/) | From incident to reviewed PR | 0 |
| [Day 33](/days/day-33-message-queues-in-devex/) | Message queues, and why they matter in DevEx | 41 |
| [Day 34](/days/day-34-agent-harness-adk/) | Building an agent harness with Google ADK | 38 |
| [Day 35](/days/day-35-durable-agents-eve/) | Durable AI agents with Eve | 38 |
| [Day 36](/days/day-36-cloud-agent-sandboxes/) | Cloud agent sandboxes | 46 |
