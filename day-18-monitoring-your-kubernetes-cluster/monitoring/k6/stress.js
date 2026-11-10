// STRESS: keep increasing the load until something hurts. "Where is the limit, and what breaks first?"
// WARNING: this can slow your whole laptop. Start from smoke.js and load.js, close other apps, and
// watch memory in Docker Desktop. Stop any time with Ctrl+C.
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://hello-py.localhost:8080';
const TARGET_PATH = __ENV.TARGET_PATH || '/hello';
const PARAMS = { headers: __ENV.HOST_HEADER ? { Host: __ENV.HOST_HEADER } : {} };

export const options = {
  stages: [
    { duration: '1m', target: 10 },
    { duration: '1m', target: 25 },
    { duration: '1m', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '1m', target: 150 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_failed: [{ threshold: 'rate<0.20', abortOnFail: true, delayAbortEval: '30s' }],
    http_req_duration: ['p(95)<2000'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}${TARGET_PATH}`, PARAMS);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.1);
}
