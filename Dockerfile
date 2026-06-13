FROM python:3.11-slim

WORKDIR /app

COPY requirements_docker.txt .

RUN pip install --no-cache-dir -r requirements_docker.txt

COPY definitions.py .
COPY definitions_ic.py .

EXPOSE 3000

CMD ["dagster", "dev", "-f", "definitions.py", "-h", "0.0.0.0", "-p", "3000"]
