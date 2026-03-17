FROM python:3.8

# Set the working directory
WORKDIR /app/src

# Copy the requirements.txt from the parent directory
COPY ../requirements.txt .

# Install the dependencies from the parent directory
RUN pip install --no-cache-dir -r ../requirements.txt

# Copy the rest of the application code
COPY . .

# Set the command to run the application
CMD ["python", "app.py"]
