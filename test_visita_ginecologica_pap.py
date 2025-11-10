#!/usr/bin/env python3
"""
Test sorting API with Visita Ginecologica + Pap Test
Using EXACT parameters from chat agent log file: 20251110_235307_chat-tes_text_chat_test.log
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


async def test_visita_ginecologica_pap():
    """Test sorting API with Visita Ginecologica + Pap Test - EXACT params from chat agent"""

    # EXACT parameters from chat agent log (20251110_235307_chat-tes_text_chat_test.log)
    health_center_uuid = "eec95682-3851-4894-b605-91130f30821d"  # Milano Via Emilio de Marchi 4
    visita_ginecologica_uuid = "d9eb5830-3c36-4aa1-b0f5-20445ef2e825"
    pap_test_uuid = "8663256e-7f01-4cf3-92ea-2fd7b4756e69"

    print(f"\n🧪 Testing Sorting API - Visita Ginecologica + Pap Test")
    print(f"=" * 80)
    print(f"📍 Health Center: Milano Via Emilio de Marchi 4 - Biochimico")
    print(f"   UUID: {health_center_uuid}")
    print(f"\n📋 Services:")
    print(f"   1. Visita Ginecologica (Prima Visita): {visita_ginecologica_uuid}")
    print(f"   2. Pap Test: {pap_test_uuid}")

    token = get_token()
    if not token:
        print("❌ Failed to get token")
        return

    api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/prod/amb/sort/health-center/{health_center_uuid}/health-service'

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

    # EXACT parameters from chat agent log
    params = {
        'gender': 'm',                                          # Male
        'date_of_birth': '20070427',                           # 2007-04-27
        'health_services': visita_ginecologica_uuid,           # Visita Ginecologica
        'prescriptions': '',
        'preliminary_visits': '',
        'optionals': pap_test_uuid,                            # Pap Test
        'opinions': ''
    }

    print(f"\n📡 API Request Parameters:")
    print(f"   gender: {params['gender']}")
    print(f"   date_of_birth: {params['date_of_birth']}")
    print(f"   health_services: {params['health_services']}")
    print(f"   optionals: {params['optionals']}")

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
                            print(f"             Code: {svc.get('code', 'N/A')}")

                    # Check if package detected
                    requested_uuids = {visita_ginecologica_uuid, pap_test_uuid}
                    response_uuids = set()

                    for group in data:
                        for svc in group.get('health_services', []):
                            response_uuids.add(svc.get('uuid'))

                    print(f"\n{'=' * 80}")
                    print(f"🎯 PACKAGE DETECTION ANALYSIS:")
                    print(f"   Requested UUIDs ({len(requested_uuids)}): {requested_uuids}")
                    print(f"   Response UUIDs ({len(response_uuids)}): {response_uuids}")

                    if requested_uuids == response_uuids:
                        print(f"   ✅ NO PACKAGE - API returned exactly what was requested")
                        print(f"      Services are separate, group field indicates bundling status")
                    else:
                        missing = requested_uuids - response_uuids
                        additional = response_uuids - requested_uuids
                        print(f"   🎁 PACKAGE DETECTED!")
                        if missing:
                            print(f"      Missing from response: {missing}")
                        if additional:
                            print(f"      Additional in response: {additional}")
                        print(f"      → API replaced services with combined package")

                    print(f"{'=' * 80}")
            else:
                print(f"❌ API Error: {response.status}")
                print(f"Response: {await response.text()}")


if __name__ == "__main__":
    asyncio.run(test_visita_ginecologica_pap())
