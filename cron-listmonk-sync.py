#! /usr/bin/python3
import logging
import yaml
import requests
from pprint import pprint
import json

def main():
    #Sync member email addresses to the Liskmonk all members email list

    logging.basicConfig(level=logging.INFO)
    
    # Load membership configuration
    try:
        with open("config-msmmembership.yaml", 'r') as stream:
            try:
                msmMembershipConfig=yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
    except IOError:
        print("Could not read config-msmmembership.yaml file")
    
    # Load listmonk configuration
    try:
        with open("config-listmonk.yaml", 'r') as stream:
            try:
                msmListmonkConfig=yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
    except IOError:
        print("Could not read config-listmonk.yaml file")
    
    listmonkBaseURL = msmListmonkConfig['listmonkBaseURL']
    listmonkUser = msmListmonkConfig['listmonkUser']
    listmonkPassword = msmListmonkConfig['listmonkPassword']
    allMSMmembersListID = 3

    civiCRMurl = msmMembershipConfig['apiV4BaseUrl']+'Membership/get'
    civiCRMkey = msmMembershipConfig['apiKey']
    civiCRMheaders = {
        'X-Civi-Auth': 'Bearer '+civiCRMkey
        }

    # Can either set limit to 0 and get all records OR set a limit and then keep querying, increasing the offset each time by the limit amount until the countFetched value returned is less than the limit

    payload = {
            'select': ['*', 'email.email', 'contact.contact_type', 'contact.display_name', 'contact.first_name', 'contact.last_name', 'contact.do_not_email', 'contact.is_opt_out'],
            'join': [['Contact AS contact', 'LEFT', ['contact.id', '=', 'contact_id']], ['Email AS email', 'LEFT', ['email.contact_id', '=', 'contact_id']]],
            'where': [['email.is_primary', '=', True], ['contact.contact_type', '=', 'Individual'], ['status_id', '<=', 3], ['contact.is_deceased', '=', False], ['contact.is_deleted', '=', False], ['contact.do_not_email', '=', False], ['contact.is_opt_out', '=', False]],
            'limit': 0,
            'offset': 0
        }

    # This is stupid. CiviCRM requires the payload data be a json string in a params= all then sent as urlencoded form data

    encoded = {
        'params': json.dumps(payload)
    }

    r = requests.post(civiCRMurl, headers=civiCRMheaders, data=encoded)

    #print(r.status_code)

    civiCRMresponseData = r.json()

    #pprint (civiCRMresponseData)

    params = {'per_page' : 'all'}
    r = requests.get(listmonkBaseURL+'/subscribers', params=params, auth=(listmonkUser,listmonkPassword))
    listmonkResponseData = r.json()
    #pprint (listmonkResponseData)

    #For each member in CiviCRM
    for member in civiCRMresponseData['values']:
        #Search Liskmonk to see if they exist
        existingSubscriber = 0
        for subscriber in listmonkResponseData['data']['results']:
            # Check using their CiviCRM contact ID first
            if 'civiCRMcontactID' in subscriber['attribs'] and subscriber['attribs']['civiCRMcontactID'] == member['contact_id']:
                existingSubscriber = 1
                #See if they are a member of the All MSM Members list (they are confirmed, unconfirmed, or have unsubscribed)
                alreadyListMember = 0
                for emailList in subscriber['lists']:
                    if emailList['id'] == allMSMmembersListID and emailList['subscription_status'] in ('unconfirmed', 'confirmed', 'unsubscribed'):
                        alreadyListMember = 1
                if alreadyListMember == 0:
                    # Add the existing subscriber to the All MSM Members list
                    data = {'ids' : [subscriber['id']], 'action': 'add', 'target_list_ids' : [allMSMmembersListID], 'status' : 'unconfirmed'}
                    r = requests.put(listmonkBaseURL+'/subscribers/lists', json=data, auth=(listmonkUser,listmonkPassword))
                # Check to see if name or email should be updated and do the update on Listmonk
                if not subscriber['name'] == member['contact.display_name'] or not subscriber['email'] == member['email.email']:
                    #Get current subscriber record from Listmonk
                    r = requests.get(listmonkBaseURL+'/subscribers/'+str(subscriber['id']), auth=(listmonkUser,listmonkPassword))
                    response = r.json()
                    oldSubscriberData = response['data']
                    oldLists = []
                    for oldList in oldSubscriberData['lists']:
                        oldLists.append(oldList['id'])
                    #Push new name and email to Listmonk, have to resend all old data that should stay the same
                    data = {'email' : member['email.email'], 'name' : member['contact.display_name'], 'status' : oldSubscriberData['status'], 'lists' : oldLists, 'attribs' : oldSubscriberData['attribs']}
                    r = requests.put(listmonkBaseURL+'/subscribers/'+str(subscriber['id']), json=data, auth=(listmonkUser,listmonkPassword))
                # Since we found someone by contact ID we can skip looking for them by email and stop searching subscribers
                break
            # Check using their email address second (see if their email is already a subscriber but they don't have contact ID data)
            elif subscriber['email'] == member['email.email']:
                existingSubscriber = 1
                #If so, proceed with checking if they are a list member, adding to the list if needed, updating name, etc. as above but also push out their contact ID
                alreadyListMember = 0
                for emailList in subscriber['lists']:
                    if emailList['id'] == allMSMmembersListID and emailList['subscription_status'] in ('unconfirmed', 'confirmed', 'unsubscribed'):
                        alreadyListMember = 1
                if alreadyListMember == 0:
                    # Add the existing subscriber to the All MSM Members list
                    data = {'ids' : [subscriber['id']], 'action': 'add', 'target_list_ids' : [allMSMmembersListID], 'status' : 'unconfirmed'}
                    r = requests.put(listmonkBaseURL+'/subscribers/lists', json=data, auth=(listmonkUser,listmonkPassword))
                #Push name and CiviCRM contact ID to Listmonk, have to resend all old data that should stay the same
                #Get current subscriber record from Listmonk
                r = requests.get(listmonkBaseURL+'/subscribers/'+str(subscriber['id']), auth=(listmonkUser,listmonkPassword))
                response = r.json()
                oldSubscriberData = response['data']
                oldLists = []
                for oldList in oldSubscriberData['lists']:
                    oldLists.append(oldList['id'])
                oldSubscriberData['attribs']['civiCRMcontactID'] = member['contact_id']
                #Push new name and email to Listmonk, have to resend all old data that should stay the same
                data = {'email' : member['email.email'], 'name' : member['contact.display_name'], 'status' : oldSubscriberData['status'], 'lists' : oldLists, 'attribs' : oldSubscriberData['attribs']}
                r = requests.put(listmonkBaseURL+'/subscribers/'+str(subscriber['id']), json=data, auth=(listmonkUser,listmonkPassword))
                # Since we found someone by email we can stop searching the subscriber list
                break
        # Else if not a current subscriber add them as a new subscriber and add to the list with all requisite information
        if existingSubscriber == 0:
            data = {'email' : member['email.email'], 'name' : member['contact.display_name'], 'status' : 'enabled', 'lists' : [allMSMmembersListID], 'attribs' : {'civiCRMcontactID' : member['contact_id']}}
            r = requests.post(listmonkBaseURL+'/subscribers', json=data, auth=(listmonkUser,listmonkPassword))

    #Check to remove any non-current MSM members from All MSM Members email distribution list
    removeIDs = []
    #Get updated Listmonk subscribers for All MSM Members List ONLY
    params = {'list_id' : allMSMmembersListID, 'per_page' : 'all'}
    r = requests.get(listmonkBaseURL+'/subscribers', params=params, auth=(listmonkUser,listmonkPassword))
    listmonkResponseData = r.json()

    #For each member in Listmonk
    for subscriber in listmonkResponseData['data']['results']:
        validMember = 0
        #Seach CiviCRM to see if they exist
        for member in civiCRMresponseData['values']:
            if subscriber['email'] == member['email.email']:
                validMember = 1
                # Stop looking through the member list
                break
        #If Not, remove them from the All MSM Members list (can be a bulk array remove id list)
        if validMember == 0:
            removeIDs.append(subscriber['id'])
    #If the removeIDs list is not empty proceed with the removal
    if len(removeIDs) > 0:
        data = {'ids' : removeIDs, 'action': 'remove', 'target_list_ids' : [allMSMmembersListID]}
        r = requests.put(listmonkBaseURL+'/subscribers/lists', json=data, auth=(listmonkUser,listmonkPassword))

    return

if __name__ == "__main__":
    main()