# This module contains functions used to access, manipulate, and download to a local database information from the Square payment processor
# It has been updated/rewritten to work with the Square v2 API
import requests
from collections import defaultdict
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from datetime import datetime, timedelta, timezone
from dateutil import tz
from pprint import pprint
import logging
import yaml

# Load configuration
try:
    with open("config-msmsquare.yaml", 'r') as stream:
        try:
            msmSquareConfig=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
except IOError:
    print("Could not read config-msmsquare.yaml file")

#connect to the squareData cache database, setup SQLAlchemy stuff
db_string = msmSquareConfig['postgresConnection']
db = create_engine(db_string, connect_args={'sslmode':'require'})  
base = declarative_base()
Session = sessionmaker(db)  # Create a session class associated with the database engine

class Location(base):  
    # Create an ORM class for holding the Location data in JSONB format
    __tablename__ = 'locations'
    id = Column(Integer, primary_key=True)
    location_id = Column(String)
    name = Column(String)
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

class Payment(base):  
    # Create an ORM class for holding the Payment data in JSONB format
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    payment_id = Column(String)
    location_id = Column(String)
    order_id = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

class Refund(base):  
    # Create an ORM class for holding the Refund data in JSONB format
    __tablename__ = 'refunds'
    id = Column(Integer, primary_key=True)
    refund_id = Column(String)
    payment_id = Column(String)
    location_id = Column(String)
    order_id = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

class Order(base):  
    # Create an ORM class for holding the Order data in JSONB format
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    order_id = Column(String)
    location_id = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

class Catalog(base):  
    # Create an ORM class for holding the catalog data in JSONB format
    __tablename__ = 'catalog'
    id = Column(Integer, primary_key=True)
    catalog_id = Column(String)
    type = Column(String)
    is_deleted = Column(Boolean)
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

class Payout(base):  
    # Create an ORM class for holding the payout data in JSONB format
    __tablename__ = 'payouts'
    id = Column(Integer, primary_key=True)
    payout_id = Column(String)
    location_id = Column(String)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

class PayoutEntries(base):  
    # Create an ORM class for holding the payout data in JSONB format
    __tablename__ = 'payoutEntries'
    id = Column(Integer, primary_key=True)
    payoutEntry_id = Column(String)
    payout_id = Column(String)
    type = Column(String)
    effective_at = Column(DateTime(timezone=True))
    lastSyncDate = Column(DateTime(timezone=True))
    data = Column(JSONB)

def getLocationsFromSquare(db_session, headers):
    #Get a current list of locations from Square and store in the local database, update any existing records too
    r = requests.get('https://connect.squareup.com/v2/locations', headers=headers)
    response = r.json()
    locations = response['locations']
    for location in locations:
        try:
            locationInDB = db_session.query(Location).filter(Location.data.contains({'id': location['id']})).one()
            # Yes, it's already in the DB so we should update the DB with the passed location dict
            locationInDB.data = location
            locationInDB.name = location['name']
            locationInDB.lastSyncDate = datetime.now(timezone.utc)
            db_session.commit()
        except NoResultFound:
            # The location ID is not in the database yet, add the passed location dict to the database
            db_location = Location(data=location,location_id=location['id'],name=location['name'],lastSyncDate = datetime.now(timezone.utc))
            db_session.add(db_location)
            db_session.commit()
        except MultipleResultsFound:
            raise Exception('Multiple Locations Found in Database with Location ID: {}'.format(location['id']))
    return locations

def getLocations(db_session, headers):
    #Get a current list of locations from the local database
    locationsInDB = db_session.query(Location).all()
    locations = []
    for location in locationsInDB:
        locations.append(location.data)
    return locations

def savePaymentInDB(payment, db_session, headers):
    # Takes in a payment dict, if the payment ID exists in the database it is updated, if not it is added
    try:
        paymentInDB = db_session.query(Payment).filter(Payment.data.contains({'id': payment['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed payment dict
        paymentInDB.data = payment
        paymentInDB.location_id = payment['location_id']
        paymentInDB.order_id = payment['order_id']
        paymentInDB.payment_id = payment['id']
        paymentInDB.created_at = payment['created_at']
        paymentInDB.updated_at = payment['updated_at']
        paymentInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payment ID is not in the database yet, add the passed payment dict to the database
        db_payment = Payment(data=payment,payment_id=payment['id'],order_id=payment['order_id'],location_id=payment['location_id'],created_at = payment['created_at'],updated_at = payment['updated_at'],lastSyncDate = datetime.now(timezone.utc))
        db_session.add(db_payment)
        db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Payments Found in Database with Payment ID: {}'.format(payment['id']))
    return

def saveRefundInDB(refund, db_session, headers):
    # Takes in a refund dict, if the refund ID exists in the database it is updated, if not it is added
    try:
        refundInDB = db_session.query(Refund).filter(Refund.data.contains({'id': refund['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed refund dict
        refundInDB.data = refund
        refundInDB.location_id = refund['location_id']
        refundInDB.order_id = refund['order_id']
        refundInDB.payment_id = refund['payment_id']
        refundInDB.refund_id = refund['id']
        refundInDB.created_at = refund['created_at']
        refundInDB.updated_at = refund['updated_at']
        refundInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The refund ID is not in the database yet, add the passed refund dict to the database
        db_refund = Refund(data=refund,refund_id=refund['id'],payment_id=refund['payment_id'],order_id=refund['order_id'],location_id=refund['location_id'],created_at = refund['created_at'],updated_at = refund['updated_at'],lastSyncDate = datetime.now(timezone.utc))
        db_session.add(db_refund)
        db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Refunds Found in Database with Refund ID: {}'.format(refund['id']))
    return

def savePayoutInDB(payout, db_session, headers):
    # Takes in a payout dict, if the refund ID exists in the database it is updated, if not it is added
    try:
        payoutInDB = db_session.query(Payout).filter(Payout.data.contains({'id': payout['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed payout dict
        payoutInDB.data = payout
        payoutInDB.location_id = payout['location_id']
        payoutInDB.payout_id = payout['id']
        payoutInDB.created_at = payout['created_at']
        payoutInDB.updated_at = payout['updated_at']
        payoutInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payout ID is not in the database yet, add the passed payout dict to the database
        db_payout = Payout(data=payout,payout_id=payout['id'],location_id=payout['location_id'],created_at = payout['created_at'],updated_at = payout['updated_at'],lastSyncDate = datetime.now(timezone.utc))
        db_session.add(db_payout)
        db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Payouts Found in Database with Payout ID: {}'.format(payout['id']))
    return

def savePayoutEntryInDB(payoutEntry, db_session, headers):
    # Takes in a payoutEntry dict, if the refund ID exists in the database it is updated, if not it is added
    try:
        payoutEntryInDB = db_session.query(PayoutEntries).filter(PayoutEntries.data.contains({'id': payoutEntry['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed payoutEntry dict
        payoutEntryInDB.data = payoutEntry
        payoutEntryInDB.payoutEntry_id = payoutEntry['id']
        payoutEntryInDB.payout_id = payoutEntry['payout_id']
        payoutEntryInDB.type = payoutEntry['type']
        payoutEntryInDB.effective_at = payoutEntry['effective_at']
        payoutEntryInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payout ID is not in the database yet, add the passed payoutEntry dict to the database
        db_payoutEntry = PayoutEntries(data=payoutEntry,payoutEntry_id=payoutEntry['id'],payout_id=payoutEntry['payout_id'],effective_at = payoutEntry['effective_at'],type = payoutEntry['type'],lastSyncDate = datetime.now(timezone.utc))
        db_session.add(db_payoutEntry)
        db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Payout Entries Found in Database with Payout Entry ID: {}'.format(payoutEntry['id']))
    return

def saveOrderInDB(order, db_session, headers):
    # Takes in an order dict, if the order ID exists in the database it is updated, if not it is added 
    try:
        orderInDB = db_session.query(Order).filter(Order.data.contains({'id': order['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed payment dict
        orderInDB.data = order
        orderInDB.location_id = order['location_id']
        orderInDB.created_at = order['created_at']
        orderInDB.updated_at = order['updated_at']
        orderInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payment ID is not in the database yet, add the passed payment dict to the database
        db_order = Order(data=order,order_id=order['id'],location_id=order['location_id'],created_at = order['created_at'],updated_at = order['updated_at'],lastSyncDate = datetime.now(timezone.utc))
        db_session.add(db_order)
        db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Orders Found in Database with Order ID: {}'.format(order['id']))
    return

def getPayment(paymentID, db_session, headers):
    # Check the local cache to see if we have that payment data. If yes, return it. If no, get it from square, store it in the local cache, and then return it.
    # Try getting the payment from the database first
    try:
        payment = db_session.query(Payment).filter(Payment.data.contains({'id': paymentID})).one()
        print ("Payment Found in Local DB: {}".format(paymentID))
        return payment.data
    except NoResultFound:
        r = requests.get('https://connect.squareup.com/v2/payments/'+paymentID, headers=headers)
        response = r.json()
        payment = response['payment']
        savePaymentInDB(payment, db_session, headers)
        #print ("Payment Added to Local DB: {}".format(paymentID))
        return payment
    except MultipleResultsFound:
        raise Exception('Multiple Payments Found in Database with Payment ID: {}'.format(paymentID))
        return

def getPaymentsByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    #Get all of the payments that Square has between two dates for a given location
    paymentList = []
    r = requests.get('https://connect.squareup.com/v2/payments?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime, headers=headers)
    response = r.json()
    try:
        payments = response['payments']
        while True:
            for payment in payments:
                logging.info('Processing Payment: %s', payment['id'])
                logging.info(' Payment Date: %s', payment['created_at'])
                savePaymentInDB(payment, db_session, headers)
                paymentList.append(payment['id'])
            # Check to see if the list of payments from Square has been paginated
            try:
                cursor = response['cursor']
                # Yes, it has so obtain the next page of payments
                r = requests.get('https://connect.squareup.com/v2/payments?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime+'&cursor='+cursor, headers=headers)
                response = r.json()
                payments = response['payments']
            except KeyError:
                # There are no more pages of payments to process
                break
    except KeyError:
        #No payments were returned
        pass
    return paymentList

def getOrdersByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    #Get all of the orders that Square has between two dates for a given location
    orderList = []
    payload = {'location_ids':[locationID],'query':{'filter':{'date_time_filter':{'created_at':{'start_at':startTime,'end_at':stopTime}}}}}
    r = requests.post('https://connect.squareup.com/v2/orders/search', headers=headers, json=payload)
    response = r.json()
    try:
        orders = response['orders']
        while True:
            for order in orders:
                logging.info('Processing Order: %s', order['id'])
                saveOrderInDB(order, db_session, headers)
                orderList.append(order['id'])
            # Check to see if the list of orders from Square has been paginated
            try:
                cursor = response['cursor']
                # Yes, it has so obtain the next page of orders
                payload = {'location_ids':[locationID],'query':{'filter':{'date_time_filter':{'created_at':{'start_at':startTime,'end_at':stopTime}}}},'cursor':cursor}
                r = requests.post('https://connect.squareup.com/v2/orders/search', headers=headers, json=payload)
                response = r.json()
                orders = response['orders']
            except KeyError:
                # There are no more pages of payments to process
                break
    except KeyError:
        #No orders were returned
        pass
    return orderList

def getCatalogFromSquare(db_session, headers):
    #Get a current full catalog from Square and store in the local database, update any existing records too
    catalog=[]
    r = requests.get('https://connect.squareup.com/v2/catalog/list', headers=headers)
    response = r.json()
    try:
        catalogObjects = response['objects']
        while True:
            for catalogObject in catalogObjects:
                try:
                    objectInDB = db_session.query(Catalog).filter(Catalog.data.contains({'id': catalogObject['id']})).one()
                    # Yes, it's already in the DB so we should update the DB with the passed object dict
                    objectInDB.data = catalogObject
                    objectInDB.type = catalogObject['type']
                    objectInDB.is_deleted = catalogObject['is_deleted']
                    objectInDB.lastSyncDate = datetime.now(timezone.utc)
                    db_session.commit()
                    catalog.append(catalogObject)
                except NoResultFound:
                    # The object ID is not in the database yet, add the passed object dict to the database
                    db_catalog = Catalog(data=catalogObject,catalog_id=catalogObject['id'],type=catalogObject['type'],is_deleted=catalogObject['is_deleted'],lastSyncDate = datetime.now(timezone.utc))
                    db_session.add(db_catalog)
                    db_session.commit()
                    catalog.append(catalogObject)
                except MultipleResultsFound:
                    raise Exception('Multiple Catalog Objects Found in Database with Object ID: {}'.format(catalogObject['id']))
            # Check to see if the list of objects from Square has been paginated
            try:
                cursor = response['cursor']
                # Yes, it has so obtain the next page of objects
                r = requests.get('https://connect.squareup.com/v2/catalog/list?cursor='+cursor, headers=headers)
                response = r.json()
                catalogObjects = response['objects']
            except KeyError:
                # There are no more pages of payments to process
                break
    except KeyError:
        #No objects were returned
        pass
    return catalog

def getRefundsByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    #Get all of the refunds that Square has between two dates for a given location
    refundList = []
    r = requests.get('https://connect.squareup.com/v2/refunds?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime, headers=headers)
    response = r.json()
    try:
        refunds = response['refunds']
        while True:
            for refund in refunds:
                logging.info('Processing Refund: %s', refund['id'])
                logging.info(' Refund Date: %s', refund['created_at'])
                saveRefundInDB(refund, db_session, headers)
                refundList.append(refund['id'])
            # Check to see if the list of refunds from Square has been paginated
            try:
                cursor = response['cursor']
                # Yes, it has so obtain the next page of refund
                r = requests.get('https://connect.squareup.com/v2/refunds?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime+'&cursor='+cursor, headers=headers)
                response = r.json()
                refunds = response['refunds']
            except KeyError:
                # There are no more pages of refunds to process
                break
    except KeyError:
        #No refunds were returned
        pass
    return refundList

def getPayoutsByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    #Get all of the payouts that Square has between two dates for a given location
    payoutList = []
    r = requests.get('https://connect.squareup.com/v2/payouts?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime, headers=headers)
    response = r.json()
    try:
        payouts = response['payouts']
        while True:
            for payout in payouts:
                logging.info('Processing Payout: %s', payout['id'])
                logging.info(' Payout Date: %s', payout['created_at'])
                savePayoutInDB(payout, db_session, headers)
                payoutList.append(payout['id'])
            # Check to see if the list of payouts from Square has been paginated
            try:
                cursor = response['cursor']
                # Yes, it has so obtain the next page of payouts
                r = requests.get('https://connect.squareup.com/v2/payouts?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime+'&cursor='+cursor, headers=headers)
                response = r.json()
                payouts = response['payouts']
            except KeyError:
                # There are no more pages of payouts to process
                break
    except KeyError:
        #No payouts were returned
        pass
    return payoutList

def getPayoutEntriesByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    # NOTE this gets all the payouts too
    #Get all of the payouts that Square has between two dates for a given location
    payoutList = getPayoutsByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers)
    payoutEntryList = []
    for payout in payoutList:
        r = requests.get('https://connect.squareup.com/v2/payouts/'+payout+'/payout-entries', headers=headers)
        response = r.json()
        try:
            payoutEntries = response['payout_entries']
            while True:
                for payoutEntry in payoutEntries:
                    logging.info('Processing Payout Entry: %s', payoutEntry['id'])
                    logging.info(' Payout Entry Effective Date: %s', payoutEntry['effective_at'])
                    savePayoutEntryInDB(payoutEntry, db_session, headers)
                    payoutEntryList.append(payoutEntry['id'])
                # Check to see if the list of payout entries from Square has been paginated
                try:
                    cursor = response['cursor']
                    # Yes, it has so obtain the next page of payout entries
                    r = requests.get('https://connect.squareup.com/v2/payouts/'+payout+'/payout-entries?cursor='+cursor, headers=headers)
                    response = r.json()
                    payoutEntries = response['payout_entries']
                except KeyError:
                    # There are no more pages of payout entries to process
                    break
        except KeyError:
            #No payout entries were returned
            pass
    return payoutEntryList

