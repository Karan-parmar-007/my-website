FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations, bootstrap data, and start server
CMD ["sh", "-c", "alembic upgrade head && python bootstrap_data.py && uvicorn main:app --host 0.0.0.0 --port 8000"]