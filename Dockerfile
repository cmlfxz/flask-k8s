# from myhub.mydocker.com/base/alpine-python:3.5.9

from myhub.mydocker.com/base/python:3.6

copy requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py /opt/microservices/
COPY flask_k8s /opt/microservices/flask_k8s
COPY config /opt/microservices/config
# COPY config.py /opt/microservices/instance/config.py
EXPOSE 8082
WORKDIR /opt/microservices

ENTRYPOINT [ "python","manage.py","runserver","-h","0.0.0.0","-p","8082" ]
# CMD [ "python","manage.py","runserver","-h","0.0.0.0","-p","8081" ]
# ADD cmd.sh /root/
# RUN chmod +x /root/cmd.sh
# CMD ["/root/cmd.sh","arg1"]
