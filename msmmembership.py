import requests
import json
import yaml
import csv
import io

# Load configuration
try:
    with open("config-msmmembership.yaml", 'r') as stream:
        try:
            msmMembershipDBConfig=yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
except IOError:
    print("Could not read config-msmmembership.yaml file")

def getTCLComplimentaryAddresses():
    headers = {
    'X-Civi-Auth': 'Bearer '+msmMembershipDBConfig['apiKey']
    }
    url = msmMembershipDBConfig['apiV4BaseUrl']+'GroupContact/get'

    # Can either set limit to 0 and get all records OR set a limit and then keep querying, increasing the offset each time by the limit amount until the countFetched value returned is less than the limit

    payload = {
            'select': ['contact_id.addressee_display', 'address.*', 'country.name', 'state_province.name', 'state_province.abbreviation'],
            'join': [['Address AS address', 'LEFT', ['contact_id.address_primary', '=', 'address.id']], ['Country AS country', 'LEFT', ['address.country_id', '=', 'country.id']], ['StateProvince AS state_province', 'LEFT', ['address.state_province_id', '=', 'state_province.id']]],
            'where': [['group_id', '=', 10], ['status', '=', 'Added'], ['contact_id.is_deleted', '=', False], ['contact_id.is_deceased', '=', False], ['contact_id.do_not_mail', '=', False]],
            'limit': 0,
            'offset': 0
        }

    # This is stupid. CiviCRM requires the payload data be a json string in a params= all then sent as urlencoded form data

    encoded = {
        'params': json.dumps(payload)
    }

    r = requests.post(url, headers=headers, data=encoded)

    data = r.json()

    return data['values']

def getTCLMemberAddresses():
    headers = {
    'X-Civi-Auth': 'Bearer '+msmMembershipDBConfig['apiKey']
    }
    url = msmMembershipDBConfig['apiV4BaseUrl']+'Membership/get'

    # Can either set limit to 0 and get all records OR set a limit and then keep querying, increasing the offset each time by the limit amount until the countFetched value returned is less than the limit

    payload = {
        'select': ['*', 'contact.contact_type', 'contact.addressee_display', 'address.*', 'country.name', 'state_province.name', 'state_province.abbreviation'],
        'join': [['Contact AS contact', 'LEFT', ['contact.id', '=', 'contact_id']], ['Address AS address', 'LEFT', ['contact.address_primary', '=', 'address.id']], ['Country AS country', 'LEFT', ['address.country_id', '=', 'country.id']], ['StateProvince AS state_province', 'LEFT', ['address.state_province_id', '=', 'state_province.id']]],
        'where': [['OR', [['AND', [['contact.contact_type', '=', 'Individual'], ['OR', [['membership_type_id', '=', 1], ['membership_type_id', '=', 12], ['membership_type_id', '=', 5], ['membership_type_id', '=', 11]]]]], ['AND', [['contact.contact_type', '=', 'Household'], ['OR', [['membership_type_id', '=', 9], ['membership_type_id', '=', 10]]]]]]], ['status_id', '<=', 3], ['contact.is_deceased', '=', False], ['contact.is_deleted', '=', False], ['contact.do_not_mail', '=', False]],
        'limit': 0,
        }

    # This is stupid. CiviCRM requires the payload data be a json string in a params= all then sent as urlencoded form data

    encoded = {
        'params': json.dumps(payload)
    }

    r = requests.post(url, headers=headers, data=encoded)

    data = r.json()

    return data['values']

def getTCLAllAddressesCSV():

    compCopies = getTCLComplimentaryAddresses()
    memberCopies = getTCLMemberAddresses()

    header = ['Addressee', 'Street Address', 'Supplemental Address 1', 'City', 'State', 'Postal Code', 'Postal Code Suffix', 'Country', 'Supplemental Address 2']

    # Create a file-like string for output
    csvOutput = io.StringIO()

    writer = csv.writer(csvOutput)
    writer.writerow(header)

    for memberAddress in memberCopies:
        addressee = memberAddress['contact.addressee_display']
        streetAddress = memberAddress['address.street_address']
        suppAddress1 = memberAddress['address.supplemental_address_1']
        city = memberAddress['address.city']
        state = memberAddress['state_province.abbreviation']
        postalCode = memberAddress['address.postal_code']
        postalCodeSuffix = memberAddress['address.postal_code_suffix']
        country = memberAddress['country.name']
        suppAddress2 = memberAddress['address.supplemental_address_2']
        #Output to CSV
        writer.writerow([addressee, streetAddress, suppAddress1, city, state, postalCode, postalCodeSuffix, country, suppAddress2])

    for compAddress in compCopies:
        addressee = compAddress['contact_id.addressee_display']
        streetAddress = compAddress['address.street_address']
        suppAddress1 = compAddress['address.supplemental_address_1']
        city = compAddress['address.city']
        state = compAddress['state_province.abbreviation']
        postalCode = compAddress['address.postal_code']
        postalCodeSuffix = compAddress['address.postal_code_suffix']
        country = compAddress['country.name']
        suppAddress2 = compAddress['address.supplemental_address_2']
        #Output to CSV
        writer.writerow([addressee, streetAddress, suppAddress1, city, state, postalCode, postalCodeSuffix, country, suppAddress2])
    
    csvData = csvOutput.getvalue()

    return csvData