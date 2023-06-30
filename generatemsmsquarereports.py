#! /usr/bin/python3
import logging
import msmsquare
from collections import Counter
from pprint import pprint
from datetime import datetime, timedelta, date, time, timezone
from dateutil import tz

import yaml

logging.basicConfig(level=logging.INFO)

# Load configuration
try:
    with open("config-msmsquare.yaml", 'r') as stream:
        try:
            msmSquareConfig=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
except IOError:
    print("Could not read config-msmsquare.yaml file")

applicationID = msmSquareConfig['squareApplicationID']
accessToken = msmSquareConfig['squareApplicationAccessToken']

# Timezone stuff
UTC_tzone = tz.gettz('UTC')
LOCAL_tzone = tz.gettz(msmSquareConfig['localTimezone'])

headers = {"Authorization":"Bearer "+ accessToken, 'Square-Version':msmSquareConfig['squareAPIVersion']}

db_session = msmsquare.Session() # create a working database session for version 2

#Ensure all the required tables exist in the database
msmsquare.base.metadata.create_all(msmsquare.db)

beginDate=date(2023,5,1)
endDate=date(2023,5,31)
locationID='M225NFD7TJ8ZJ' #CHSL
#locationID='5RT3Z6SAPGQB7' #ESL
#locationID='8CY2M680JGBJE' #MSM
#locationID='LBR2E5T341WDH' #Webstore

for location in msmsquare.getLocations(db_session, headers):
    #do for each location
    msmsquare.generateReportDataForDates(beginDate,endDate, location['id'],db_session, headers)

#test = msmsquare.generateReportDataForDates(beginDate,endDate, locationID,db_session, headers)
# test = msmsquare.getPayment('E2EIz42nt0BCvi75DxmyPsMF', db_session, headers)

#test = msmsquare.getLineItemsFromOrder('MEOlFrwQ5BxWYclwA76H8i9eV', db_session, headers)

# pprint(test)

# NOTES: 