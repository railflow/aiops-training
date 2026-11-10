// Appwrite Function (runtime node-22). Entrypoint: src/main.js. The executor calls the default export once per request.
export default async ({ req, res, log }) => {
  if (req.path === '/ping') {
    return res.text('pong');
  }
  const name = req.query.name ?? 'world';
  log(`greeting ${name}`);
  return res.json({ message: `Hello, ${name}!`, runtime: 'node' });
};
