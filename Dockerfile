FROM python:3.8

WORKDIR /user/src/server

ENV FLASK_APP=app.py
ENV FLASK_ENV=development

COPY . .

# Download dependencies
RUN pip3 install -r requirements.txt

EXPOSE 8080

ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.2.1/wait /wait
RUN chmod +x /wait

CMD /wait && python3 -u app.py
