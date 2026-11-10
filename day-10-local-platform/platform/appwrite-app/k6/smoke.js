// k6 smoke test through Appwrite's execution API. Needs the k6 binary (or the grafana/k6 container) and:
//   k6 run -e BASE=http://appwrite.localhost:8080/v1 -e PROJECT=<project id> k6/smoke.js
// Nothing here is a secret: execution is allowed for "any", so no API key is sent.
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 2,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1500'],
  },
};

const headers = { 'Content-Type': 'application/json', 'X-Appwrite-Project': __ENV.PROJECT };

function execute(payload) {
  return http.post(`${__ENV.BASE}/functions/guestbook/executions`, JSON.stringify({ async: false, ...payload }), { headers });
}

export default function () {
  const write = execute({
    path: '/entries',
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ name: `k6-${__VU}`, message: `iteration ${__ITER}` }),
  });
  check(write, {
    'execution created': (r) => r.status === 201,
    'function answered 201': (r) => r.json('responseStatusCode') === 201,
  });
  const read = execute({ path: '/entries', method: 'GET' });
  check(read, { 'list answered 200': (r) => r.json('responseStatusCode') === 200 });
  sleep(1);
}
