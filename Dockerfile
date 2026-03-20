FROM python:3.13-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

ARG BUILD_DATE=unknown
ENV BUILD_DATE=$BUILD_DATE

WORKDIR /app

# Install Python deps first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create dirs and collect static files
RUN mkdir -p /app/backups /app/staticfiles \
    && SECRET_KEY=build-only python manage.py collectstatic --noinput

EXPOSE 3033

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "3033", "config.asgi:application"]
