# Lab 1: bus basics with the nats CLI

Goal: understand stream, subject, durable consumer, ack, redelivery, replay and dedupe by doing each once.

```bash
export NATS_URL=nats://127.0.0.1:4222      # or the port-forwarded Day 4 NATS
./lab1.sh                                  # about 2 seconds, safe to re-run
```

`lab1.sh` runs eight numbered steps and prints what the server says. `captured-output.txt` is the output of a real run on 2026-11-05 with `nats` 0.5.1
against `nats-server` 2.11.17 (ANSI colours stripped; timestamps and sizes will differ on your machine).

Things to notice in the output:

- Step 2: the three messages are stored although no consumer exists. The stream, not the consumer, owns the data.
- Step 3: `Unprocessed Messages: 2`, not 3, because the consumer filters on `eng.build.completed`.
- Step 5: `Outstanding Acks: 1` is a message handed out but not acknowledged. After `--wait 30s` the server will hand it out again with `tries: 2`.
- Step 6: a second consumer starting at the beginning replays the whole history. That is the audit log.
- Step 8: the same `Nats-Msg-Id` twice stores one message (4 total, not 5).

## Try it yourself (no script)

```bash
nats stream add ENG --subjects "eng.>,infra.>" --defaults
nats pub infra.request.k8s '{"name":"orders","env":"dev"}'
nats consumer add ENG infra-bot --pull --filter "infra.request.>" --ack explicit --deliver all --defaults
nats consumer next ENG infra-bot --count 1 --ack
nats stream view ENG
```

If a flag differs on your version, `nats stream add --help` and `nats consumer add --help` are the source of truth.
