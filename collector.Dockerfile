FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir requests

# Copy collector script
COPY collector.py /app/

# Set environment variables
ENV PYTHONUNBUFFERED=1

CMD ["python", "collector.py"]
