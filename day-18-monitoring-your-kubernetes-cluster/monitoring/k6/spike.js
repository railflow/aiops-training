// SPIKE: a sudden jump in traffic, then back to normal. "Do we survive a burst, and how fast do we recover?"
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://hello-py.localhost:8080';
const PEAK = parseInt(__ENV.PEAK_VUS || '60', 10);
const TARGET_PATH = __ENV.TARGET_PATH || '/hello';
const PARAMS = { headers: __ENV.HOST_HEADER ? { Host: __ENV.HOST_HEADER } : {} };

export const options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '10s', target: PEAK },   // the spike
    { duration: '1m', target: PEAK },
    { duration: '10s', target: 5 },      // back to normal
    { duration: '1m', target: 5 },       // watch the recovery
    { duration: '10s', target: 0 },
  ],
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<1000'],
  },
};

export default function () {
  const res = http.get(`${BASE_URL}${TARGET_PATH}`, PARAMS);
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(0.2);
}
