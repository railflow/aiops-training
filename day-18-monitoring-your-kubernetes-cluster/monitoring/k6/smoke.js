// SMOKE: one virtual user for 30 seconds. "Does it work at all?" Run this before anything bigger.
//   k6 run smoke.js
//   k6 run -e BASE_URL=http://shop.localhost:8080 smoke.js
// Through Docker Desktop (the container cannot see your laptop's *.localhost names, so use
// host.docker.internal and send the Host header Traefik routes on):
//   docker run --rm -i -v "${PWD}:/scripts" grafana/k6 run -e BASE_URL=http://host.docker.internal:8080 -e HOST_HEADER=hello-py.localhost /scripts/smoke.js
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://hello-py.localhost:8080';
const TARGET_PATH = __ENV.TARGET_PATH || '/hello';
const PARAMS = { headers: __ENV.HOST_HEADER ? { Host: __ENV.HOST_HEADER } : {} };

export const options = {
  vus: 1,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],   // under 1% errors
    http_req_duration: ['p(95)<500'], // 95% of requests faster than 500 ms
    checks: ['rate>0.99'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}${TARGET_PATH}`, PARAMS);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'has a message': (r) => r.body && r.body.includes('message'),
  });
  sleep(1);
}
