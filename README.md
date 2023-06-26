# am_restore.py
A Python script to help you restore your deleted Apple Music playlists using a "Apple Media Services information.zip" file downloaded from https://privacy.apple.com.

# What's it for?
If you were once a subscriber to Apple Music but let your membership lapse, you may be surprised to find that Apple delete all of your Apple Music playlists a few weeks after your subscription ends. So if you re-subscribe at a later date your old playlists will be gone.

This script is intended to give you a means of getting at least some of those old playlists back. We don't know if it works as we intend because we don't have an abandoned Apple Music account to try it on. However if you want to give it a try, please feel free to step through the steps below and let us know how you get on. It definitely won't do any harm to your Apple Music library or account - it simply creates a PLIF file which can be read by Playlisty and used to restore individual playlists. If it works, please let us know. And if it doesn't work, please get in touch and we'll see if we can fix it.

You can contact us using the "Contact Us" link on the Playlisty Settings page.

# How does it work?
For legal reasons Apple retain a significant amount of data on you and your usage of their services. You can request an archive file of this data from them and, by using this script on the Apple Music service files, we should be able to re-create some or all of your missing playlists.

# What's the process?
There are 2 steps to this process, and you'll need a Mac for the second:

## Request your "Apple Media Services information" from Apple
1. Log-on to https://privacy.apple.com using the Apple Id that you use for Apple Music (this is very important if you use different Ids for Apple Music & iCloud)
2. Select "Obtain a copy of your data" and then "Apple Media Services information". Then "Continue".
3. Choose a maximum file size (the minimum of 1Gb should be fine) and then "Complete request".
4. Wait. For a day or two. Or three. Keep checking back here: https://privacy.apple.com/account to see if your file is ready for download.
5. Once it is ready, download your file (it is called "Apple Media Services information.zip") to the Downloads folder on your Mac

## Import it into your Apple Music account
1. Download the file am_restore.py (above) to the same directory as your "Apple Media Services information.zip" file
2. Start a command prompt in the same directory (in Finder, right-click on the folder name and select "New Terminal at Folder")
3. At the prompt, type `chmod +x am_restore.py` and then hit enter. This makes the file executable.
4. Then type: `./am_restore.py` and hit enter, to run the script. Wait until finished. Observe you have a new file called "Apple Music Library Archive.plif".
5. Open Playlisty and use the files tab to import the new PLIF file from the above directory. From within Playlisty you can then select which playlists you want to import, as you would with any multi-playlist import.
