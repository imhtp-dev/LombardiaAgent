import requests
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
#from auth import get_token


def get_token():
    url = 'https://cerbahc.auth.eu-central-1.amazoncognito.com/oauth2/token'
    client_id = '732bjl1ih32jdk3qjcq7dej1tp'
    client_secret = 'c8vst12at03p7d197648h1apktkuv61f8d83qtg3jdbh0nntf8'
    payload = {
    "client_id": client_id,
    "client_secret": client_secret,
    "grant_type": "client_credentials",  
    "scope": "voila/api"
}
    headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}

    response = requests.post(url, data=payload, headers=headers)
    
    token=""
    if response.status_code == 200:
        token = response.json()['access_token']
    else:
        print(f'Error while requesting: {response.status_code} - {response.text}')
    return token




def list_slot(health_center_uuid, date_search, uuid_exam, gender='m', date_of_birth='1980-04-13', start_time=None, end_time=None):
    token = get_token()
    ambiente="prod"
    api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/{ambiente}/amb/health-center/{health_center_uuid}/slot'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }



    request_data = {
        'gender': "m",
        'date_of_birth': "1990-08-11",
        'health_services': uuid_exam,
        'start_date': date_search, # Date of appointment
        'start_time': start_time, # 2025-09-12 09:00:00+00
        'end_time': end_time, # 2025-09-12 10:00:00+00
        'availabilities_limit': 3                   
    }

    response = requests.get(api_url, headers=headers, params=request_data)
    if response.status_code == 200:
        slots = response.json()
        print(f'Slots: {slots}')
        return slots  # Return the slots data
    else:
        print(f'Error during request: {response.status_code} - {response.text}')
        return []  # Return empty list on error


def create_slot(start_slot,end_slot,pea):
    rome_tz = ZoneInfo('Europe/Rome')
    start_slot= datetime.strptime(start_slot, '%Y-%m-%d %H:%M:%S').replace(tzinfo=rome_tz).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    end_slot= datetime.strptime(end_slot, '%Y-%m-%d %H:%M:%S').replace(tzinfo=rome_tz).astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    ambiente="prod"

    token = get_token()
    
    api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/{ambiente}/amb/slot'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    
    request_data = {
        'start_time':start_slot,
        'end_time':end_slot,
        'providing_entity_availability':pea # unique identifier of the availability
    }
    response = requests.post(api_url, headers=headers, json=request_data)
    uuid_slot=""
    crea_at=""
    if response.status_code == 200:
        data = response.json()
        #print(data)
        uuid_slot = data.get('uuid', '')
        crea_at = data.get('created_at', '')
    return response.status_code,uuid_slot,crea_at


def delete_slot(slot_uuid):
    token = get_token()
    ambiente="prod"
    api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/{ambiente}/amb/slot/{slot_uuid}'

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    }
    response = requests.delete(api_url, headers=headers)
    uuid_slot=""
    upd_at=""
    return response

#print(list_slot("c48ff93f-1c88-4621-9cd5-31ad87e83e48","2025-09-19","9a93d65f-396a-45e4-9284-94481bdd2b51"))
print(create_slot('2025-09-19 09:45:00','2025-09-19 09:50:00',"81bc7563-ac82-4f90-8bda-e2143c9d15c4"))