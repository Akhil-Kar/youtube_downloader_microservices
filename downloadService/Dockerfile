# Use a Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the Python script into the container
COPY . /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose any ports your app might need (for RabbitMQ connection)
EXPOSE 5672

# Command to run the Python application
CMD ["python", "app.py"]
