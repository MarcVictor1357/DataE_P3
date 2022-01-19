FROM ubuntu:20.04

ADD requirements.txt .
ADD main.py .
ADD artists-data.csv .
ADD lyrics-data.csv .

RUN apt update && apt install python3-pip libmysqlclient-dev -y && pip install -r requirements.txt

EXPOSE 8000

CMD uvicorn main:request_server --host 0.0.0.0

