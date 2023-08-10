# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set environment variables for Pipenv
ENV PIPENV_VENV_IN_PROJECT=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the Pipfile and Pipfile.lock to the container
COPY Pipfile* /app/

# Install Pipenv and the dependencies from Pipfile.lock
RUN pip install pipenv && \
    pipenv install --system --deploy --ignore-pipfile

# Copy the application code to the container
COPY . /app/

# Expose the port on which the FastAPI application will run
EXPOSE 8090

# Run the FastAPI application using Uvicorn
CMD ["pipenv", "run", "uvicorn", "--proxy-headers", "app.main:app", "--port", "8090"]