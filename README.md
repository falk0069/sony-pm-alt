# sony-pm-alt
Transfer pictures wirelessly for a Sony camera without using Playmemories (Sony PM Alternative)

BACKGROUND
I created this project because I wanted to be able to transfer my pictures to my Linux machines, but Playmemories was not available for Linux.  So, I ended up running a mini windows VM within Linux jsut to run Playmemories.  This was a pain and sooo slow.  The slowness had very little to do with the VM and more with the way Sony rescans every image/video.

TECHNOLOGY
The way Sony transfers pictures is via PTP/IP (Picture Transfer Protocol over Internet Protocol).  The moment you enable the 'Send to Computer' option from the Camera it starts braodcasting UPNP UDP packets across the network to multicast address (239.255.255.250:1900).  This is also known as Simple Service Discovery Protocol (SSDP).  At the same time the camera starts up A PTP/IP server on port 15740.  The UPNP packets contain all the connection details.  The Playmemories app (or sony-pm-alt.py) see these packets and then turn around an hit the PTP/IP servers and transfer the pictures.

TRANSFER SOFTWARE: GPHOTO
The sony-pm-alt.py pytho script is really only the UPNP listener.  The real magic comes from the open source gphoto software: http://www.gphoto.com/.  Basically once the PTP/IP mode is enabled ('Send to Computer' option selected), you can run a command like this to download all the pictures/videos:
gphoto2 -P --port ptpip:192.168.1.222 --skip-existing   #assuming your camera's IP is 192.168.1.222
This was tested with version 2.5.8.1 using a Sony Alpha ILCE-5000  (version 2.5.8 had an issue for me)

MAIN CHALLENGE
Sony requires some non-standard packets to display the 'Sending...' on the camera.  This also goes for the automatic shut down feature when done.  Without this you have about 2 minutes to transfer the picture before the camera stops and you have no confirmation that it worked.  Also, the camera will remain on so you can't walk away or else your battery will continue to drain.  I was hoping there would be one magic packet to turn these options on, but this doesn't seem to be the case.  Doing a series of tcpdumps I was able to determine what packets make it work.  I started off with over a 100 packets being needed and have finally narrowed it down to 23 packets.  I'm sure it can be narrowed down more, but I haven't found a whole lot of rhyme or reason to it.  I was also hoping I could send these packets directly from python using a different tcp session than gphoto, but no luck.  So, I ended up really hacking up the libgphoto code to make this work.  Maybe one day these can be incorporated in the main gphoto code.  More on the edits later.

LINKING THE CAMERA AND THE PTP-GUID
In order to use this method you do still need to initially install Playmemories on a PC/MAC and link the camera to it.  The key is to obtain the PTP-GUID.  I'm not sure at this point the easiest way to obtain this is it doesn't seem to appear in any config files or settings menus that I can find.  I did find a partial match to the GUID used on the USB controller in the windows registry.  Basically the last 12 digit on this registry entry matched for me if anyone else want to validate:
HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Enum\USB\VID_14CD&PID_6D00\5&c1e6cce&0&1
ContainerID = {a4d7a2f7-c5ae-11e4-93ac-080027f5164f}

Otherwise the for-sure method is to run tcpdump/wireshark and watch for the first ptp packet (port 15740).  You will see something like this:
00000000  2c 00 00 00 01 00 00 00  00 00 00 00 00 00 00 00 ,....... ........
00000010  ff ff 08 00 27 f5 16 4f  57 00 49 00 4e 00 37 00 ....'..O W.I.N.7.
00000020  2d 00 56 00 4d 00 00 00  00 00 01 00             -.V.M... ....

Where bytes 9 - 24 are the GUID: 0000000000000000ffff080027f5164f

Wireshark will nicely display this in the info window like so:
Init Command Request GUID: 0000000000000000ffff080027f5164f Name: WIN7-VM
