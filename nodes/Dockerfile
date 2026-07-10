FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask

# Copy nodes simulator files
COPY nodes/ /app/nodes/

# Expose ports 6001, 6002, 6003
EXPOSE 6001 6002 6003

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Defaults to RU simulator; compose will override CMD
CMD ["python", "nodes/ru_sim.py"]
