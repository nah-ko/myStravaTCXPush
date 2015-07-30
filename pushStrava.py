#!/usr/bin/env python

import json
from stravalib import Client, exc, model
from lxml import objectify
import os
import fnmatch
import shutil
from requests.exceptions import ConnectionError, HTTPError
from datetime import datetime,  timedelta

# First, load settings from file
print("Loading settings...")
with open("settings.json", "r") as f:
    settings = json.load(f)

# Then, connect to user Strava account.
print("Connecting to Strava...")
StravaClient = Client()
StravaClient.access_token = settings.get('strava_token')

# You're logged in !
StravaAthlete = StravaClient.get_athlete()
print("Hello, {} {}.\nYou are now connected to Strava.".format(StravaAthlete.firstname,  StravaAthlete.lastname))

# Now we'll try to find activity(ies) to upload.
tcxStorageDir = settings.get('archives_dir') # Where TCX files are stored
Debug = False # If we need to have some more informations...
#Debug = True
Year = datetime.now().strftime("%Y") # This exists because TCX files are like : 2015-06-06T15-23-01.000Z_Walking.tcx
Exclude = ('UploadedToStrava', 'Endomondo', 'runtastic2strava') # List directories we don't want do search into

print("List files to upload...")

# Check if directory exists before go ahead.
if not os.path.exists(tcxStorageDir):
   print("Error listing TCX files in {}: not found\nExiting...".format(tcxStorageDir))
   exit(1)

# Walk trough dir to find files...
for root, dirs, files in os.walk(tcxStorageDir):
   # We don't want to deal with some directories
   dirs[:] = list(filter(lambda x: not x in Exclude, dirs))
   if Debug: print("dirs :\n{}".format(dirs))
   # Find files matching
   for filenames in fnmatch.filter(files, Year+"*.tcx"):
      if Debug: print(os.path.join(root,filenames))
      File = os.path.join(root,filenames)
      # Parse TCX file to get sport type
      try:
          tcxFile = objectify.parse(File)
      except:
          print("Error reading TCX file")
          exit(1)

      tcxRoot = tcxFile.getroot()
      tcxActivity = tcxRoot.Activities.Activity
      tcxSportType = tcxActivity.attrib['Sport']

      # If ActivityType is "Other", then we know that Polar give real sport name information in filename
      if tcxSportType == 'Other':
          tcxFileName_Right = File.split('_')[1]
          tcxSportType = str(tcxFileName_Right.split('.')[0])
      if Debug: print("Hello, activity type for {} file is {}".format(File, tcxSportType))

      # Need to convert sport type into Strava one
      i = 0
      Strava_Sports = model.Activity.TYPES
      if Debug: print("Try to find activity in Strava Sports...")
      while i < len(Strava_Sports):
          if not tcxSportType.find(Strava_Sports[i]) == -1:
              tcxSportType = Strava_Sports[i]
          i = i + 1
          if Debug: print("At {}/{}".format(i,len(Strava_Sports)))
 
      # Next: upload to Strava
      print("Uploading...")
      try:
         upload = StravaClient.upload_activity(
                     activity_file = open(File, 'r'),
                     data_type = 'tcx',
                     private = True if tcxSportType == 'Swim' else False,
                     activity_type = tcxSportType
                     )
      except exc.ActivityUploadFailed as err:
          print("Problem raised: {}".format(err))
          exit(1) # deal with duplicate type of error, if duplicate then continue with next file ? else stop

      except ConnectionError as err:
          print("No Internet connection: {}".format(err))
          exit(1)

      print "Upload succeded.\nWaiting for activity..."

      try:
          upResult = upload.wait()
      except HTTPError as err:
          print("Problem raised: {}\nExiting...".format(err))
          exit(1)

      print("Activity viewable at: https://www.strava.com/activities/{}".format(str(upResult.id)))

      # Now move file to "UploadedToStrava" dir...
      UP2S = "UploadedToStrava/"
      UploadDir = root + UP2S
      try:
         if not os.path.exists(UploadDir):
            os.mkdir(UploadDir)
         shutil.move(File, UploadDir)
      except (IOError, os.error), why:
         print("Unable to move {} to {} because of error: {}".format(File, UploadDir, str(why)))

print("End of the list.")
