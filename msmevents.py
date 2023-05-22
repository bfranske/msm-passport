#!/usr/bin/python3
import requests
import json
import yaml
import logging

log = logging.getLogger(__name__)

# Load configuration
try:
    with open("config-msmevents.yaml", 'r') as stream:
        try:
            eventsConfig=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
except IOError:
    print("Could not read config-msmevents.yaml file")

#eventsConfig['wcConsumerKey']
#eventsConfig['wcConsumerSecret']
#eventsConfig['wcBaseURL']
#eventsConfig['wcCategoryID']

def getEventList():
    r = requests.get(eventsConfig['wcBaseURL']+'products?category='+str(eventsConfig['wcCategoryID'])+'per_page=100&orderby=date', auth=(eventsConfig['wcConsumerKey'], eventsConfig['wcConsumerSecret']))
    events = r.json()
    return events

def getURLs():
    urls={'appBaseURL': eventsConfig['appBaseURL']}
    return urls

def getVariations(form):
    eventID = form['eventID']
    r = requests.get(eventsConfig['wcBaseURL']+'products/'+str(eventID)+'/variations?per_page=100', auth=(eventsConfig['wcConsumerKey'], eventsConfig['wcConsumerSecret']))
    variations = r.json()
    return variations

def processEventCustomersForm(form):
    #Right now only works for up to 200 people, needs recursion for more.
    eventID = int(form['eventID'])
    variationID = int(form['variationID'])
    r = requests.get(eventsConfig['wcBaseURL']+'orders?product='+str(eventID)+'&per_page=100', auth=(eventsConfig['wcConsumerKey'], eventsConfig['wcConsumerSecret']))
    orders = r.json()
    totalTicketsSold=0
    customers = []
    for order in orders:
        log.info('Order: '+str(order))
        if variationID:
            for item in order['line_items']:
                if item['id'] == eventID and item['variation_id'] == variationID:
                    customer = {'firstName': order['shipping']['first_name'], 'lastName': order['shipping']['last_name'], 'email': order['billing']['email'], 'qty': item['quantity']}
                    customers.append(customer)
        else:
            for item in order['line_items']:
                if item['id'] == eventID:
                    customer = {'firstName': order['shipping']['first_name'], 'lastName': order['shipping']['last_name'], 'email': order['billing']['email'], 'qty': item['quantity']}
                    customers.append(customer)
    # If there are more than 100 people...
    if r.links.get('next'):
        r = requests.get(response.links['next']['url'], auth=(eventsConfig['wcConsumerKey'], eventsConfig['wcConsumerSecret']))
        orders = r.json()
        for order in orders:
            if variationID:
                for item in order['line_items']:
                    if item['id'] == eventID and item['variation_id'] == variationID:
                        customer = {'firstName': order['shipping']['first_name'], 'lastName': order['shipping']['last_name'], 'email': order['billing']['email'], 'qty': item['quantity']}
                        customers.append(customer)
            else:
                for item in order['line_items']:
                    if item['id'] == eventID:
                        customer = {'firstName': order['shipping']['first_name'], 'lastName': order['shipping']['last_name'], 'email': order['billing']['email'], 'qty': item['quantity']}
                        customers.append(customer)
    eventDetails = {'eventID': eventID, 'eventName': form['eventName'], 'variationID': variationID, 'variationName': form['variationName'], 'totalTicketsSold': totalTicketsSold}
    data = {'eventDetails': eventDetails, 'customers': customers}
    return data
