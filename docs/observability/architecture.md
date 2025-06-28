# Observability Architecture

This document outlines the observability stack used by CausaGanha.

- **OpenTelemetry** is configured in the async pipeline to send tracing data via the OTLP exporter.
- **Prometheus** metrics are exposed on port `8001` and include counters and histograms for database sync operations.
- **Grafana** consumes Prometheus metrics and provides dashboards for pipeline health and database sync performance.
- Alerting rules are defined in `observability/alerting.yaml` to notify on excessive failure rates.
