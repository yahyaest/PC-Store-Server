FROM python:3.11-alpine
ENV PYTHONUNBUFFERED 1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN apk update && \
 apk add mariadb-connector-c-dev gcc musl-dev mysql mysql-client
RUN pip install -r requirements.txt
COPY . /app
