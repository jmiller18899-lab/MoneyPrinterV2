FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install build dependencies for native Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port for Railway
EXPOSE 5000

# Run app.py when the container launches
ENTRYPOINT ["python", "app.py"]