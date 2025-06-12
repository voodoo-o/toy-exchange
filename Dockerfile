FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EXPOSE 8443

ENV PYTHONPATH=/app
ENV TESTING=true

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]