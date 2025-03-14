#! /usr/bin/python3
import logging
import msmsquare
from datetime import datetime, timedelta, timezone
from dateutil import tz
from collections import Counter
import requests
from pprint import pprint
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

def loadPayments(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all payments from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
	for location in locations:
		endTime=endTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		beginTime=beginTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		payments = msmsquare.getPaymentsByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
	return

def loadRefunds(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all refunds from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
	for location in locations:
		endTime=endTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		beginTime=beginTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		msmsquare.getRefundsByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
	return

def loadPayoutEntries(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all payouts and payout entries from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
	for location in locations:
		endTime=endTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		beginTime=beginTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		msmsquare.getPayoutEntriesByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
	return

def loadOrders(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all orders from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
	for location in locations:
		endTime=endTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		beginTime=beginTimeDT.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
		msmsquare.getOrdersByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
	return

#True inception is Nov. 1, 2018
beginTime=datetime(2024,5,1,0,0,0,tzinfo=LOCAL_tzone)
endTime=datetime.now(timezone.utc)
#endTime=datetime(2023,1,1,0,0,0,tzinfo=LOCAL_tzone)

#Get all of the location IDs from square into the database api v2
logging.info('Getting Locations')
locations = msmsquare.getLocationsFromSquare(db_session,headers)

#Get all of the catalog objects from square into the database api v2
logging.info('Getting Catalog Objects')
msmsquare.getCatalogFromSquare(db_session, headers)

#Get all of the payments from square into the database api v2
logging.info('Getting Payments')
loadPayments(locations, db_session, headers, beginTime, endTime)

#Get all of the orders from square into the database api v2
logging.info('Getting Orders')
loadOrders(locations, db_session, headers, beginTime, endTime)

#Get all of the refunds from square into the database api v2
logging.info('Getting Refunds')
loadRefunds(locations, db_session, headers, beginTime, endTime)

#Get all of the payouts and payout entries from square into the database api v2
logging.info('Getting Payouts and Payout Entries')
loadPayoutEntries(locations, db_session, headers, beginTime, endTime)

logging.info('DB Load Complete')