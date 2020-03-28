FROM python:2-alpine3.9

EXPOSE 15740/tcp
EXPOSE 15740/udp
EXPOSE 1900/udp

ENV PTP_GUID="ff:ff:52:54:00:b6:fd:a9:ff:ff:52:3c:28:07:a9:3a"
ENV DEBUG=false

RUN apk add --no-cache gphoto2
RUN pip install --no-cache requests

WORKDIR /root

ADD make_gphoto_settings.sh .
ADD gphoto_connect_test.sh .

RUN chmod +x make_gphoto_settings.sh
RUN chmod +x gphoto_connect_test.sh

ADD sony-pm-alt.py .

VOLUME /var/lib/Sony

CMD /root/make_gphoto_settings.sh && exec python sony-pm-alt.py
