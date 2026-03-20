FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install build dependencies for native Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run src/main.py when the container launches
EXPOSE 5000
ENTRYPOINT ["python", "src/web_app.py"]