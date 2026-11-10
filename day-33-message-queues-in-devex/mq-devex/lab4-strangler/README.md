# Lab 4: the strangler facade

```
caller --ci.requested--> facade.py --reads KV flags/ci-runner--> ci.run.legacy --> adapters.py legacy --(wraps)--> legacy/run_ci_legacy.sh
                                                             \-> ci.run.new    --> adapters.py new
                         both adapters end with the SAME event: ci.completed {impl, shadow, passed, duration_ms}
                         compare.py (shadow mode) joins both answers per correlation id -> ci.compare.result {agree}
```

## Run

```bash
export PYTHONPATH=../lib NATS_URL=nats://127.0.0.1:4222 STATE_DIR=.state
python3 facade.py & python3 compare.py & python3 adapters.py legacy & python3 adapters.py new &

nats kv add flags 2>/dev/null; nats kv put flags ci-runner legacy
# publish a request (any publisher; here the nats CLI with a hand-written envelope is awkward, so use Python):
python3 -c "
import asyncio, devbus
async def go():
    nc, js = await devbus.connect(); await devbus.ensure_stream(js)
    ev = devbus.new_event('ci.requested', {'repo':'orders-api','sha':'s1','flags':{}}, 'demo'); await devbus.publish(js, 'ci.requested', ev); await nc.close()
asyncio.run(go())"
nats kv put flags ci-runner shadow         # now both run; compare.py reports agree true/false
NEW_BUG=1 python3 adapters.py new          # restart the new adapter with a bug: shadow mode catches it before any real traffic moves
nats kv put flags ci-runner canary:20      # then 20% of repos, stable per repo name
nats kv put flags ci-runner new            # finally everything; delete legacy/ and adapters.py legacy when you trust it
```

The caller never changes. That is the whole trick: the seam is the `ci.requested` / `ci.completed` contract.

`tests/test_strangler.py` runs the whole story (legacy, then new, then shadow with a planted bug) against a real server. The `shadow_agreement` and `impl_mix` queries in `../sql/queries.sql` are the "metrics of both side by side".

`legacy/run_ci_legacy.sh` is a fake legacy system (sleeps, prints `KEY=VALUE`, exits 0/1). It needs bash; on Windows use Git Bash or WSL.
