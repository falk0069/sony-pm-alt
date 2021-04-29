#!/bin/sh
mkdir -p .gphoto
echo "gphoto2=port=ptpip:0.0.0.0
gphoto2=model=PTP/IP Camera
ptp2_ip=guid=$PTP_GUID" > .gphoto/settings