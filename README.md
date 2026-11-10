# aiops-training

The files behind the **AI Ops Academy** course: scripts, Dockerfiles, Kubernetes manifests, charts, sample programs, configuration and sample data. One folder per lesson day, plus shared tools and the capstone.

The lesson text is **not** in this repo. It lives on the course site, which tells you when to open a folder here. Every value in the files (names, addresses, accounts, data) is fictional, and no file contains a real secret.

## Quick start

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global core.autocrlf input
cd ~
git clone https://github.com/railflow/aiops-training
cd aiops-training
./tools/kind start
```

Run commands from the repo root (`~/aiops-training`) unless a lesson says otherwise. Do your own work in a separate folder and repository (`~/heyjob-labs/dayNN/`), not in this clone.

## How this repo pairs with the course site

| On the course site | In this repo |
|---|---|
| The lesson: goals, explanations, step-by-step labs | The files the lab uses, in the day's folder |
| "Files for this lesson" note at the top of each lesson | `day-NN-<slug>/` and its `README.md` |
| Homework section | `day-NN-<slug>/homework.md` (assignment text only, no answers) |
| Short explanations of every file | The repo's docs, `docs/` (see below) |

## Folder map

| Folder | Contents |
|---|---|
| `day-NN-<slug>/` | One folder per lesson day: the scripts, Dockerfiles, manifests, charts, source, configs and sample data of that day, a `README.md` (what is inside) and `homework.md` |
| `capstone/` | The capstone reference kit: generator, measurement scripts, workflows, manifests, tests |
| `tools/` | Shared helpers: `kind` (cluster wrapper), `build.sh`, `deploy.sh`, `check-docs-touched.sh`, `coverage_percent.py`, `ports.sh`, `versions.env` |
| `docs/` | The repo's own docs (Astro Starlight): one page per day, setup, shared tools |
| `build.sh` | Builds and serves the docs |

Days without sample files of their own (1, 24, 25, 26, 30, 31, 32) still have a folder with a `README.md` and `homework.md`; their lessons use files from the folders named on the day's docs page. Paths such as `day-04-data-services-and-appwrite/java-app` are what the lessons type.

| Day | Folder | Files |
|---|---|---|
| Capstone | [`capstone/`](capstone/) | 74 |
| Day 1 | [`day-01-getting-started/`](day-01-getting-started/) | 0 |
| Day 2 | [`day-02-docker-basics/`](day-02-docker-basics/) | 18 |
| Day 3 | [`day-03-kind-kubernetes/`](day-03-kind-kubernetes/) | 9 |
| Day 4 | [`day-04-data-services-and-appwrite/`](day-04-data-services-and-appwrite/) | 12 |
| Day 5 | [`day-05-kubernetes-jobs/`](day-05-kubernetes-jobs/) | 5 |
| Day 6 | [`day-06-networking-and-network-policy/`](day-06-networking-and-network-policy/) | 6 |
| Day 7 | [`day-07-traefik-ingress/`](day-07-traefik-ingress/) | 13 |
| Day 8 | [`day-08-security-and-supply-chain/`](day-08-security-and-supply-chain/) | 6 |
| Day 9 | [`day-09-build-tools-and-tests/`](day-09-build-tools-and-tests/) | 2 |
| Day 10 | [`day-10-local-platform/`](day-10-local-platform/) | 68 |
| Day 11 | [`day-11-first-ci-and-kubectl/`](day-11-first-ci-and-kubectl/) | 2 |
| Day 12 | [`day-12-understanding-dependencies/`](day-12-understanding-dependencies/) | 24 |
| Day 13 | [`day-13-ci-at-scale-build-sh/`](day-13-ci-at-scale-build-sh/) | 3 |
| Day 14 | [`day-14-secrets-detection/`](day-14-secrets-detection/) | 5 |
| Day 15 | [`day-15-guard-rails-and-opa/`](day-15-guard-rails-and-opa/) | 8 |
| Day 16 | [`day-16-secrets-management-openbao/`](day-16-secrets-management-openbao/) | 6 |
| Day 17 | [`day-17-observability/`](day-17-observability/) | 17 |
| Day 18 | [`day-18-monitoring-your-kubernetes-cluster/`](day-18-monitoring-your-kubernetes-cluster/) | 24 |
| Day 19 | [`day-19-observability-dashboards/`](day-19-observability-dashboards/) | 17 |
| Day 20 | [`day-20-alerting-with-keep/`](day-20-alerting-with-keep/) | 35 |
| Day 21 | [`day-21-is-my-app-up-gatus/`](day-21-is-my-app-up-gatus/) | 4 |
| Day 22 | [`day-22-progressive-delivery-flux-flagger/`](day-22-progressive-delivery-flux-flagger/) | 12 |
| Day 23 | [`day-23-server-and-application-patching/`](day-23-server-and-application-patching/) | 35 |
| Day 24 | [`day-24-container-patching/`](day-24-container-patching/) | 0 |
| Day 25 | [`day-25-internal-platform/`](day-25-internal-platform/) | 0 |
| Day 26 | [`day-26-appwrite-hands-on/`](day-26-appwrite-hands-on/) | 0 |
| Day 27 | [`day-27-durable-workflows-temporal/`](day-27-durable-workflows-temporal/) | 30 |
| Day 28 | [`day-28-write-good-docs/`](day-28-write-good-docs/) | 43 |
| Day 29 | [`day-29-ai-tools-foundations/`](day-29-ai-tools-foundations/) | 47 |
| Day 30 | [`day-30-ai-agents-and-sandboxes/`](day-30-ai-agents-and-sandboxes/) | 0 |
| Day 31 | [`day-31-ai-quality-specs-evals-decisions/`](day-31-ai-quality-specs-evals-decisions/) | 0 |
| Day 32 | [`day-32-incident-to-reviewed-pr/`](day-32-incident-to-reviewed-pr/) | 0 |
| Day 33 | [`day-33-message-queues-in-devex/`](day-33-message-queues-in-devex/) | 41 |
| Day 34 | [`day-34-agent-harness-adk/`](day-34-agent-harness-adk/) | 38 |
| Day 35 | [`day-35-durable-agents-eve/`](day-35-durable-agents-eve/) | 38 |
| Day 36 | [`day-36-cloud-agent-sandboxes/`](day-36-cloud-agent-sandboxes/) | 46 |

## Homework

Each day's homework is in `homework.md` inside the day's folder, for example `day-05-kubernetes-jobs/homework.md`, and again at the bottom of the day's page in the docs. Only the assignment text is here: no answers, hints or grading rubrics.

## Docs: build and serve locally

The docs explain every file: what it is for, how to run it, what you should see, and how it relates to other days and the shared tools. Each day has a page, and the homework is on it.

### Prerequisites

Node.js **22.23.4 or newer** (and npm, which comes with it). Docker, kind and kubectl are not needed for the docs.

```bash
node --version
```

```text
v24.22.2
```

Any version from `v22.23.4` up is fine. If `node` is missing or too old, install it from <https://nodejs.org/> (macOS: `brew install node`; any system: `nvm install 22`) and open a new terminal.

### Build and serve: `./build.sh`

```bash
./build.sh
```

```text
node v24.22.2, npm 11.19.1
Installing docs dependencies (npm ci)

added 295 packages in 52s
Building the docs (full output: docs/.build.log)
Built 42 pages into docs/dist
Docs: http://localhost:4321/  (Ctrl+C to stop)
 astro  v7.3.6 ready in 20 ms
┃ Local    http://127.0.0.1:4321/
```

Open <http://localhost:4321/>. The first run installs dependencies (about a minute); later runs print `Dependencies are up to date (docs/node_modules)` and take a few seconds. Press `Ctrl+C` to stop.

### Live reload: `./build.sh --dev`

```bash
./build.sh --dev
```

```text
node v24.22.2, npm 11.19.1
Dependencies are up to date (docs/node_modules)
Dev server: http://localhost:4321/  (Ctrl+C to stop; search needs a build, use ./build.sh)
...
 astro  v7.3.6 ready in 906 ms
┃ Local    http://127.0.0.1:4321/
```

Edit any file under `docs/src/content/docs/` and the browser page updates. Search is not available in the dev server. The very first dev start can restart once; reload the page if it shows an error.

### Static output only (CI): `./build.sh --build-only`

```bash
./build.sh --build-only
```

```text
node v24.22.2, npm 11.19.1
Dependencies are up to date (docs/node_modules)
Building the docs (full output: docs/.build.log)
Built 42 pages into docs/dist
Static output: docs/dist (plain HTML, CSS and JS; any static web server can serve it)
```

The exit code is `0` on success. The build also checks every internal link and fails on a broken one (the details are in `docs/.build.log`).

### Change the port

```bash
./build.sh --port 4400      # same as: PORT=4400 ./build.sh
```

```text
Docs: http://localhost:4400/  (Ctrl+C to stop)
```

`--dev` takes the same options: `./build.sh --dev --port 4400`. If the default port 4321 is busy, `build.sh` uses the next free one and says so (`Port 4321 is busy, using 4322 instead`). A port you ask for explicitly that is busy is an error.

### Serve the built output with a plain static server

After `./build.sh --build-only`, any static server works, for example Python's:

```bash
python3 -m http.server 8000 --directory docs/dist
```

```text
Serving HTTP on :: port 8000 (http://[::]:8000/) ...
```

Open <http://localhost:8000/>. Search works here too, because the index is part of the static files.

### Open a specific day

Each day's page is at `/days/<folder name>/`:

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:4321/days/day-05-kubernetes-jobs/
```

```text
200
```

Open <http://localhost:4321/days/day-05-kubernetes-jobs/> in a browser (macOS: `open <url>`, Linux: `xdg-open <url>`). Other useful pages: `/getting-started/`, `/tools/`, `/homework/`.

### Search

Search works in `./build.sh` and in any static server, not in `--dev`. Click the **Search** box at the top (or press `Ctrl+K`, `Cmd+K` on a Mac) and type, for example, `job-db-seed`. The results list the pages and headings that mention it, such as "Day 5: Kubernetes Jobs". The search index is the static file `/pagefind/pagefind-entry.json`.

### Troubleshooting

| What you see | What to do |
|---|---|
| `build.sh: node was not found. Install Node.js 22.23.4 or newer ...` | Install Node.js (see Prerequisites), open a new terminal, run `./build.sh` again |
| `build.sh: Node.js 22.23.4 or newer is required, found v22.13.1.` | Upgrade Node.js (`nvm install 22` or install from nodejs.org), run again |
| `build.sh: port 4400 is already in use. Pick another one: ./build.sh --port 4401 ...` | Use another port, or stop the program that holds it (`lsof -i :4400` shows which one) |
| Odd errors after switching Node versions, a `node_modules` that is out of date, or an interrupted install | `./build.sh --reinstall` deletes `docs/node_modules` and installs again. When `package-lock.json` changes, `build.sh` reinstalls by itself |
| `npm ci` fails with a network error | Check your connection or proxy, then run `./build.sh --reinstall` |
| The build fails | `build.sh` prints the end of `docs/.build.log`; the first error line says which page or link is wrong |
| Windows | Use WSL2 (Ubuntu): install Node.js inside WSL (not the Windows one), clone into the Linux filesystem (`~/aiops-training`), run `./build.sh` there, and open <http://localhost:4321/> in the Windows browser |

## Shared tools

`tools/kind` creates and manages the course cluster (`./tools/kind start | stop | destroy | list`), `tools/build.sh` is the central build script, `tools/deploy.sh` asks the policy engine before deploying, and `tools/versions.env` pins image and tool versions. The docs page `/tools/` explains each one.

## Windows notes

All scripts are bash. Use Git Bash or WSL2. Set `git config --global core.autocrlf input` before cloning; `.gitattributes` keeps scripts on LF line endings. If a script says `Permission denied`: `chmod +x tools/kind build.sh`, or run it with `bash`.
