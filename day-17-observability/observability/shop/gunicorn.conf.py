"""Gunicorn settings. OpenTelemetry must be started AFTER the worker forks, because exporter threads
do not survive a fork; post_fork is the documented place for that."""
bind = "0.0.0.0:8080"
workers = 1
threads = 4
accesslog = None  # the app writes its own structured request logs


def post_fork(server, worker):
    import telemetry

    telemetry.init()
