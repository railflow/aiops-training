"""Appwrite Function (runtime python-3.12). Entrypoint: src/main.py. The runtime calls main(context) once per request."""


def main(context):
    if context.req.path == "/ping":
        return context.res.text("pong")
    name = context.req.query.get("name", "world")
    context.log(f"greeting {name}")
    return context.res.json({"message": f"Hello, {name}!", "runtime": "python"})
