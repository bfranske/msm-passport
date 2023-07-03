# This module contains functions used to access, manipulate, and download to a local database information from the Square payment processor
# It has been updated/rewritten to work with the Square v2 API
import requests
from collections import defaultdict
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, DateTime, Boolean, desc
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from datetime import datetime, timedelta, date, time, timezone
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

base = declarative_base()

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
    version = Column(String)
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

class DailyReport(base):  
	# Create an ORM class for holding the Daily Report data in JSONB format
	__tablename__ = 'dailyReports'
	id = Column(Integer, primary_key=True)
	location_id = Column(String)
	location_name = Column(String)
	reportCreationDate = Column(DateTime(timezone=True))
	reportStartDate = Column(DateTime(timezone=True))
	reportEndDate = Column(DateTime(timezone=True))
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

def getLocationByID(locationID, db_session, headers):
    locationInDB = db_session.query(Location).filter(Location.location_id==locationID).one()
    location = {'location_id':locationInDB.location_id, 'name':locationInDB.name}
    return location


def savePaymentInDB(payment, db_session, headers):
    # Takes in a payment dict, if the payment ID exists in the database it is updated, if not it is added
    try:
        paymentInDB = db_session.query(Payment).filter(Payment.data.contains({'id': payment['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed payment dict
        logging.debug('Payment Found in DB, updating: %s', payment['id'])
        paymentInDB.data = payment
        paymentInDB.location_id = payment['location_id']
        paymentInDB.order_id = payment['order_id']
        paymentInDB.payment_id = payment['id']
        paymentInDB.created_at = payment['created_at']
        paymentInDB.updated_at = payment.get('updated_at')
        paymentInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payment ID is not in the database yet, add the passed payment dict to the database
        logging.debug('Payment NOT Found in DB, adding: %s', payment['id'])
        db_payment = Payment(data=payment,payment_id=payment['id'],order_id=payment['order_id'],location_id=payment['location_id'],created_at=payment['created_at'],updated_at=payment.get('updated_at'),lastSyncDate = datetime.now(timezone.utc))
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
        refundInDB.updated_at = refund.get('updated_at')
        refundInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The refund ID is not in the database yet, add the passed refund dict to the database
        db_refund = Refund(data=refund,refund_id=refund['id'],payment_id=refund['payment_id'],order_id=refund['order_id'],location_id=refund['location_id'],created_at = refund['created_at'],updated_at = refund.get('updated_at'),lastSyncDate = datetime.now(timezone.utc))
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
        payoutInDB.updated_at = payout.get('updated_at')
        payoutInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payout ID is not in the database yet, add the passed payout dict to the database
        db_payout = Payout(data=payout,payout_id=payout['id'],location_id=payout['location_id'],created_at = payout['created_at'],updated_at = payout.get('updated_at'),lastSyncDate = datetime.now(timezone.utc))
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
        orderInDB.updated_at = order.get('updated_at')
        orderInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The payment ID is not in the database yet, add the passed payment dict to the database
        db_order = Order(data=order,order_id=order['id'],location_id=order['location_id'],created_at = order['created_at'],updated_at = order.get('updated_at'),lastSyncDate = datetime.now(timezone.utc))
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
        logging.debug('Payment Found in Local DB: %s',paymentID)
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
                logging.debug('Processing Payment: %s', payment['id'])
                logging.debug(' Payment Date: %s', payment['created_at'])
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

def getPaymentsAndOrdersByDateRange(startTime, stopTime, locationID, db_session, headers):
    #Get all of the payment and associated order IDs between two dates for a given location
    paymentsAndOrders = []
    try:
        paymentsInDB = db_session.query(Payment).filter(Payment.location_id == locationID, Payment.created_at >= startTime, Payment.created_at < stopTime).all()
        for payment in paymentsInDB:
            logging.debug('Processing Payment: %s', payment.payment_id)
            logging.debug(' Payment Date: %s', payment.created_at)
            if payment.data['status'] == 'FAILED' or payment.data['status'] == 'CANCELED':
                #do not include failed or cancelled payments in the payments and orders, sometimes they have orderids which don't really exist
                pass
            else:
                paymentsAndOrders.append({'paymentID': payment.payment_id, 'orderID': payment.order_id})
        return paymentsAndOrders
    except:
        return

def getLineItemsFromOrder(orderID, db_session, headers):
    try:
        orderInDB = db_session.query(Order).filter(Order.order_id == orderID).one()
        orderData = orderInDB.data
        if not 'line_items' in orderData:
            logging.debug('No line items in Order: %s', orderID)
            return -1
        return orderData['line_items']
    except NoResultFound:
        logging.debug('Order NOT Found in DB: %s', orderID)
    except MultipleResultsFound:
        raise Exception('Multiple Orders Found in Database with Order ID: {}'.format(orderID))
    return

def getReturnedLineItemsFromOrder(orderID, db_session, headers):
    lineItems = []
    try:
        orderInDB = db_session.query(Order).filter(Order.order_id == orderID).one()
        orderData = orderInDB.data
        for ireturn in orderData['returns']:
            for item in ireturn['return_line_items']:
                lineItems.append(item)
    except NoResultFound:
        logging.debug('Order NOT Found in DB: %s', orderID)
    except MultipleResultsFound:
        raise Exception('Multiple Orders Found in Database with Order ID: {}'.format(orderID))
    return lineItems

def getCategoryForObject(objectID, catalogVersion, db_session, headers):
    # Returns the category ID and category name of an item or item variation
    # Try from local first
    try:
        objectInDB = db_session.query(Catalog).filter(Catalog.catalog_id == objectID).one()
        catalogData = objectInDB.data
        if catalogData['type'] == 'ITEM_VARIATION':
            category = getCategoryForObject(catalogData['item_variation_data']['item_id'], catalogVersion, db_session, headers)
            return category
        elif catalogData['type'] == 'ITEM':
            if not 'category_id' in catalogData['item_data']:
                category = {'categoryID': -1}
                return category
            else:
                categoryID = catalogData['item_data']['category_id']
        else:
            logging.debug('ITEM or ITEM VARIATION not returned for Object ID: %s', objectID)
            return
    except NoResultFound:
        r = requests.get('https://connect.squareup.com/v2/catalog/object/'+objectID+'?catalog_version='+str(catalogVersion), headers=headers)
        response = r.json()
        object = response['object']
        saveCatalogObjectInDB(object, db_session, headers)
        logging.debug('Object Added to Local DB: %s', objectID)
        if object['type'] == 'ITEM_VARIATION':
            category = getCategoryForObject(object['item_variation_data']['item_id'], catalogVersion, db_session, headers)
            return category
        elif object['type'] == 'ITEM':
            if not 'category_id' in object['item_data']:
                category = {'categoryID': -1}
                return category
            else:
                categoryID = object['item_data']['category_id']

    except MultipleResultsFound:
        raise Exception('Multiple Objects Found in Database with Object ID: {}'.format(objectID))
        return
    #Get category name too
    try:
        categoryInDB = db_session.query(Catalog).filter(Catalog.catalog_id == categoryID).one()
        categoryName = categoryInDB.data['category_data']['name']
    except NoResultFound:
        print('No category for: '+categoryID)
        r = requests.get('https://connect.squareup.com/v2/catalog/object/'+categoryID+'?catalog_version='+str(catalogVersion), headers=headers)
        response = r.json()
        saveCatalogObjectInDB(object, db_session, headers)
        categoryName = response['category_data']['name']
    category = {'categoryID': categoryID, 'categoryName': categoryName}
    return category

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
                logging.debug('Processing Order: %s', order['id'])
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

def getOrder(orderID, db_session, headers):
    # Check the local cache to see if we have that order data. If yes, return it. If no, get it from square, store it in the local cache, and then return it.
    # Try getting the order from the database first
    try:
        refund = db_session.query(Order).filter(Order.data.contains({'id': orderID})).one()
        print ("Order Found in Local DB: {}".format(orderID))
        return refund.data
    except NoResultFound:
        r = requests.get('https://connect.squareup.com/v2/orders/'+orderID, headers=headers)
        response = r.json()
        order = response['order']
        saveOrderInDB(order, db_session, headers)
        #print ("Order Added to Local DB: {}".format(orderID))
        return order
    except MultipleResultsFound:
        raise Exception('Multiple Orders Found in Database with Order ID: {}'.format(orderID))
        return

def getCatalogFromSquare(db_session, headers):
    #Get a current full catalog from Square and store in the local database, update any existing records too
    catalog=[]
    r = requests.get('https://connect.squareup.com/v2/catalog/list', headers=headers)
    response = r.json()
    try:
        catalogObjects = response['objects']
        while True:
            for catalogObject in catalogObjects:
                saveCatalogObjectInDB(catalogObject, db_session, headers)
                catalog.append(catalogObject)
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

def saveCatalogObjectInDB(catalogObject, db_session, headers):
    # Takes in an object dict, if the object ID exists in the database it is updated, if not it is added
    try:
        objectInDB = db_session.query(Catalog).filter(Catalog.data.contains({'id': catalogObject['id']})).one()
        # Yes, it's already in the DB so we should update the DB with the passed object dict
        objectInDB.data = catalogObject
        objectInDB.type = catalogObject['type']
        objectInDB.version = catalogObject['version']
        objectInDB.is_deleted = catalogObject['is_deleted']
        objectInDB.lastSyncDate = datetime.now(timezone.utc)
        db_session.commit()
    except NoResultFound:
        # The object ID is not in the database yet, add the passed object dict to the database
        db_catalog = Catalog(data=catalogObject,catalog_id=catalogObject['id'],type=catalogObject['type'],is_deleted=catalogObject['is_deleted'],lastSyncDate = datetime.now(timezone.utc))
        db_session.add(db_catalog)
        db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Catalog Objects Found in Database with Catalog Object ID: {}'.format(catalogObject['id']))
    return

def getRefundsByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    #Get all of the refunds that Square has between two dates for a given location
    refundList = []
    r = requests.get('https://connect.squareup.com/v2/refunds?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime, headers=headers)
    response = r.json()
    try:
        refunds = response['refunds']
        while True:
            for refund in refunds:
                logging.debug('Processing Refund: %s', refund['id'])
                logging.debug(' Refund Date: %s', refund['created_at'])
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

def getRefundsByDateRange(startTime, stopTime, locationID, db_session, headers):
    #Get all of the refund, payment, and associated order IDs between two dates for a given location
    refunds = []
    refundsInDB = db_session.query(Refund).filter(Refund.location_id == locationID, Refund.created_at >= startTime, Refund.created_at < stopTime ).all()
    for refund in refundsInDB:
        refunds.append({'refundID': refund.refund_id, 'paymentID': refund.payment_id,'orderID': refund.order_id})
    return refunds

def getRefund(refundID, db_session, headers):
    # Check the local cache to see if we have that refund data. If yes, return it. If no, get it from square, store it in the local cache, and then return it.
    # Try getting the refund from the database first
    try:
        refund = db_session.query(Refund).filter(Refund.data.contains({'id': refundID})).one()
        logging.debug('Refund Found in Local DB: %s',refundID)
        return refund.data
    except NoResultFound:
        r = requests.get('https://connect.squareup.com/v2/refunds/'+refundID, headers=headers)
        response = r.json()
        refund = response['refund']
        saveRefundInDB(refund, db_session, headers)
        #print ("Refund Added to Local DB: {}".format(refundID))
        return refund
    except MultipleResultsFound:
        raise Exception('Multiple Refunds Found in Database with Refund ID: {}'.format(refundID))
        return

def getPayoutsByDateRangeFromSquare(startTime, stopTime, locationID, db_session, headers):
    #Get all of the payouts that Square has between two dates for a given location
    payoutList = []
    r = requests.get('https://connect.squareup.com/v2/payouts?location_id='+locationID+'&begin_time='+startTime+'&end_time='+stopTime, headers=headers)
    response = r.json()
    try:
        payouts = response['payouts']
        while True:
            for payout in payouts:
                logging.debug('Processing Payout: %s', payout['id'])
                logging.debug(' Payout Date: %s', payout['created_at'])
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
                    logging.debug('Processing Payout Entry: %s', payoutEntry['id'])
                    logging.debug(' Payout Entry Effective Date: %s', payoutEntry['effective_at'])
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

def combineIntoDefaultDict(d, new_d):
	# When passed a default dict and a second dict, sum the values of the second dict into the default dict
	for k, v in new_d.items():
		if isinstance(v, dict):
			combineIntoDefaultDict(d[k], v)
		else: 
			d[k] = d.setdefault(k, 0) + v

def default_dict_to_regular(d):
	# Take a defaultdict and convert it to a regular dict including nested default dicts
	if isinstance(d, defaultdict):
		d = {k: default_dict_to_regular(v) for k, v in d.items()}
	return d

def sumDicts(listToProcess):
	# Takes a list of dicts and sums the values by each key, returning a single dict, works with nested dicts too
	nested = lambda: defaultdict(nested)
	d = nested()
	for subd in listToProcess:
		combineIntoDefaultDict(d, subd)
	return default_dict_to_regular(d)

def summaryFinancialsForPurchase(paymentsAndOrders, locationID, db_session, headers):
    # Return financial statistics for a given order
    finStats = {
		'fares': 0,
		'passes': 0,
		'donations': 0,
		'charters': 0,
		'merchandise_taxable': 0,
		'merchandise_nontaxable': 0,
		'uncategorized': 0,
		'memberships': 0,
		'tax_collected': 0,
		'processing_fees':0,
        'online_sales':0,
		'special_events': {},
		'tenders': {}
		}
    special_events = []
    tenders = []
    # get list of line items from the order
    lineItems = getLineItemsFromOrder(paymentsAndOrders['orderID'], db_session, headers)
    if lineItems == -1:
        #No line items in the order (could be a NO SALE for instance)
        return finStats
    else:
        for item in lineItems:
            if locationID == 'LBR2E5T341WDH':
                # Webstore sale, put all in online category
                finStats['online_sales'] += item['total_money']['amount']
            # Custom Amount items have no catalog object id, they should be treated as uncategorized
            elif not 'catalog_object_id' in item:
                if item['item_type'] == 'CUSTOM_AMOUNT':
                    finStats['uncategorized'] += item['total_money']['amount']
            else:
                # get category name for each item
                category = getCategoryForObject(item['catalog_object_id'], item['catalog_version'], db_session, headers)
                if not 'categoryName' in category:
                    finStats['uncategorized'] += item['total_money']['amount']
                elif category['categoryName'] == 'Special Events':
                    special_events.append({item['name']:item['total_money']['amount']})
                elif category['categoryName'] == 'Fares':
                    finStats['fares'] += item['total_money']['amount']
                elif category['categoryName'] == 'Passes':
                    finStats['passes'] += item['total_money']['amount']
                elif category['categoryName'] == 'Donations':
                    finStats['donations'] += item['total_money']['amount']
                elif category['categoryName'] == 'Charters':
                    finStats['charters'] += item['total_money']['amount']
                elif category['categoryName'] == 'Membership':
                    finStats['memberships'] += item['total_money']['amount']
                else:
                    if item['total_tax_money']['amount'] == 0:
                        finStats['merchandise_nontaxable'] += item['total_money']['amount']
                    else:
                        finStats['merchandise_taxable'] += item['total_money']['amount']
            finStats['tax_collected'] += item['total_tax_money']['amount']
        finStats['special_events'] = sumDicts(special_events)
        payment = getPayment(paymentsAndOrders['paymentID'], db_session, headers)
        if payment['source_type'] != 'EXTERNAL':
            tenders.append({payment['source_type']:payment['total_money']['amount']})
        elif payment['external_details']['type'] == 'CHECK':
            tenders.append({'CHECK':payment['total_money']['amount']})
        finStats['tenders'] = sumDicts(tenders)
        if 'processing_fee' in payment:
            #skip if there is no fee line in the payment, eg cash sale
            for fee in payment['processing_fee']:
                finStats['processing_fees'] += 0-fee['amount_money']['amount']
        return finStats

def summaryFinancialsForRefund(refundIDs, locationID, db_session, headers):
    # Return financial statistics for a given refund
    finStats = {
		'fares': 0,
		'passes': 0,
		'donations': 0,
		'charters': 0,
		'merchandise_taxable': 0,
		'merchandise_nontaxable': 0,
		'uncategorized': 0,
		'memberships': 0,
		'tax_collected': 0,
		'processing_fees':0,
        'online_sales':0,
		'special_events': {},
		'tenders': {}
		}
    special_events = []
    tenders = []
    lineItems = getReturnedLineItemsFromOrder(refundIDs['orderID'], db_session, headers)
    for item in lineItems:
        if locationID == 'LBR2E5T341WDH':
                # Webstore sale, put all in online category
                finStats['online_sales'] += 0-item['total_money']['amount']
        elif not 'catalog_object_id' in item:
                if item['item_type'] == 'CUSTOM_AMOUNT':
                    finStats['uncategorized'] += 0-item['total_money']['amount']
        else:
            # get category name for each item
            category = getCategoryForObject(item['catalog_object_id'], item['catalog_version'], db_session, headers)
            if not 'categoryName' in category:
                finStats['uncategorized'] += 0-item['total_money']['amount']
            elif category['categoryName'] == 'Special Events':
                if item['variation_name']:
                    special_events.append({item['variation_name']:0-item['total_money']['amount']})
                else:
                    special_events.append({item['name']:0-item['total_money']['amount']})
            elif category['categoryName'] == 'Fares':
                finStats['fares'] += 0-item['total_money']['amount']
            elif category['categoryName'] == 'Passes':
                finStats['passes'] += 0-item['total_money']['amount']
            elif category['categoryName'] == 'Donations':
                finStats['donations'] += 0-item['total_money']['amount']
            elif category['categoryName'] == 'Charters':
                finStats['charters'] += 0-item['total_money']['amount']
            elif category['categoryName'] == 'Membership':
                finStats['memberships'] += 0-item['total_money']['amount']
            else:
                if item['total_tax_money']['amount'] == 0:
                    finStats['merchandise_nontaxable'] += 0-item['total_money']['amount']
                else:
                    finStats['merchandise_taxable'] += 0-item['total_money']['amount']
        finStats['tax_collected'] += 0-item['total_tax_money']['amount']
    finStats['special_events'] = sumDicts(special_events)
    refund = getRefund(refundIDs['refundID'], db_session, headers) 
    if 'processing_fee' in refund:
        # square used to refund the processing fees too
        for fee in refund['processing_fee']:
            finStats['processing_fees'] += fee['amount_money']['amount']
    tenders.append({refund['destination_type']:0-refund['amount_money']['amount']})
    finStats['tenders'] = sumDicts(tenders)
    return finStats

def generateSummaryStatsForDateRange(beginTime,endTime,locationID,db_session, headers):
    location=getLocationByID(locationID,db_session,headers)
    # Get list of orderIDs in the date range
    paymentsAndOrders = getPaymentsAndOrdersByDateRange(beginTime, endTime, locationID, db_session, headers)
    summaries = []
    for paymentAndOrder in paymentsAndOrders:
	    # get summary statistics for the order
        summaries.append(summaryFinancialsForPurchase(paymentAndOrder, locationID, db_session, headers))
    chargeSummaries = sumDicts(summaries)
    summaries = []
    refunds = getRefundsByDateRange(beginTime, endTime, locationID, db_session, headers)
    for refund in refunds:
        summaries.append(summaryFinancialsForRefund(refund, locationID, db_session, headers))
    refundSummaries = sumDicts(summaries)
    totalSummaries = sumDicts([chargeSummaries,refundSummaries])
    try:
        reportInDB = db_session.query(DailyReport).filter(DailyReport.reportStartDate==beginTime, DailyReport.reportEndDate==endTime, DailyReport.location_id==locationID).one()
        # Yes, it's already in the DB so we should update the DB with the passed report data
        reportInDB.data = totalSummaries
        reportInDB.location_id = locationID
        reportInDB.location_name = location['name']
        reportInDB.reportCreationDate = datetime.now(timezone.utc)
        reportInDB.reportStartDate = beginTime
        reportInDB.reportEndDate = endTime
        db_session.commit()
    except NoResultFound:
        # The daily report is not in the database yet, add the passed report dict to the database if it's not empty
        if totalSummaries:
            db_report = DailyReport(data=totalSummaries,location_id=locationID,location_name=location['name'],reportCreationDate=datetime.now(timezone.utc),reportStartDate=beginTime,reportEndDate=endTime)
            db_session.add(db_report)
            db_session.commit()
    except MultipleResultsFound:
        raise Exception('Multiple Daily Reports Found in Database with same location and start/end date')
    return totalSummaries

def generateReportDataForDates(beginDate,endDate, locationID,db_session, headers):
    UTC_tzone = tz.gettz('UTC')
    LOCAL_tzone = tz.gettz(msmSquareConfig['localTimezone'])
    deltaDays = endDate-beginDate
    for i in range(deltaDays.days + 1):
        date = beginDate + timedelta(days=i)
        newDayTime = time(3,0,0,tzinfo=LOCAL_tzone)
        beginTime=datetime.combine(date, newDayTime)
        spelledDate = beginTime.astimezone(LOCAL_tzone).strftime('%A %B %-d, %Y')
        beginTimeTZ = beginTime.astimezone(LOCAL_tzone)
        endTime=beginTime+timedelta(days=1)
        endTimeTZ = endTime.astimezone(LOCAL_tzone)
        endTime=endTime.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
        beginTime=beginTime.astimezone(UTC_tzone).strftime('%Y-%m-%dT%H:%M:%SZ')
        logging.info('Generating Report for: %s for Location %s', spelledDate, locationID)
        generateSummaryStatsForDateRange(beginTime,endTime,locationID,db_session, headers)
    return

def getReportDataForDatesFromDBAllLocations(beginDate,endDate, db_session, headers):
    UTC_tzone = tz.gettz('UTC')
    LOCAL_tzone = tz.gettz(msmSquareConfig['localTimezone'])
    reportData = []
    newDayTime = time(3,0,0,tzinfo=LOCAL_tzone)
    beginTime = datetime.combine(beginDate, newDayTime)
    beginTimeTZ = beginTime.astimezone(LOCAL_tzone)
    endTime = datetime.combine(endDate, newDayTime)
    endTimeTZ = endTime.astimezone(LOCAL_tzone)
    reportsInDB = db_session.query(DailyReport).filter(DailyReport.reportStartDate.between(beginTimeTZ,endTimeTZ)).order_by(DailyReport.location_name,DailyReport.reportStartDate).all()
    for report in reportsInDB:
        spelledDate = report.reportStartDate.strftime('%A %B %-d, %Y')
        reportData.append({'location':report.location_name, 'date': spelledDate, 'created': report.reportCreationDate, 'data': report.data})
    return reportData