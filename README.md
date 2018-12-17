# sony-pm-alt
Transfer pictures wirelessly for a Sony camera without using Playmemories (Sony PM Alternative)

BACKGROUND:
-----------------------------------------------------------------
I created this project because I wanted to be able to transfer my pictures to my Linux machines, but Playmemories was not available for Linux.  So, I ended up running a mini windows VM within Linux just to run Playmemories.  This was a pain and sooo slow.  The slowness had very little to do with the VM and more with the way Sony rescans every image/video.

TECHNOLOGY:
-----------------------------------------------------------------
The way Sony transfers pictures is via PTP/IP (Picture Transfer Protocol over Internet Protocol).  The moment you enable the 'Send to Computer' option from the Camera it starts broadcasting UPNP UDP packets across the network to the multicast address (239.255.255.250:1900).  This is also known as Simple Service Discovery Protocol (SSDP).  At the same time the camera starts up A PTP/IP server on port 15740.  The UPNP packets contain all the connection details.  The Playmemories app (or sony-pm-alt.py) see these packets and then turn around an hit the PTP/IP servers and transfer the pictures.

TRANSFER SOFTWARE: GPHOTO2:
-----------------------------------------------------------------
The sony-pm-alt.py pytho script is really only the UPNP listener.  The real magic comes from the open source gphoto software: http://www.gphoto.com/.  Basically once the PTP/IP mode is enabled ('Send to Computer' option selected), you can run a command like this to download all the pictures/videos: <br>
```gphoto2 -P --port ptpip:192.168.1.222 --skip-existing```   #assuming your camera's IP is 192.168.1.222 <br>
This was tested with version 2.5.8.1 using a Sony Alpha ILCE-5000  (version 2.5.8 had an issue for me) <br>

MAIN CHALLENGE:
-----------------------------------------------------------------
Sony requires some non-standard packets to display the 'Sending...' on the camera.  This also goes for the automatic shut down feature when done.  Without this you have about 2 minutes to transfer the picture before the camera stops and you have no confirmation that it worked.  Also, the camera will remain on so you can't walk away or else your battery will continue to drain.  I was hoping there would be one magic packet to turn these options on, but this doesn't seem to be the case.  Doing a series of tcpdumps I was able to determine what packets make it work.  I started off with over a 100 packets being needed and have finally narrowed it down to 23 packets (update: 4 packets to start and 3 packets to end).  I was also hoping I could send these packets directly from python using a different tcp session than gphoto, but no luck.  So, I ended up really hacking up the libgphoto code to make this work.  The developer of libgphoto was then kind enough to work with me and incorporate changes to make things work without the hacking.

LINKING THE CAMERA AND THE PTP-GUID:
-----------------------------------------------------------------
In order to use this tool you need to link the camera and generate the PTP-GUID.  I'm going to list out a few method.

###Method 1: Playmemories on a PC/MAC
If you already have Playmemories installed and want to switch to Linux this is the way to go.  Bascially, after you are are "connected" your GUID will be:<br>
<code>00:00:00:00:00:00:00:00:ff:ff:aa:bb:cc:dd:ee:ff</code><br>
where <code>aa:bb:cc:dd:ee:ff</code> is the MAC Address of your primary interface that communicates with your camera.  On windows you can see the MAC Address by running 'ipconfig /all' and looking at the 'Physical Address'.  On Mac run 'ifconfig' and look at the 'ether' value.

###Method 2: Sony-guid-setter
Thanks to Clemens Fruhwirth we now have a GUID setting option from Linux.  He provided some reverse engineered code that requires compiling but can link the camera and set the GUID.  This is the option to use if you don't have access to a Windows/Mac.  More on how to compile and run this in the next section.  But basically once compiled you connect your camera via a usb cable and run it like: <code>sony-guid-setter -g YOUR_CAMERA_VID:PID</code> and it will link and set the GUID to <code>ff:ff:52:54:00:b6:fd:a9:ff:ff:52:3c:28:07:a9:3a</code>.  If you feel insecure you can change this.  More on this later.

###Method 3: tcpdump/wireshark
This is really the same as method 1, but if GUID is still unknown you can run tcpdump/wireshark and verify what it is.  What you would do is run tcpdump/wireshark after you used PM on Windows/Mac and watch for the first ptp packet (port 15740).  You will see something like this: <br>
```
00000000  2c 00 00 00 01 00 00 00  00 00 00 00 00 00 00 00 ,....... ........
00000010  ff ff 08 00 27 f5 16 4f  57 00 49 00 4e 00 37 00 ....'..O W.I.N.7.
00000020  2d 00 56 00 4d 00 00 00  00 00 01 00             -.V.M... ....
```
Where bytes 9 - 24 are the GUID: 0000000000000000ffff080027f5164f <br>

Wireshark will nicely display this in the info window like so: <br>
Init Command Request GUID: 0000000000000000ffff080027f5164f Name: WIN7-VM <br>

COOL NEW SONY-GUID-SETTER:
-------------------------------------------------------------------
So, in order to use this new tool you will need to compile it.  The main prereq is the development package for libusb-1.0 version > 1.0.16.  If you are on a newer Debian distro you likely can just run <code>sudo apt-get install libusb-1.0.0.dev</code>. On a newer Fedora you can run <code>sudo dnf install libusbx-devel</code>.

Then to compile run: <code>gcc sony-guid-setter.c -lusb-1.0 -o sony-guid-setter</code><br>
<br>
On older Redhat/Centos or any other older Linux distro, you probably won't be so lucky, the package may be missing or too old. What I ended up doing is grabbing libusb from sourceforge and compiling using these steps: <br>
```
wget https://sourceforge.net/projects/libusb/files/latest/download?source=files -O libusb-1.0.tar.bz2
tar -xvf libusb-1.0.tar.bz2
cd libusb-1.0.*
#need prereq udev to compile
 sudo yum install libudev-devel      #if Redhat-like
 sudo apt-get install libudev-dev    #if Debian-like
./configure
make
sudo make install            #installs to /usr/local/ by default
gcc -Wl,-rpath -Wl,/usr/local/lib -I/usr/local/include -L/usr/local/lib sony-guid-setter.c -lusb-1.0 -o sony-guid-setter
```
Note: if you are concerned about the hardcoded <code>ff:ff:52:54:00:b6:fd:a9:ff:ff:52:3c:28:07:a9:3a</code> just edit lines 300 and 301 to fit your needs and compile.<br>
<br>
Next you need to find the VID:PID of you camera.  So, just plug your camera into your PC via a USB cable and turn it on.  Then run <code>lsusb</code>.  You will see something like this:
```
Bus 001 Device 002: ID 1871:0d01 Aveo Technology Corp. USB2.0 Camera
Bus 003 Device 007: ID 054c:0994 Sony Corp.
Bus 004 Device 002: ID 046d:c001 Logitech, Inc. N48/M-BB48/M-UK96A [FirstMouse Plus]
```
In the case above the <code>054c:0994</code> is what you want.<br>
<br>
You can then run something like this to link the camera and set the GUID
```
sudo ./sony-guid-setter -g 054c:0994
```
If you are paranoid running this with sudo you can "chown" /dev/bus/usb/xxx/yyy to your user (where xxx and yyy is the Bus and Device number listed with 'lsusb'


Run in Docker (or manually see below)
-----------------------------------------------

0. Set your camera with default GUID (see the above section)

`$ ./sony-guid-setter -g YOUR_CAMERA_VID:PID`

1. Build image

`$ docker build . -t sony-pm-alt`

2. Run

`$ docker run --name=sony-pm-alt --net=host -v /folder/for/incoming/photos:/var/lib/Sony sony-pm-alt`


GETTING GPHOTO2:
-------------------------------------------------------------------
To test things out quickly (without the compiling or modifying) you probably will want to just grab the latest gphoto2/libgphoto2.  If you are using a Debian/Ubuntu based Linux distro run this: <br>
```sudo apt-get install gphoto2```  
Then to quickly test that your camera will work:<br>
```
1. Disable playmemories (disable network, block port 15740, turn off PC, etc)
2. Turn Camera's 'Send to Computer' option on
3. Run: gphoto2 --port ptpip:192.168.1.222 --summary  #Update IP accordingly
Note: First time will probably fail since the GUID will be wrong
4. Update the ~/.gphoto/settings that should now exist and replace with correct GUID
5. Run the gphoto command again
```

<b>If you have version 2.5.9 or greater, you shouldn't need to do the following downloading and compiling sections</b>


DOWNLOAD SOURCE FOR LIBGPHOTO2 and GPHOTO2 (shouldn't be needed anymore):
-------------------------------------------------------------------
###Here are three methods for downloading libgphoto2: <br>
1) The bleeding edge version is located on github: https://github.com/gphoto/libgphoto2/archive/master.zip <br>
  <br>
2) Or you can do a git clone: <br>
  ```git clone https://github.com/gphoto/libgphoto2.git``` <br>
  (Note you need git installed.  E.g. ```sudo apt-get install git```) <br>
  <br>
3) Or assuming a version >2.5.8 is out you could grab a stable version at sourceforce: <br>    
  http://sourceforge.net/projects/gphoto/files/libgphoto/ <br>

###And three methods for downloading gphoto2: <br>
1) Stable version at sourceforce: <br> 
  http://sourceforge.net/projects/gphoto/files/gphoto/ <br>
2) Bleeding edge at github: <br>
  https://github.com/gphoto/gphoto2/archive/master.zip <br>
3) Git clone: <br>
  ```git clone https://github.com/gphoto/gphoto2.git``` <br>


COMPILING LIBGPHOTO2 and GPHOTO2  (shouldn't be needed anymore):
--------------------------------------------------------------------
First you need to make sure you have these pre-reqs: <br>
pkg-config <br>
m4 <br>
gettext <br>
autopoint <br>
autoconf <br>
automake <br>
libtool <br>
libpopt-dev <br>
libltdl-dev <br>
 <br>
For example on Debian/Ubuntu run: <br>
```
sudo apt-get install pkg-config m4 gettext autopoint autoconf automake libtool libpopt-dev libltdl-dev
```
On CentOS/Redhat run: <br>
```
sudo yum install pkgconfig m4 gettext gettext-devel autoconf automake libtool popt-devel libtool-ltdl-devel
```
 <br>
Next make sure the source is unzipped for both and then run these commands in each of the source directories (do libgphoto2 first): <br>
```
-#this will validate the 'configure' script is ready
 autoreconf --install --symlink -f
-#use a custom prefix so we don't affect other versions installed
 ./configure --prefix=/usr/local
-#does the compiling
 make            
-#deploy the code
 sudo make install                     

To run then update your LD_LIBRARY_PATH and kick off the command:
export LD_LIBRARY_PATH=/usr/local/lib
/usr/local/bin/gphoto2 --version
```
COMPILING IN THE CUSTOMIZATION TO LIBGPHOTO2  (shouldn't be needed anymore):
--------------------------------------------------------------------
No customizations are needed at this time.  From time to time I might add something in here.  One item I want to continue exploring is the 'Sending' message vs. the 'Sending - automatically shutting down when complete' message. <br>
<br>
To test any customizations, rerun :
```
make
sudo make install
```
TEST! <br>


USING THE PYTHON SCRIPT - sony-pm-alt.py
--------------------------------------------------------------------
This is just a basic python server that will listen for correct UPNP broadcast.  What you will need to do is edit it and update the top few line with your correct information (e.g. paths and GUID).  Once configured, run it.  It shouldn't do much until to you turn on the Sony camera and try to send to PC.  Hopefully it works.  I also include a simple start script to help auto start it when you PC boots up.  


TROUBLESHOOTING:
-----------------------------------------------------------------
* Make sure you linked the camera.  See LINKING THE CAMERA AND THE PTP-GUID section <br>

* Edit the sony-pm-alt.py script and update line 19 to: ```DEBUG = True``` <br>

* Manually run the script: ```./sony-pm-alt.py``` <br>

* Turn on your camera and do the 'Send to Computer' <br>
  At this point you should see logs being printed from the sony-pm-alt.py script with details.
  
* If you don't, try running ghoto2 directly, but first you need to determine the camera's IP. <br>
  To do this you have about 2 minutes to figure it out after you select the 'Send to Computer' option.<br>

* The easiest method is probably going to be to log into your Internet router and look for the connected wireless client<br>

* You could also try running tcpdump and watch for upnp traffic: ```sudo tcpdump -i any udp port 1900``` <br>
  You should see lines like this:  ```12:18:50.948572 IP 192.168.1.253.27998 > 239.255.255.250.ssdp: UDP, length 291``` <br>
  Where ```192.168.1.253``` is the IP you want. <br>

* Once you have the IP, do the 'Send to Computer' again and run gphoto2 with the correct IP.  Example: ```gphoto2 --port ptpip:192.168.1.253 --summary``` <br>

* If this was the first running, it may have failed due to a bad GUID.  So, validate the ~/.gphoto/settings file and make sure the GUID is correct.  If you used the sony-guid-setter, set it to: ```00:00:00:00:00:00:00:00:ff:ff:08:00:27:f5:16:4f``` <br>

* Run the gphoto2 command again and make sure it returns without errors <br>

* Feel free to log a ticket with your logs for help debugging <br>
