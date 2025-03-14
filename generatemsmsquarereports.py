#! /usr/bin/python3
import logging
import msmsquare
from collections import Counter
from pprint import pprint
from datetime import datetime, timedelta, date, time, timezone
from dateutil import tz
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine

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

#connect to the squareData cache database, setup SQLAlchemy stuff
db_string = msmSquareConfig['postgresConnection']
db = create_engine(db_string, connect_args={'sslmode':'disable'})
Session = sessionmaker(db)  # Create a session class associated with the database engine

db_session = Session() # create a working database session for version 2

beginDate=date(2025,1,1)
endDate=date(2025,3,12)
#locationID='M225NFD7TJ8ZJ' #CHSL
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