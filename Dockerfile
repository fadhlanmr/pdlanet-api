# Use an official Python runtime as the base image
FROM python:3.9

# set display port to avoid crash
ENV DISPLAY=:99
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

# install google chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get -y update
RUN apt-get install -y google-chrome-stable

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_115`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# Expose the port on which the FastAPI application will run
EXPOSE 8090

# Run the FastAPI application using Uvicorn
CMD ["pipenv", "run", "uvicorn", "--proxy-headers", "app.main:app", "--host", "0.0.0.0", "--port", "8090"]