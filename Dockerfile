FROM python:3.6

RUN echo "\nPREPARING\n" && \
    apt-get update && \
    apt-get install -y --no-install-recommends
RUN pip3 install --upgrade pip

COPY ["requirements.txt", "requirements.txt"]
RUN pip3 install -r /requirements.txt

RUN mkdir app
ADD . /app
WORKDIR /app

EXPOSE 8080

RUN chmod 777 entrypoint.sh

RUN ls -la

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python3", "/app/eunlg/server.py", "8080"]
