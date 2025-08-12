FROM python:3.11-slim
WORKDIR /app

# System deps (optional but handy if you later add psycopg[c])
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python","-u","/app/main.py"]