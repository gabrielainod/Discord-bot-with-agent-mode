FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# stats survive restarts if you mount a volume on /app/data
VOLUME ["/app/data"]

CMD ["python", "-m", "tripletbot"]
