FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask flask-cors numpy requests

# Copy backend files
COPY backend/ /app/backend/

EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1

CMD ["python", "backend/app.py"]
