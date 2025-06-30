# Use an official Python runtime as a parent image
FROM python:3.9-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Expose the port that the application will listen on
# Cloud Run expects applications to listen on the port specified by the PORT environment variable
ENV PORT 8080
EXPOSE 8080

# Run the application using Gunicorn
# The command specifies that Gunicorn should run the 'app' object from 'app.py'
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
