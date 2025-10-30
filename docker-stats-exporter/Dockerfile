FROM python:3.11-alpine

# Minimal tools for docker CLI invocation
RUN apk add --no-cache docker-cli

# Python deps
RUN pip install --no-cache-dir prometheus_client

WORKDIR /app
COPY exporter.py /app/exporter.py

ENV CONTAINER_NAME=keycloak
ENV SCRAPE_INTERVAL=5
ENV LISTEN_PORT=9323
ENV DOCKER_HOST=tcp://host.docker.internal:2375

EXPOSE 9323
CMD ["python", "exporter.py"]
