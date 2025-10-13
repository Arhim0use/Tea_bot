FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TZ=Europe/Moscow
ENV PYTHONPATH=/app

CMD ["python", "bot.py"]

