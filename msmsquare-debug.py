#! /usr/bin/python3
# Provides CLI debug options for MSM Square
import logging
import msmsquare
from collections import Counter
from pprint import pprint
from datetime import datetime, timedelta, date, time, timezone
from dateutil import tz
import yaml
from sqlalchemy import desc
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-b","--startdate", help="Start Date YYYY-MM-DD", type=str)
    parser.add_argument("-e","--stopdate", help="Stop Date YYYY-MM-DD", type=str)
    parser.add_argument("-l","--locationid", help="Location ID", type=str)
    arguments = parser.parse_args()
    
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

    locationID = arguments.locationid
    beginTime = datetime.strptime(arguments.startdate, "%Y-%m-%d").replace(tzinfo=LOCAL_tzone)
    endTime = datetime.strptime(arguments.stopdate, "%Y-%m-%d").replace(tzinfo=LOCAL_tzone)

    #generate a new report for a certain day
    msmsquare.generateReportDataForDates(beginTime,endTime, locationID,db_session, headers)
    #get report data
    report = msmsquare.getReportDataForDatesFromOneLocation(beginTime,endTime,locationID,db_session, headers)
    #print report data
    pprint(report)

    return

if __name__ == "__main__":
    main()