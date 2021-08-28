This is my new approach of making configs since i had to take care of 5 different configs i went for a Universal Prusa / Bear config set.
The most of you are using the Prusa / Bear with the stock Einsy. Personally i dont use the Einsy anymore but i use a Duet 3 Mini 5+ and a Octopus board.
This made keeping the other configs up to date for me difficult and as said had to replicate my edits on 5 other configs.

For this reason i went for a more universal config where more things are splitted out and makes updates more easy.
The main file will be printer.cfg but you will need all files to copu to your klipper_config.

If you like to add something dont edit the files as when i make updates those will be overwritten.
Instead of that add them to the printer.cfg at the end as they will overrule what is in the configs.
You even dont need to remove the old part as the new part will overwrite those settings.

The selection is by default for a stock prusa with the stock extruder and a Einsy board.
If you want to use something else then remove the corrospondig # infront of that config.

Contribution is appriciated please use the issue tracker from Git and if interesting / helpfull we can add those requests.

This config is made of parts of my own but also scraped from various Klipper channels.
A special thanks to Khuaong for helping with the MMU part, Q66 for some great additions and Alexz who is always assisting if i want to create some stupid macro :)

Make sure you make a copy of your old klipper configuration before copying this to the klipper_config folder.
Due i have to use some defaults for PID and Z_Offset i suggest you copy from your old config the part that say's do not edit like the following example
#*# <---------------------- SAVE_CONFIG ---------------------->
#*# DO NOT EDIT THIS BLOCK OR BELOW. The contents are auto-generated.

Copy the whole block with contents and put this in the printer.cfg and run PID tuning after that for the bed and extruder.

Also add your MCU in mcu.cfg as then i can create update on the cfg's without overwriteing your MCU settings
I use a simplified way of MCU selection through Symlinks so you dont have to bother about the wier name like: usb-Klipper_stm32f446xx_3D002A000950534E4E313020-if00
But after creating a Symlink it would be: btt-octopus-11.

To create a Symlink use the following commands on your Pi:
pi@fluiddpi:~ $ lsusb
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 001 Device 037: ID 1d50:614e OpenMoko, Inc.
Bus 001 Device 002: ID 2109:3431 VIA Labs, Inc. Hub
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
pi@fluiddpi:~ $

In my case i am interested in the ID of the OpenMoko device what is the Octopus.
Next is to create the Symlink with the following command: (this will open the Nano editor with a blanc file)
sudo nano /etc/udev/rules.d/99-usb-serial.rules
Edit this file and put there: (in my example you see it for the Octopus)
SUBSYSTEMS=="usb", ATTRS{idProduct}=="614e",  ATTRS{idVendor}=="1d50", ACTION=="add", SYMLINK+="btt-octopus-11"

Save this file with CTRL-X and check if the printer has now a new name with ls /dev it should show there the name of the printer.
Now edit mcu.cfg (n ano ~/klipper_config/mcu.cfg ) and make the serial line like this (with your printer name)
serial: /dev/btt-octopus-11
Save it with CTRL-X and done you now can reach the printer by an easy name.

