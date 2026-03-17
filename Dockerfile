# Updated Dockerfile for MoneyPrinterV2

FROM python:3.8-slim

# Set the working directory back to /app
WORKDIR /app

# Copy all files into the container
COPY . .

# Run the application
CMD ["python", "src/main.py"]
