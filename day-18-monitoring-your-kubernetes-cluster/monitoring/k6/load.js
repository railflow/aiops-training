// LOAD: ramp up to a normal-busy level, hold, ramp down. "Does it hold up at the traffic we expect?"
// Laptop-safe default is 20 virtual users; raise it deliberately: k6 run -e MAX_VUS=50 load.js
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://hello-py.localhost:8080';
const MAX_VUS = parseInt(__ENV.MAX_VUS || '20', 10);
const TARGET_PATH = __ENV.TARGET_PATH || '/hello';
const PARAMS = { headers: __ENV.HOST_HEADER ? { Host: __ENV.HOST_HEADER } : {} };

export const options = {
  stages: [
    { duration: '1m', target: MAX_VUS },      // ramp up
    { duration: '3m', target: MAX_VUS },      // hold
    { duration: '30s', target: 0 },           // ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}${TARGET_PATH}`, PARAMS);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(Math.random() * 0.4 + 0.1);
}
