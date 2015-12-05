#!/usr/bin/python
import socket, struct, time, SocketServer, re, subprocess, sys, logging, logging.handlers
import thread, requests, os
from threading import Thread
from shutil import move

#  install pip and requests if missing:
#  sudo apt-get install python-pip
#  sudo pip install requests

#config
BCAST_IP = "239.255.255.250"
UPNP_PORT = 1900
GPHOTO_CMD_ARGS = [os.path.expanduser("~/gphoto2-2.5.8/gphoto2/gphoto2"),"-P","--skip-existing"]
GPHOTO_SETTINGS = "~/.gphoto/settings"
PHOTO_DIR = "/var/lib/Sony"
CUSTOM_LD_LIBRARY_PATH = "/usr/local/lib"
PTP_GUID = "00:00:00:00:00:00:00:00:ff:ff:08:00:27:f5:16:4f"

#Setup Logging Output
logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s")
L = logging.getLogger()
L.setLevel(logging.DEBUG) #set to INFO or ERROR for less logging
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
L.addHandler(consoleHandler)

L.info("Server starting")

os.chdir(PHOTO_DIR)
os.environ["LD_LIBRARY_PATH"] = CUSTOM_LD_LIBRARY_PATH

#NOTES...
#The following USN have been seen coming from the Sony camera when turning
#on the 'Send to Computer' option:
#USN: uuid:00000000-0001-0010-8000-784b87a9899a
#USN: uuid:00000000-0001-0010-8000-784b87a9899a::upnp:rootdevice
#USN: uuid:00000000-0001-0010-8000-784b87a9899a::urn:microsoft-com:device:mtp:1
#USN: uuid:00000000-0001-0010-8000-784b87a9899a::urn:microsoft-com:service:MtpNullService:1
#
#associated NT:
#NT: uuid:00000000-0001-0010-8000-784b87a9899a
#NT: upnp:rootdevice
#NT: urn:microsoft-com:device:mtp:1
#NT: urn:microsoft-com:service:MtpNullService:1
#
#Server:
#SERVER: FedoraCore/2 UPnP/1.0 MINT-X/1.8.1

#updates the gphoto settings (makes backup if changed)
def ValidateUpdateSettings( file, ip, guid):
  new_settings = """gphoto2=port=ptpip:{}
gphoto2=model=PTP/IP Camera
ptp2_ip=guid={}
""".format(ip,guid)
  current_settings = ""
  if (os.path.isfile(os.path.expanduser(file))):
    with open (os.path.expanduser(file), "r") as myfile:
      current_settings = myfile.read()

  if ( new_settings != current_settings ):
    L.debug("New settings file needed")
    #backup if previous exists
    if (os.path.isfile(os.path.expanduser(file))):
      #backupfile = file + "." + time.strftime("%Y%m%d%H%M%S") + ".bak"
      backupfile = "{}.{}.bak".format(file,time.strftime("%Y%m%d%H%M%S"))
      L.info("Creating backup: {}".format(backupfile))
      move(os.path.expanduser(file), os.path.expanduser(backupfile))
    with open(os.path.expanduser(file), "w") as myfile:
      myfile.write(new_settings)
    L.info("New settings written to {}".format(file))
    L.debug("\n----------\n{}----------".format(new_settings))
  return;


class Responder(Thread):
  interrupted = False
  def run(self):

    global GPHOTO_SETTINGS, PTP_GUID

    #dummy process to define a PROC to use poll (check if still running)
    PROC = subprocess.Popen("/bin/echo")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(('', UPNP_PORT))
    mreq = None
    try:
      mreq = struct.pack("4sl", socket.inet_aton(BCAST_IP), socket.INADDR_ANY)
      sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    except socket.error, msg:
      L.error("socket error: %s" % msg[1])
      thread.interrupt_main()  #exiting program

    sock.settimeout(1)
    while True:
      try:
        data, addr = sock.recvfrom(1024)
      except socket.error:
        if self.interrupted:
          sock.close()
          return
      else:
        if "MtpNullService" in data and PROC.poll() is not None:
          L.info("received MtpNullService from {}".format(addr))
          L.debug(" data:\n{}".format(data.strip()))
          searchObj = re.search( r'LOCATION: (.+\.xml)', data, re.I)
          if searchObj and "://" in searchObj.group(1):
            try:
              r = requests.get(searchObj.group(1), timeout=4)
            except requests.exceptions.RequestException:
               L.warn("Connection Error")
            else:
              L.debug("Got XML - verify if our camera")
              if "Sony Corporation" in r.content:
                L.debug("Camera Found...starting gphoto")
                ValidateUpdateSettings(GPHOTO_SETTINGS, addr[0], PTP_GUID)
                PROC = subprocess.Popen(GPHOTO_CMD_ARGS)
          L.debug("----------------------")
          L.debug("  ")
#        else:
#          L.info("received data - ignoring")
#          L.debug("----------------------")
#          L.debug("  ")

  def stop(self):
    self.interrupted = True


if __name__ == '__main__':
  responder = Responder()
  responder.start()
  try:
    while True:
      responder.join(1)
  except (KeyboardInterrupt, SystemExit):
    L.info("Waiting for connections to end before exiting")
  responder.stop()
