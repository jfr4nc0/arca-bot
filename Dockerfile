FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (removed Chrome/ChromeDriver as we use Selenium service)
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    cron \
    locales \
    && echo "es_ES.UTF-8 UTF-8" >> /etc/locale.gen \
    && echo "es_AR.UTF-8 UTF-8" >> /etc/locale.gen \
    && locale-gen es_ES.UTF-8 \
    && locale-gen es_AR.UTF-8 \
    && update-locale LANG=es_AR.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# Set Spanish locale environment variables
ENV LANG es_AR.UTF-8
ENV LC_ALL es_AR.UTF-8

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Copy poetry.lock and pyproject.toml
COPY pyproject.toml ./

# Install Poetry
RUN pip install poetry

# Install dependencies (without installing the current project)
RUN poetry config virtualenvs.create false \
    && poetry lock && poetry install --only=main --no-root --no-interaction --no-ansi

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x ./scripts/start.sh
RUN chmod +x ./scripts/start_debug.sh

# Expose port
EXPOSE 8000

# Run the application
CMD ["./scripts/start.sh"]
