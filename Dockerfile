# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME /app
ENV PORT 8080

# Create and set the working directory
WORKDIR $APP_HOME

# Install system dependencies if any (e.g., for certain Python packages)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Install Poetry or Pipenv if you use them, or copy requirements.txt
# For requirements.txt:
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the working directory
# Ensure only necessary files are copied by using .dockerignore
COPY ./api $APP_HOME/api
COPY ./trademark_core $APP_HOME/trademark_core
COPY main.py .
# The root main.py is for Cloud Functions, for Cloud Run we use api.main:app directly with Uvicorn.
# If api.main.py relies on any other root files or specific structures, adjust as needed.

# Expose the port the app runs on
EXPOSE $PORT

# Command to run the application using Uvicorn
# The FastAPI app instance is assumed to be named 'app' in 'api.main'
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"] 