#!/bin/sh
# usage: ./gphoto_connect_test ip.of.camera
gphoto2 --get-all-files --port ptpip:$1 --filename=/var/lib/Sony/%f.%C