# webhook/: Forgejo to Temporal

`app.py` verifies the HMAC signature, routes the event (`route()` is a pure function), and starts or signals a workflow. Run locally: `WEBHOOK_SECRET=x uvicorn app:app_factory --factory`. Deploy: `k8s.yaml`. Test delivery: Forgejo repo Settings, Webhooks, Test Delivery, then Recent Deliveries.

Replay by hand: `body='{"repository":{"full_name":"capstone/a","default_branch":"main"},"ref":"refs/heads/main","after":"'$(printf 'a%.0s' {1..40})'"}'; sig=$(printf '%s' "$body" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $NF}'); curl -H "X-Forgejo-Event: push" -H "X-Forgejo-Signature: $sig" -d "$body" http://capstone-webhook.localhost:8080/forgejo`
