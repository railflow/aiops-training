import test from 'node:test';
import assert from 'node:assert/strict';
import handler from './src/main.js';

// A fake of the context the runtime passes in: just enough for the handler.
const ctx = (req) => ({
  req: { path: '/', query: {}, ...req },
  res: {
    text: (body) => ({ kind: 'text', body }),
    json: (body) => ({ kind: 'json', body }),
  },
  log: () => {},
});

test('greets the world by default', async () => {
  const out = await handler(ctx({}));
  assert.deepEqual(out.body, { message: 'Hello, world!', runtime: 'node' });
});

test('greets by name', async () => {
  const out = await handler(ctx({ query: { name: 'Ada' } }));
  assert.equal(out.body.message, 'Hello, Ada!');
});

test('ping', async () => {
  const out = await handler(ctx({ path: '/ping' }));
  assert.equal(out.body, 'pong');
});
