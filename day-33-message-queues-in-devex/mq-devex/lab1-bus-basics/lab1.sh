#!/usr/bin/env bash
# Lab 1: bus basics with the nats CLI. Needs: `nats` (natscli) and a NATS server with JetStream, reachable at $NATS_URL.
#   NATS_URL=nats://127.0.0.1:4222 ./lab1.sh        (local nats-server, or `kubectl port-forward -n data svc/nats 4222:4222`)
# Verified with natscli 0.5.1 against nats-server 2.11.17 (the course pins nats:2.11-alpine). Safe to re-run: it deletes the ENG stream first.
set -euo pipefail
: "${NATS_URL:=nats://127.0.0.1:4222}"
export NATS_URL
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "0. clean slate"
nats stream rm ENG -f >/dev/null 2>&1 || true

step "1. create the stream ENG: it captures everything published to eng.> and infra.>"
nats stream add ENG --subjects "eng.>,infra.>" --storage file --retention limits --max-age 7d --defaults >/dev/null
nats stream ls

step "2. publish three messages (the stream stores them even though nobody is listening yet)"
nats pub eng.build.completed '{"repo":"orders-api","sha":"4f2a9c1"}' >/dev/null
nats pub eng.build.completed '{"repo":"billing-api","sha":"9b1d7e0"}' >/dev/null
nats pub infra.request.k8s   '{"name":"orders","env":"dev"}' >/dev/null
nats stream info ENG | sed -n '/^State:/,$p'

step "3. a durable PULL consumer for build events only. 'durable' = the server remembers where it is up to"
nats consumer add ENG build-worker --pull --filter "eng.build.completed" --ack explicit --deliver all --replay instant --max-deliver 4 --wait 30s --defaults >/dev/null
nats consumer info ENG build-worker | sed -n '/^State:/,$p'

step "4. take one message and ack it"
nats consumer next ENG build-worker --count 1 --ack

step "5. take the next one but do NOT ack it (--no-ack): it stays pending, and the server will redeliver after the wait time"
nats consumer next ENG build-worker --count 1 --no-ack
nats consumer info ENG build-worker | sed -n '/^State:/,$p'

step "6. replay: a brand-new consumer starting from the beginning sees ALL the history. That is your audit log."
nats consumer add ENG auditor --pull --ack none --deliver all --replay instant --defaults >/dev/null
nats consumer next ENG auditor --count 3 --no-ack

step "7. look at the stream and consumers"
nats stream info ENG | sed -n '/^State:/,$p'
nats consumer ls ENG

step "8. duplicate protection: the same Nats-Msg-Id twice inside the 2 minute window is stored once"
nats pub eng.test.once 'hello' -H Nats-Msg-Id:demo-1 >/dev/null
nats pub eng.test.once 'hello' -H Nats-Msg-Id:demo-1 >/dev/null
nats stream info ENG | grep -E "Messages:"
