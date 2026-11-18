FROM python:3.11-slim

# Prevent Python from writing .pyc and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

WORKDIR /app

# Install build dependencies if needed for packages like pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# OpenShift runs containers with an arbitrary non-root UID belonging to root group (GID 0).
# Ensure all files and directories in /app are accessible by group 0.
RUN chgrp -R 0 /app && chmod -R g=u /app

EXPOSE 8080

# Collect static files, apply migrations, and run gunicorn
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && gunicorn bloodbank.wsgi:application --bind 0.0.0.0:8080 --workers 2"]
