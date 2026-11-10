# Test image for the Home Assistant integration (HA does not support Windows hosts).
# Build:  docker build -t nspanel-ha-tests -f tests_ha/Dockerfile .
# Run:    docker run --rm -v "$PWD:/work" nspanel-ha-tests
FROM python:3.14-slim
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /work
COPY requirements_test.txt /tmp/requirements_test.txt
RUN pip install --no-cache-dir -r /tmp/requirements_test.txt
ENV PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-m", "pytest", "-p", "no:cacheprovider", "-q"]
