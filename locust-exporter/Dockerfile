FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir prometheus_client requests

COPY locust_exporter.py /app/locust_exporter.py

ENV LISTEN_PORT=9324
ENV LOCUST_URL=http://host.docker.internal:8089
ENV SCRAPE_INTERVAL=5

CMD ["python", "locust_exporter.py"]
