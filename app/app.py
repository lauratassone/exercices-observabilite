#!/usr/bin/env python3
"""
Sample Flask application instrumented with prometheus_client.

Exposes:
    /                -> homepage
    /api/users       -> list users (random latency)
    /api/orders      -> list orders (random latency, sometimes errors)
    /metrics         -> Prometheus scrape endpoint

This app is provided to students for the PromQL and exporter exercises.
"""

import random
import time
from flask import Flask, jsonify, request
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

app = Flask(__name__)

# ----------------------------------------------------------------------
# Prometheus metrics
# ----------------------------------------------------------------------

# Counter: number of HTTP requests
REQUESTS = Counter(
    "demo_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Histogram: latency of HTTP requests
LATENCY = Histogram(
    "demo_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Gauge: number of in-flight requests
IN_FLIGHT = Gauge(
    "demo_http_requests_in_flight",
    "Requests currently being handled",
)

# Gauge: simulated business KPI
ACTIVE_USERS = Gauge(
    "demo_active_users",
    "Number of currently active users (simulated)",
)


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@app.route("/")
def index():
    REQUESTS.labels("GET", "/", "200").inc()
    return jsonify({"service": "demo-api", "status": "ok"})


@app.route("/api/users")
def users():
    IN_FLIGHT.inc()
    start = time.time()
    # simulate variable latency
    time.sleep(random.uniform(0.01, 0.3))
    REQUESTS.labels("GET", "/api/users", "200").inc()
    LATENCY.labels("/api/users").observe(time.time() - start)
    IN_FLIGHT.dec()
    return jsonify([
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
        {"id": 3, "name": "Charlie"},
    ])


@app.route("/api/orders")
def orders():
    IN_FLIGHT.inc()
    start = time.time()
    time.sleep(random.uniform(0.02, 0.6))

    # ~10% of requests fail
    if random.random() < 0.10:
        REQUESTS.labels("GET", "/api/orders", "500").inc()
        LATENCY.labels("/api/orders").observe(time.time() - start)
        IN_FLIGHT.dec()
        return jsonify({"error": "internal"}), 500

    REQUESTS.labels("GET", "/api/orders", "200").inc()
    LATENCY.labels("/api/orders").observe(time.time() - start)
    IN_FLIGHT.dec()
    return jsonify([{"id": 101, "total": 42.50}])


@app.route("/metrics")
def metrics():
    # update simulated business metric
    ACTIVE_USERS.set(random.randint(50, 200))
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
