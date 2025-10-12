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
        'gender': gender,
        'date_of_birth': date_of_birth,
        'health_services': uuid_exam,
        'start_date': date_search, # Date of appointment
        'start_time': start_time, # 2025-09-12 09:00:00+00
        'end_time': end_time, # 2025-09-12 10:00:00+00
        'availabilities_limit': 3                   
    }

    print(f'🔍 SLOT FETCH DEBUG: Making API request to: {api_url}')
    print(f'🔍 SLOT FETCH DEBUG: Request params: {request_data}')

    response = requests.get(api_url, headers=headers, params=request_data)

    print(f'🔍 SLOT FETCH DEBUG: Response status: {response.status_code}')

    if response.status_code == 200:
        slots = response.json()
        print(f'🔍 SLOT FETCH DEBUG: ===== FULL API RESPONSE =====')
        print(f'🔍 SLOT FETCH DEBUG: Raw response: {slots}')
        print(f'🔍 SLOT FETCH DEBUG: Response type: {type(slots)}')

        if isinstance(slots, list):
            print(f'🔍 SLOT FETCH DEBUG: Number of slots returned: {len(slots)}')
            for i, slot in enumerate(slots):
                print(f'🔍 SLOT FETCH DEBUG: --- SLOT {i+1} ---')
                print(f'🔍 SLOT FETCH DEBUG: Full slot data: {slot}')
                print(f'🔍 SLOT FETCH DEBUG: start_time: {slot.get("start_time", "MISSING")}')
                print(f'🔍 SLOT FETCH DEBUG: end_time: {slot.get("end_time", "MISSING")}')
                print(f'🔍 SLOT FETCH DEBUG: providing_entity_availability_uuid: {slot.get("providing_entity_availability_uuid", "MISSING")}')
                print(f'🔍 SLOT FETCH DEBUG: health_services: {slot.get("health_services", "MISSING")}')
                if i >= 2:  # Limit to first 3 slots to avoid log spam
                    print(f'🔍 SLOT FETCH DEBUG: ... ({len(slots) - i - 1} more slots not shown)')
                    break
        else:
            print(f'🔍 SLOT FETCH DEBUG: Response is not a list: {slots}')

        print(f'🔍 SLOT FETCH DEBUG: ===== END RESPONSE =====')
        return slots  # Return the slots data
    else:
        print(f'🔍 SLOT FETCH DEBUG: ❌ API Error: {response.status_code} - {response.text}')
        return []  # Return empty list on error


def create_slot(start_slot,end_slot,pea):
    # Use slot times as-is (no timezone conversion needed)
    # Input format: 2025-10-27 11:25:00
    # API expects: 2025-10-27 11:25:00 (same format)
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


#print(list_slot("c48ff93f-1c88-4621-9cd5-31ad87e83e48","2025-10-24","9a93d65f-396a-45e4-9284-94481bdd2b51"))
#print(create_slot('2025-10-08 15:15:00','2025-10-08 15:25:00',"d1bbc9cd-e7e8-4e1e-8075-b637824504a6"))
#print(create_slot('2025-10-27 11:25:00','2025-10-27 11:30:00',"d1bbc9cd-e7e8-4e1e-8075-b637824504a6"))