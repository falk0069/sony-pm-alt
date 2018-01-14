FROM python:2-alpine

RUN apk add --no-cache gphoto2
RUN pip install --no-cache requests

WORKDIR /root

RUN mkdir .gphoto
ADD gphoto-settings .gphoto/settings
ADD sony-pm-alt.py .

VOLUME /var/lib/Sony

CMD exec python sony-pm-alt.py
