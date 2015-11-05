# sony-pm-alt
Transfer pictures wirelessly for a Sony camera without using Playmemories (Sony PM Alternative)

BACKGROUND:
-----------------------------------------------------------------
I created this project because I wanted to be able to transfer my pictures to my Linux machines, but Playmemories was not available for Linux.  So, I ended up running a mini windows VM within Linux just to run Playmemories.  This was a pain and sooo slow.  The slowness had very little to do with the VM and more with the way Sony rescans every image/video.

TECHNOLOGY:
-----------------------------------------------------------------
The way Sony transfers pictures is via PTP/IP (Picture Transfer Protocol over Internet Protocol).  The moment you enable the 'Send to Computer' option from the Camera it starts braodcasting UPNP UDP packets across the network to multicast address (239.255.255.250:1900).  This is also known as Simple Service Discovery Protocol (SSDP).  At the same time the camera starts up A PTP/IP server on port 15740.  The UPNP packets contain all the connection details.  The Playmemories app (or sony-pm-alt.py) see these packets and then turn around an hit the PTP/IP servers and transfer the pictures.

TRANSFER SOFTWARE: GPHOTO2:
-----------------------------------------------------------------
The sony-pm-alt.py pytho script is really only the UPNP listener.  The real magic comes from the open source gphoto software: http://www.gphoto.com/.  Basically once the PTP/IP mode is enabled ('Send to Computer' option selected), you can run a command like this to download all the pictures/videos: <br>
gphoto2 -P --port ptpip:192.168.1.222 --skip-existing   #assuming your camera's IP is 192.168.1.222 <br>
This was tested with version 2.5.8.1 using a Sony Alpha ILCE-5000  (version 2.5.8 had an issue for me) <br>

MAIN CHALLENGE:
-----------------------------------------------------------------
Sony requires some non-standard packets to display the 'Sending...' on the camera.  This also goes for the automatic shut down feature when done.  Without this you have about 2 minutes to transfer the picture before the camera stops and you have no confirmation that it worked.  Also, the camera will remain on so you can't walk away or else your battery will continue to drain.  I was hoping there would be one magic packet to turn these options on, but this doesn't seem to be the case.  Doing a series of tcpdumps I was able to determine what packets make it work.  I started off with over a 100 packets being needed and have finally narrowed it down to 23 packets.  I'm sure it can be narrowed down more, but I haven't found a whole lot of rhyme or reason to it.  I was also hoping I could send these packets directly from python using a different tcp session than gphoto, but no luck.  So, I ended up really hacking up the libgphoto code to make this work.  Maybe one day these can be incorporated in the main gphoto code.  More on the edits later.

LINKING THE CAMERA AND THE PTP-GUID:
-----------------------------------------------------------------
In order to use this method you do still need to initially install Playmemories on a PC/MAC and link the camera to it.  The key is to obtain the PTP-GUID.  I'm not sure at this point the easiest way to obtain this is it doesn't seem to appear in any config files or settings menus that I can find.  I did find a partial match to the GUID used on the USB controller in the windows registry.  Basically the last 12 digit on this registry entry matched for me if anyone else want to validate: <br>
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\USB\VID_14CD&PID_6D00\5&c1e6cce&0&1 <br>
ContainerID = {a4d7a2f7-c5ae-11e4-93ac-080027f5164f}

Otherwise the for-sure method is to run tcpdump/wireshark and watch for the first ptp packet (port 15740).  You will see something like this: <br>
```
00000000  2c 00 00 00 01 00 00 00  00 00 00 00 00 00 00 00 ,....... ........
00000010  ff ff 08 00 27 f5 16 4f  57 00 49 00 4e 00 37 00 ....'..O W.I.N.7.
00000020  2d 00 56 00 4d 00 00 00  00 00 01 00             -.V.M... ....
```
Where bytes 9 - 24 are the GUID: 0000000000000000ffff080027f5164f <br>

Wireshark will nicely display this in the info window like so: <br>
Init Command Request GUID: 0000000000000000ffff080027f5164f Name: WIN7-VM <br>

GETTING GPHOTO2:
-------------------------------------------------------------------
To test things out quickly (without the addtional packet injection hack to get the Sony to gracefully transfer files) you probably will want to just grab the latest gphoto2/libgphoto2.  If you are using a Debian/Ubuntu based Linux distro run this: <br>
```sudo apt-get install gphoto2```  Then to quickly test that your camera will work:<br>
```
1. Disable playmemories (disable network, block port 15740, turn PC, etc)
2. Turn Camera's 'Send to Computer' option on
3. Run: gphoto2 --port ptpip:192.168.1.222 --summary  #Update IP accordingly
Note: First time will probably fail since the GUID will be wrong
4. Update the ~/.gphoto/settings that should now exist and replace with correct GUID
5. Run the gphoto command again <br>
```

DOWNLOAD SOURCE FOR LIBGPHOTO2 and GPHOTO2:
-------------------------------------------------------------------
Here are four methods for downloading libghoto2:
1) The developers of gphoto kindly provided a temporary snapshot of version 2.5.8.1.  This is the exact version I was working with.  I'm not sure how long it will be available but here is the link: <br>
  http://www.lst.de/~mm/libgphoto2-2.5.8.1.tar.bz2 <br>
  (Note to unzip: ```tar -xvf libgphoto2-2.5.8.1.tar.bz2```) <br>
  <br>
2) Otherwise the bleeding edge version is located on github: https://github.com/gphoto/libgphoto2/archive/master.zip <br>
  <br>
3) Or you can do a git clone: <br>
  ```git clone https://github.com/gphoto/libgphoto2.git``` <br>
  (Note you need git installed.  E.g. ```sudo apt-get install git```) <br>
  <br>
4) Or assuming a version >2.5.8 is out you could grab a stable version at sourceforce: <br>    
  http://sourceforge.net/projects/gphoto/files/libgphoto/ <br>

To download ghoto2: <br>
1) Stable version at sourceforce: <br> 
  http://sourceforge.net/projects/gphoto/files/gphoto/ <br>
2) Bleeding edge at github: <br>
  https://github.com/gphoto/gphoto2/archive/master.zip <br>
3) Git clone: <br>
  ```git clone https://github.com/gphoto/gphoto2.git``` <br>


COMPILING LIBGPHOTO2 and GPHOTO2:
--------------------------------------------------------------------
First you need to make sure you have these pre-reqs: <br>
pkg-config <br>
m4 <br>
gettext <br>
autopoint <br>
autoconf <br>
automake <br>
libtool <br>
 <br>
For example on Debian/Ubuntu run: <br>
```
sudo apt-get install pkg-config m4 gettext autopoint autoconf automake libtool
```
 <br>
Next make sure the source is unzipped for both and then run these commands in each of the source directories: <br>
```
-#this with validate the 'configure' script is ready
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
COMPILING IN THE CUSTOMIZATION TO LIBGPHOTO2:
--------------------------------------------------------------------
Replace this file:  libgphoto2/camlibs/ptp2/ptpip.c with the one on this site <br>
Rerun :
```
make
sudo make install
```
TEST! <br>

