// LOOP: a steady, low request RATE that runs for a long time, so dashboards always have live data.
// Defaults are laptop-safe: 5 requests per second for 30 minutes, against the two-service shop app.
//   k6 run loop.js
//   k6 run -e RATE=10 -e DURATION=2h loop.js
// Mix: mostly /checkout (frontend -> backend), some /hello, a few requests that can fail or be slow.
// Faults are driven by the app (INJECT_* variables and /flaky, /slow), so a quiet app gives a quiet loop.
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://shop.localhost:8080';
const PARAMS = { headers: __ENV.HOST_HEADER ? { Host: __ENV.HOST_HEADER } : {} };
const FLAKY_RATE = __ENV.FLAKY_RATE || '0.05';

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: parseInt(__ENV.RATE || '5', 10),
      timeUnit: '1s',
      duration: __ENV.DURATION || '30m',
      preAllocatedVUs: 10,
      maxVUs: 50,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<1000'],
  },
};

export default function () {
  const dice = Math.random();
  let res;
  if (dice < 0.70) {
    res = http.get(`${BASE_URL}/checkout`, { ...PARAMS, tags: { name: 'checkout' } });
  } else if (dice < 0.90) {
    res = http.get(`${BASE_URL}/hello`, { ...PARAMS, tags: { name: 'hello' } });
  } else if (dice < 0.97) {
    res = http.get(`${BASE_URL}/flaky?rate=${FLAKY_RATE}`, { ...PARAMS, tags: { name: 'flaky' } });
  } else {
    res = http.get(`${BASE_URL}/slow?ms=400`, { ...PARAMS, tags: { name: 'slow' } });
  }
  check(res, { 'status is 2xx': (r) => r.status >= 200 && r.status < 300 });
}
