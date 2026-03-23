FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install build dependencies, Firefox ESR, and supporting tools for browser automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    firefox-esr \
    wget \
    libdbus-glib-1-2 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxt6 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Create a default Firefox profile for Selenium automation
RUN mkdir -p /data/firefox-profile \
    && firefox-esr --headless -CreateProfile "default /data/firefox-profile" 2>/dev/null || true

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# At container start, patch config.json with Docker-specific defaults, then run the app
COPY scripts/docker_entrypoint.sh /app/scripts/docker_entrypoint.sh
RUN chmod +x /app/scripts/docker_entrypoint.sh
ENTRYPOINT ["/app/scripts/docker_entrypoint.sh"]
