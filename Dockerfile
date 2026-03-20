FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
 && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Bootstrap config if not present
RUN if [ ! -f config.json ]; then cp config.example.json config.json; fi

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run web app when the container launches
EXPOSE 5000
ENTRYPOINT ["python", "src/web_app.py"]
