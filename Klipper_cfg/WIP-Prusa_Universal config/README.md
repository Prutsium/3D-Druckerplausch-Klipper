This is my new approach of making configs since i had to take care of 5 different configs i went for a Universal Prusa / Bear config set.
The most of you are using the Prusa / Bear with the stock Einsy. Personally i dont use the Einsy anymore but i use a Duet 3 Mini 5+ and a Octopus board.
This made keeping the other configs up to date for me difficult and as said had to replicate my edits on 5 other configs.

For this reason i wen for a more universal config where more things are splitted out and makes updates more easy.
The main file will be printer.cfg but you will need all files to copu to your klipper_config.

If you like to add something dont edit the files as when i make updates those will be overwritten.
Instead of that add them to the printer.cfg at the end as they will overrule what is in the configs.
You even dont need to remove the old part as the new part will overwrite those settings.

The selection is by default for a stock prusa with the stock extruder and a Einsy board.
If you want to use something else then remove the corrospondig # infront of that config.

Contribution is appriciated please use the issue tracker from Git and if interesting / helpfull we can add those requests.

This config is made of parts of my own but also scraped from various Klipper channels.
A special thanks to Khuaong for helping with the MMU part, Q66 for some great additions and Alexz who is always assisting if i want to create some stupid macro :)
