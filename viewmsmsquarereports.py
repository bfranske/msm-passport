#! /usr/bin/python3
import logging
import msmsquare
from collections import Counter
from pprint import pprint
from datetime import datetime, timedelta, date, time, timezone
from dateutil import tz
from flask import Flask, render_template, session, request, redirect, url_for
import weasyprint

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

reportData = [{'location': 'CHSL',
        'date': 'May 4, 2019',
        'data': {'charters': 0,
            'donations': 0,
            'fares': 5750,
            'memberships': 0,
            'merchandise_nontaxable': 0,
            'merchandise_taxable': 4325,
            'partial_refunds': 0,
            'passes': 0,
            'uncategorized': 0,
            'processing_fees': -105,
            'special_events': {'Pumpkin': 0},
            'tax_collected': 321,
            'tenders': {'CASH': 5750, 'CREDIT_CARD': 3800, 'NO_SALE': 0, 'OTHER': 525}}},
            {'location': 'ESL',
            'date': 'May 5, 2019',
            'data': {'charters': 100,
                'donations': 200,
                'fares': 3050,
                'memberships': 0,
                'merchandise_nontaxable': 0,
                'uncategorized': 0,
                'merchandise_taxable': 4025,
                'partial_refunds': 0,
                'passes': 0,
                'processing_fees': -1105,
                'special_events': {},
                'tax_collected': 1300,
                'tenders': {'CASH': 7676, 'CREDIT_CARD': 265, 'NO_SALE': 0, 'OTHER': 322}}}]

app = Flask(__name__)

@app.route("/")
def index():
    try:
        beginYear=int(request.args['by'])
    except:
        beginYear=2022
    try:
        beginMonth=int(request.args['bm'])
    except:
        beginMonth=4
    try:
        beginDay=int(request.args['bd'])
    except:
        beginDay=1
    try:
        endYear=int(request.args['ey'])
    except:
        endYear=2022
    try:
        endMonth=int(request.args['em'])
    except:
        endMonth=4
    try:
        endDay=int(request.args['ed'])
    except:
        endDay=30
    beginDate=date(beginYear,beginMonth,beginDay)
    endDate=date(endYear,endMonth,endDay)
    reportData=msmsquare.getReportDataForDatesFromDBAllLocations(beginDate,endDate, db_session, headers)
    return render_template('dailyreport.html', reportData=reportData, LOCAL_tzone = tz.gettz('America/Chicago'))

if __name__ == "__main__":
    app.run()