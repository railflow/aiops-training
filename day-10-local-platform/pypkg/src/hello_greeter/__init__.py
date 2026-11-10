def make_greeting(name=None):
    cleaned = (name or "").strip()
    return f"Hello, {cleaned or 'world'}!"
