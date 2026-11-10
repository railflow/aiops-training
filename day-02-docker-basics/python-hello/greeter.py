def make_greeting(name=None):
    """Return a greeting for name; blank or missing names become 'world'."""
    cleaned = (name or "").strip()
    return f"Hello, {cleaned or 'world'}!"
