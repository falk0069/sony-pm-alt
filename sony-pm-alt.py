#!/usr/bin/python
import socket, struct, time, socketserver, re, subprocess, sys, logging, logging.handlers
import _thread, requests, os
from threading import Thread
from shutil import move

#  install pip and requests if missing:
#  sudo apt-get install python-pip
#  sudo pip install requests

#CONFIG
#------------------------------------------------------------------
#Probably don't want to change:
BCAST_IP = "239.255.255.250" #standard upnp multicast address--don't change
UPNP_PORT = 1900             #standard upnp multicast port--don't change
GPHOTO_CMD = "gphoto2"
GPHOTO_ARGS = ["-P","--skip-existing"]
GPHOTO_SETTINGS = "~/.gphoto/settings" #default location gphoto2 uses
CUSTOM_LD_LIBRARY_PATH = "/usr/local/lib" #common path if self-compiled

#Might want to change:
PHOTO_DIR = "/var/lib/Sony"  #photo/videos will be downloaded to here
PTP_GUID = os.environ['PTP_GUID']
DEBUG = os.environ['DEBUG'].lower() in ['true', '1', 'yes', 'y']
#------------------------------------------------------------------

#replace '~' if used
GPHOTO_CMD = os.path.expanduser(GPHOTO_CMD)
GPHOTO_SETTINGS = os.path.expanduser(GPHOTO_SETTINGS)
PHOTO_DIR = os.path.expanduser(PHOTO_DIR)
CUSTOM_LD_LIBRARY_PATH = os.path.expanduser(CUSTOM_LD_LIBRARY_PATH)


#check for commandline args
for i,arg in enumerate(sys.argv):
#Let commandline arg override config
  if arg == '-d':
    DEBUG = True
  #Set logging file
  elif arg == '-l':
    if len(sys.argv) > i+1:
      sys.stdout = open(sys.argv[i+1], 'w')
      sys.stderr = open(sys.argv[i+1], 'w')
    else:
      print("Please provide path the log file after -l")
      _thread.interrupt_main()  #exiting program


#Setup Logging Output
logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s")
L = logging.getLogger()
if DEBUG is True:
  L.setLevel(logging.DEBUG)
else:
  L.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logFormatter)
L.addHandler(consoleHandler)

L.info("Server starting")

L.info("Setting download dir [PHOTO_DIR] to: {}".format(PHOTO_DIR))
os.chdir(PHOTO_DIR)
L.info("Setting LD_LIBRARY_PATH to: {}".format(CUSTOM_LD_LIBRARY_PATH))
os.environ["LD_LIBRARY_PATH"] = CUSTOM_LD_LIBRARY_PATH

#Display other settings for debugging
L.debug("BCAST_IP set to: {}".format(BCAST_IP))
L.debug("UPNP_PORT set to: {}".format(UPNP_PORT))
L.debug("GPHOTO_SETTINGS set to: {}".format(GPHOTO_SETTINGS))
L.debug("PTP_GUID set to: {}".format(PTP_GUID))
L.debug("GPHOTO_ARGS set to: {}".format(GPHOTO_ARGS))


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
  if (os.path.isfile(file)):
    with open (file, "r") as myfile:
      current_settings = myfile.read()
      L.debug("Current settings in {}\n----------\n{}----------".format(file,current_settings))

  if ( new_settings != current_settings ):
    L.debug("New settings file needed")
    #backup if previous exists
    if (os.path.isfile(file)):
      #backupfile = file + "." + time.strftime("%Y%m%d%H%M%S") + ".bak"
      backupfile = "{}.{}.bak".format(file,time.strftime("%Y%m%d%H%M%S"))
      L.info("Creating backup: {}".format(backupfile))
      move(file, backupfile)
    with open(file, "w") as myfile:
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
    except socket.error as msg:
      L.error("setsockopt error: %s" % msg[1])
      _thread.interrupt_main()  #exiting program

    sock.settimeout(1)
    while True:
      try:
        data, addr = sock.recvfrom(1024)
        data = data.decode('UTF-8')
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
              if "Sony Corporation" in r.content.decode('UTF-8'):
                L.debug("Camera Found...starting gphoto")
                ValidateUpdateSettings(GPHOTO_SETTINGS, addr[0], PTP_GUID)
                gphoto_cmd = [GPHOTO_CMD,
                              "--port", "ptpip:{}".format(addr[0])] + \
                             GPHOTO_ARGS
                L.debug("Executing: {}".format(gphoto_cmd))
                PROC = subprocess.Popen(gphoto_cmd)
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
