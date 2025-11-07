#!/usr/bin/env python3
"""
Test script for health center selection API
Tests the health-service API with specified parameters
"""

import asyncio
import aiohttp
import json
import requests


def get_token():
    """Get authentication token from Cerba Healthcare API"""
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

    try:
        print(f"🔐 Requesting authentication token...")
        response = requests.post(url, data=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            token = response.json()['access_token']
            print(f"✅ Token acquired successfully")
            return token
        else:
            print(f'❌ Token request failed: {response.status_code} - {response.text}')
            return None

    except Exception as e:
        print(f"❌ Token request error: {e}")
        return None


async def test_health_center_api():
    """
    Test the health center selection API with specified parameters
    """
    # Parameters from your request
    health_center_uuid = "c5535638-6c18-444c-955d-89139d8276be"
    selected_service_uuid = "9a93d65f-396a-45e4-9284-94481bdd2b51"
    additional_services_uuid = "ea65a7bf-58e4-4ac0-9041-61a5088cefb6"

    print(f"\n🧪 Testing Health Center Selection API")
    print(f"=" * 80)
    print(f"📋 Parameters:")
    print(f"   Health Center UUID: {health_center_uuid}")
    print(f"   Selected Service UUID: {selected_service_uuid}")
    print(f"   Additional Services UUID: {additional_services_uuid}")

    try:
        # Get authentication token
        token = get_token()
        if not token:
            print("❌ Failed to get authentication token")
            return

        # Prepare API request
        ambiente = "prod"  # or "test" depending on environment
        api_url = f'https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/{ambiente}/amb/sort/health-center/{health_center_uuid}/health-service'

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        request_data = {
            'gender': 'm',
            'date_of_birth': '1980-04-13',
            'health_services': selected_service_uuid,
            'prescriptions': '',
            'preliminary_visits': '',
            'optionals': additional_services_uuid,
            'opinions': ''
        }

        print(f"\n📡 API Request Details:")
        print(f"   URL: {api_url}")
        print(f"   Method: GET")
        print(f"\n📊 Request Parameters:")
        print(f"   gender: {request_data['gender']}")
        print(f"   date_of_birth: {request_data['date_of_birth']}")
        print(f"   health_services: {request_data['health_services']}")
        print(f"   prescriptions: {request_data['prescriptions']}")
        print(f"   preliminary_visits: {request_data['preliminary_visits']}")
        print(f"   optionals: {request_data['optionals']}")
        print(f"   opinions: {request_data['opinions']}")

        # Make the API request
        print(f"\n⏳ Making API request...")
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers, params=request_data) as response:
                status = response.status
                print(f"\n📊 Response Status: {status}")

                if status == 200:
                    data = await response.json()
                    print(f"✅ API call successful!")

                    # Print full response
                    print(f"\n📄 FULL API RESPONSE:")
                    print("=" * 80)
                    print(json.dumps(data, indent=2, ensure_ascii=False))
                    print("=" * 80)

                    # Save to file
                    output_filename = f"health_center_response_{health_center_uuid}.json"
                    with open(output_filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    print(f"\n💾 Response saved to: {output_filename}")

                    # Analyze response
                    if data and isinstance(data, list) and len(data) > 0:
                        print(f"\n🔍 Response Analysis:")
                        print(f"   Number of results: {len(data)}")

                        first_result = data[0]
                        print(f"   Health Center: {first_result.get('health_center', {}).get('name', 'N/A')}")

                        health_services = first_result.get('health_services', [])
                        print(f"   Number of services: {len(health_services)}")

                        if health_services:
                            print(f"\n   📋 Services:")
                            for idx, service in enumerate(health_services, 1):
                                service_name = service.get('name', 'N/A')
                                service_uuid = service.get('uuid', 'N/A')
                                print(f"      {idx}. {service_name}")
                                print(f"         UUID: {service_uuid}")

                else:
                    print(f"❌ API call failed!")
                    response_text = await response.text()
                    print(f"   Response: {response_text}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point"""
    print(f"🏥 Health Center API Tester")
    print(f"=" * 80)

    # Run the async test
    asyncio.run(test_health_center_api())

    print(f"\n✅ Test completed!")


if __name__ == "__main__":
    main()
