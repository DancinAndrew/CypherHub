import multiprocessing
import os

# Gunicorn configuration file

# Server socket
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Worker processes
# Calculation: 2 * CPUs + 1 for standard scaling, but constrained by environment if needed.
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Threads per worker for I/O bound tasks
threads = int(os.getenv("GUNICORN_THREADS", 4))

# Worker class
worker_class = "gthread"

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
