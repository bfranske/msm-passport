#!/usr/bin/python3
import requests
import uuid
import json
from datetime import datetime, timedelta
import yaml
from pprint import pprint

# Load configuration
try:
    with open("config-msmcharters.yaml", 'r') as stream:
        try:
            charterConfig=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
except IOError:
    print("Could not read config-msmcharters.yaml file")

charter_catalog_object_id=charterConfig['charterObjectID']
application_id=charterConfig['applicationID']
accessToken=charterConfig['accessToken']
headers = {"Authorization":"Bearer "+ accessToken, 'Square-Version':charterConfig['squareApiVersion'], 'Content-Type':'application/json'}
baseURL = charterConfig['squareBaseURL']
invoiceDescription = charterConfig['invoiceNote']

def getCharterLocations():
    return charterConfig['locations']

def processCharterInvoiceForm(form):
    fname = form['fname']
    lname = form['lname']
    cname = form['cname']
    email = form['email']
    charter_location = form['charter_location']
    charter_location_id = charterConfig['locations'][charter_location]
    charter_date = str(form['charter_date'])
    charter_date_dt = datetime.strptime(charter_date, "%Y-%m-%d")
    charter_date_us = charter_date_dt.strftime("%m/%d/%y")
    #print("Charter Date: "+charter_date)
    start_time = form['start_time']
    start_time_dt = datetime.combine(charter_date_dt,datetime.strptime(start_time,"%H:%M").time())
    start_time_12 = start_time_dt.strftime("%-I:%M%p")
    end_time = form['end_time']
    end_time_dt = datetime.combine(charter_date_dt,datetime.strptime(end_time,"%H:%M").time())
    end_time_12 = end_time_dt.strftime("%-I:%M%p")
    chargeCents = int(float(form['charge'])*100)
    due_date_dt = charter_date_dt - timedelta(days=7)
    if due_date_dt < datetime.now() + timedelta(days=1):
        due_date_dt = datetime.now() + timedelta(days=1)
    due_date = due_date_dt.strftime("%Y-%m-%d")
    due_date_us = due_date_dt.strftime("%m/%d/%y")
    note = charter_date_us+" Charter at "+charter_location+", "+start_time_12+"-"+end_time_12
    title = charter_date_us+" Charter at "+charter_location
    #print("Due Date: "+due_date)
    #print(chargeCents)
    invoiceCreated = sendInvoice(given_name=fname,family_name=lname,company_name=cname,email_address=email,location_id=charter_location_id,note=note,charterAmount=chargeCents,title=title,invoiceDate=charter_date,dueDate=due_date)
    result = {'fname':fname, 'lname':lname, 'cname':cname, 'email':email, 'charter_location':charter_location, 'charter_date':charter_date, 'start_time':start_time, 'end_time':end_time, 'charge':"{:.2f}".format(chargeCents/100), 'invoiceID':invoiceCreated['invoice']['id'], 'invoiceNumber':invoiceCreated['invoice']['invoice_number']}
    return result

def sendInvoice(given_name,family_name,email_address,location_id,note,charterAmount,title,invoiceDate,dueDate,company_name=""):
    customerID = createCustomerRecord(given_name,family_name,email_address,company_name)
    print('Customer ID: ',customerID)
    orderID = createCharterOrder(location_id,note,charterAmount)
    print('Order ID: ',orderID)
    invoice = createCharterInvoice(title,invoiceDescription,invoiceDate,dueDate,orderID,customerID)
    print('Invoice ID: ',invoice['invoice']['id'])
    invoice = publishInvoice(invoice)
    return invoice

def createCharterOrder(location_id,note,charterAmount):
    # Create Order
    url = baseURL+'/v2/orders'
    payload = {}
    payload['idempotency_key'] = str(uuid.uuid4())
    payload['order'] = {}
    payload['order']['location_id'] = location_id
    payload['order']['line_items'] = [{}]
    payload['order']['line_items'][0]['quantity'] = '1'
    payload['order']['line_items'][0]['catalog_object_id'] = charter_catalog_object_id
    payload['order']['line_items'][0]['note'] = note
    payload['order']['line_items'][0]['base_price_money'] = {}
    payload['order']['line_items'][0]['base_price_money']['amount'] = charterAmount
    payload['order']['line_items'][0]['base_price_money']['currency'] = 'USD'
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    response = r.json()
    orderID = response['order']['id']
    return orderID

def createCharterInvoice(title,description,invoiceDate,dueDate,orderID,customerID):
    url = baseURL+'/v2/invoices'
    payload = {}
    payload['idempotency_key'] = str(uuid.uuid4())
    payload['invoice'] = {}
    payload['invoice']['order_id'] = orderID
    payload['invoice']['title'] = title
    payload['invoice']['description'] = description
    payload['invoice']['sale_or_service_date'] = invoiceDate
    payload['invoice']['primary_recipient'] = {}
    payload['invoice']['primary_recipient']['customer_id'] = customerID
    payload['invoice']['delivery_method'] = "EMAIL"
    payload['invoice']['payment_requests'] = [{}]
    payload['invoice']['payment_requests'][0]['request_type'] = "BALANCE"
    payload['invoice']['payment_requests'][0]['due_date'] = dueDate
    payload['invoice']['payment_requests'][0]['reminders'] = [{},{},{},{}]
    payload['invoice']['payment_requests'][0]['reminders'][0]['relative_scheduled_days'] = -7
    payload['invoice']['payment_requests'][0]['reminders'][1]['relative_scheduled_days'] = 0
    payload['invoice']['payment_requests'][0]['reminders'][2]['relative_scheduled_days'] = 1
    payload['invoice']['payment_requests'][0]['reminders'][3]['relative_scheduled_days'] = 3
    payload['invoice']['accepted_payment_methods'] = {}
    payload['invoice']['accepted_payment_methods']['card'] = True
    payload['invoice']['accepted_payment_methods']['square_gift_card'] = False
    payload['invoice']['accepted_payment_methods']['bank_account'] = True
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    response = r.json()
    pprint(response)
    invoice = response
    return invoice
    
def publishInvoice(invoice):
    invoiceID=invoice['invoice']['id']
    url = baseURL+'/v2/invoices/'+invoiceID+'/publish'
    payload = {}
    payload['idempotency_key'] = str(uuid.uuid4())
    payload['version'] = invoice['invoice']['version']
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    response = r.json()
    invoice = response
    return invoice

def createCustomerRecord(given_name,family_name,email_address,company_name=""):
    #check to see if there is an existing customer with that email address
    url = baseURL+'/v2/customers/search'
    payload = {}
    payload['query'] = {}
    payload['query']['filter'] = {}
    payload['query']['filter']['email_address'] = {}
    payload['query']['filter']['email_address']['exact'] = email_address
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    response = r.json()
    if 'customers' in response:
        return response['customers'][0]['id']
    else:
        url = baseURL+'/v2/customers'
        payload = {}
        payload['idempotency_key'] = str(uuid.uuid4())
        payload['given_name'] = given_name
        payload['family_name'] = family_name
        payload['company_name'] = company_name
        payload['email_address'] = email_address
        r = requests.post(url, headers=headers, data=json.dumps(payload))
        response = r.json()
        customerID = response['customer']['id']
        return customerID

#print(createCharterOrder())
#print(createCustomerRecord())
#print(createCharterInvoice("6qgexSjJDGFUCIebcAgSWUOYOcTZY","6J2PNTCMPRTPB3C914EX4WVBQ8"))
#myInvoice = {'invoice' : {'id' : 'inv:0-ChBOUFcEgtxi6aQQMoaKdnsVEPYN', 'version': 0}}
#print(publishInvoice(myInvoice))
#print(publishInvoice(createCharterInvoice(createCharterOrder(),"6J2PNTCMPRTPB3C914EX4WVBQ8")))

#pprint(sendInvoice(given_name="Ben",family_name="Franske",company_name="",email_address="ben.mm@franske.com",location_id="LFEP2YQQYFHPT",note="05/01/22 charter at CHSL, 10:00-11:00 note",charterAmount=8500,title="05/01/22 Charter at CHSL title",charterDate="2022-05-01",dueDate="2022-04-24"))