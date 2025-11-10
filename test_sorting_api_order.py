#!/usr/bin/env python3
"""
Test sorting API with RX Caviglia Destra to verify response order
"""

import asyncio
import aiohttp
import json
import requests


def get_token():
    """Get authentication token"""
    url = 'https://cerbahc.auth.eu-central-1.amazoncognito.com/oauth2/token'
    client_id = '732bjl1ih32jdk3qjcq7dej1tp'
    client_secret = 'c8vst12at03p7d197648h1apktkuv61f8d83qtg3jdbh0nntf8'

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "voila/api"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = requests.post(url, data=payload, headers=headers, timeout=10)
    return response.json()['access_token'] if response.status_code == 200 else None


async def test_sorting_api():
    """Test sorting API with RX Caviglia Destra"""
    health_center_uuid = "eec95682-3851-4894-b605-91130f30821d"
    rx_caviglia_uuid = "9a93d65f-396a-45e4-9284-94481bdd2b51"

    print(f"\n🧪 Testing Sorting API - RX Caviglia Destra")
    print(f"=" * 80)

    token = get_token()
    if not token:
        print("❌ Failed to get token")
        return

    api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/prod/amb/sort/health-center/{health_center_uuid}/health-service'

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    
    params = {
        'gender': 'f',
        'date_of_birth': '20010427',
        'health_services': "d9eb5830-3c36-4aa1-b0f5-20445ef2e825",
        'prescriptions': '',
        'preliminary_visits': '',
        'optionals': '8663256e-7f01-4cf3-92ea-2fd7b4756e69',
        'opinions': ''
    }

    print(f"📡 Requesting: RX Caviglia Destra (UUID: {rx_caviglia_uuid})")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                print(f"\n{'=' * 80}")
                print(f"📄 SORTING API RAW RESPONSE:")
                print(f"{'=' * 80}")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print(f"{'=' * 80}")

                # Analyze structure
                if data and isinstance(data, list):
                    print(f"\n🔍 ANALYSIS:")
                    print(f"   Number of groups: {len(data)}")

                    for group_idx, group in enumerate(data):
                        print(f"\n   Group {group_idx}:")
                        print(f"      'group' field value: {group.get('group')}")
                        
                        services = group.get('health_services', [])
                        print(f"      Services ({len(services)}):")
                        
                        for svc_idx, svc in enumerate(services):
                            print(f"         [{svc_idx}] {svc.get('name')}")
                            print(f"             UUID: {svc.get('uuid')}")

                    # Check if package detected
                    first_group = data[0] if data else {}
                    first_services = first_group.get('health_services', [])
                    
                    if first_services:
                        first_uuid = first_services[0].get('uuid')
                        print(f"\n{'=' * 80}")
                        print(f"🎯 RESULT:")
                        print(f"   Requested: RX Caviglia Destra ({rx_caviglia_uuid})")
                        print(f"   First in response: {first_services[0].get('name')} ({first_uuid})")
                        
                        if first_uuid == rx_caviglia_uuid:
                            print(f"   ✅ ORDER PRESERVED - No package replacement")
                        else:
                            print(f"   ⚠️ PACKAGE DETECTED - API reordered/replaced services!")
                        print(f"{'=' * 80}")

asyncio.run(test_sorting_api())
