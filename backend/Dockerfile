FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# 生產用 gunicorn；開發可透過 docker-compose command 覆蓋
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app:create_app()"]
