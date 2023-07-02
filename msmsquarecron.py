#! /usr/bin/python3
import logging
import msmsquare
from collections import Counter
from pprint import pprint
from datetime import datetime, timedelta, date, time, timezone
from dateutil import tz
import yaml
from  sqlalchemy import desc

def main():
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

    logging.info('Starting Cron DB Load')

    #Get all of the location IDs from square into the database api v2
    logging.info('Getting Locations')
    locations = msmsquare.getLocationsFromSquare(db_session,headers)

    #Get all of the catalog objects from square into the database api v2
    logging.info('Getting Catalog Objects')
    msmsquare.getCatalogFromSquare(db_session, headers)

    getNewSquareData(db_session, headers, locations)

    logging.info('Cron DB Load Complete')

    logging.info('Generating Report Data')

    generateReports(db_session, headers, locations)

    logging.info('Done Generating Report Data')

    return

# Get the date of the last report in the local Square database, go back 3 days, and create reports until now
def generateReports(db_session, headers, locations):
    lastReport = db_session.query(msmsquare.DailyReport).order_by(desc(msmsquare.DailyReport.reportStartDate)).limit(1).all()

    # Go back 3 days
    beginTime=lastReport[0].reportStartDate - timedelta(days = 3)
    endTime=datetime.now(timezone.utc)

    for location in locations:
        #do for each location
        msmsquare.generateReportDataForDates(beginTime,endTime, location['id'],db_session, headers)

    return

# Get the date of the last transaction data in the local Square database, go back 3 days, and pull data from square until now
def getNewSquareData(db_session, headers, locations):
    lastOrder = db_session.query(msmsquare.Order).order_by(desc(msmsquare.Order.updated_at)).limit(1).all()

    # Get the latest updated order from the local database and go back 3 days
    beginTime=lastOrder[0].updated_at - timedelta(days = 3)
    endTime=datetime.now(timezone.utc)

    #Get all of the payments from square into the database api v2
    loadPayments(locations, db_session, headers, beginTime, endTime)

    #Get all of the orders from square into the database api v2
    loadOrders(locations, db_session, headers, beginTime, endTime)

    #Get all of the refunds from square into the database api v2
    loadRefunds(locations, db_session, headers, beginTime, endTime)

    #Get all of the payouts and payout entries from square into the database api v2
    loadPayoutEntries(locations, db_session, headers, beginTime, endTime)

    return

def loadPayments(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all payments from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
    logging.info('Getting Payments')
    for location in locations:
        endTime=endTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        beginTime=beginTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        payments = msmsquare.getPaymentsByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
    return

def loadRefunds(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all refunds from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
    logging.info('Getting Refunds')
    for location in locations:
        endTime=endTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        beginTime=beginTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        msmsquare.getRefundsByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
    return

def loadPayoutEntries(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all payouts and payout entries from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
    logging.info('Getting Payouts and Payout Entries')
    for location in locations:
        endTime=endTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        beginTime=beginTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        msmsquare.getPayoutEntriesByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
    return

def loadOrders(locations, db_session, headers, beginTimeDT, endTimeDT):
	#Load all orders from all locations since Nov 1, 2018 (MSM Square Inception Date) into the database
    logging.info('Getting Orders')
    for location in locations:
        endTime=endTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        beginTime=beginTimeDT.strftime('%Y-%m-%dT%H:%M:%SZ')
        msmsquare.getOrdersByDateRangeFromSquare(beginTime, endTime, location['id'], db_session, headers)
    return

if __name__ == "__main__":
    main()