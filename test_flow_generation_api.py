#!/usr/bin/env python3
"""
Test script for the Flow Generation API that's experiencing timeout issues.

This script tests the specific API call that's failing in the logs:
- API: https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/prod/amb/health-service/{medical_exam_id}
- Error: HTTPSConnectionPool Read timed out (read timeout=30)

Usage:
    python test_flow_generation_api.py [--timeout SECONDS] [--service-uuid UUID] [--health-centers UUIDs]
"""

import requests
import json
import sys
import argparse
import time
from typing import List, Dict, Any, Optional


class FlowGenerationAPITester:
    """Test the flow generation API with various timeout and retry strategies"""

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.base_url = "https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com"
        self.environment = "prod"

    def get_token(self) -> Optional[str]:
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

    def test_flow_generation_api(
        self,
        medical_exam_id: str,
        health_centers: List[str],
        gender: str = "f",
        date_of_birth: str = "19990106"
    ) -> Dict[str, Any]:
        """
        Test the flow generation API with specified parameters

        Args:
            medical_exam_id: UUID of the medical service
            health_centers: List of health center UUIDs
            gender: Patient gender (m/f)
            date_of_birth: Date in YYYYMMDD format

        Returns:
            Dictionary with test results
        """
        token = self.get_token()
        if not token:
            return {"success": False, "error": "Failed to get authentication token"}

        api_url = f'{self.base_url}/{self.environment}/amb/health-service/{medical_exam_id}'

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        request_data = {
            'gender': gender,
            'date_of_birth': date_of_birth,
            'health_centers': health_centers,
        }

        print(f"\n🧪 Testing Flow Generation API")
        print(f"   URL: {api_url}")
        print(f"   Service ID: {medical_exam_id}")
        print(f"   Health Centers: {health_centers}")
        print(f"   Timeout: {self.timeout}s")
        print(f"   Gender: {gender}")
        print(f"   DOB: {date_of_birth}")

        start_time = time.time()

        try:
            response = requests.get(
                api_url,
                headers=headers,
                params=request_data,
                timeout=self.timeout
            )

            end_time = time.time()
            response_time = end_time - start_time

            print(f"\n📊 Response received in {response_time:.2f}s")
            print(f"   Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ API call successful!")
                print(f"   Service Name: {data.get('name', 'N/A')}")
                print(f"   Service Code: {data.get('health_service_code', 'N/A')}")
                print(f"   Relations Count: {len(data.get('health_service_relations', []))}")

                # Analyze the response structure
                self._analyze_response_structure(data)

                return {
                    "success": True,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "data": data
                }
            else:
                print(f"❌ API call failed with status {response.status_code}")
                print(f"   Response: {response.text}")

                return {
                    "success": False,
                    "response_time": response_time,
                    "status_code": response.status_code,
                    "error": response.text
                }

        except requests.exceptions.Timeout:
            end_time = time.time()
            response_time = end_time - start_time

            print(f"⏰ API call timed out after {response_time:.2f}s (limit: {self.timeout}s)")

            return {
                "success": False,
                "response_time": response_time,
                "error": f"Request timed out after {self.timeout}s"
            }

        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time

            print(f"❌ API call failed with error: {e}")

            return {
                "success": False,
                "response_time": response_time,
                "error": str(e)
            }

    def _analyze_response_structure(self, data: Dict[str, Any]):
        """Analyze the response structure to understand the flow generation data"""
        print(f"\n🔍 Response Structure Analysis:")

        # Basic service info
        print(f"   UUID: {data.get('uuid')}")
        print(f"   Requires Prescription: {data.get('requires_prescription')}")
        print(f"   Requires Recontact: {data.get('requires_recontact')}")
        print(f"   Requires Preliminary Visit: {data.get('requires_preliminary_visit')}")
        print(f"   Medical Examination: {data.get('medical_examination')}")
        print(f"   Follow Up: {data.get('follow_up')}")

        # Relations analysis
        relations = data.get('health_service_relations', [])
        if relations:
            print(f"   Health Service Relations:")
            relation_types = {}
            for relation in relations:
                rel_type = relation.get('health_service_relation_type', {}).get('label', 'Unknown')
                if rel_type not in relation_types:
                    relation_types[rel_type] = 0
                relation_types[rel_type] += 1

            for rel_type, count in relation_types.items():
                print(f"      {rel_type}: {count} relations")

    def test_with_multiple_timeouts(
        self,
        medical_exam_id: str,
        health_centers: List[str],
        timeouts: List[int] = [15, 30, 45, 60, 90]
    ):
        """Test the API with multiple timeout values to find optimal setting"""
        print(f"\n🔄 Testing multiple timeout values...")

        results = []

        for timeout in timeouts:
            print(f"\n--- Testing with {timeout}s timeout ---")
            self.timeout = timeout

            result = self.test_flow_generation_api(medical_exam_id, health_centers)
            result['timeout'] = timeout
            results.append(result)

            if result['success']:
                print(f"✅ Success with {timeout}s timeout!")
                break
            else:
                print(f"❌ Failed with {timeout}s timeout")

        # Summary
        print(f"\n📈 Timeout Test Summary:")
        for result in results:
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            print(f"   {result['timeout']}s: {status} (Response time: {result['response_time']:.2f}s)")

        return results


def main():
    parser = argparse.ArgumentParser(description="Test Flow Generation API")
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--service-uuid', type=str,
                       default='ffea106f-44e3-49d6-a3b5-606c3c5898ad',
                       help='Medical service UUID to test')
    parser.add_argument('--health-centers', type=str, nargs='+',
                       default=['c48ff93f-1c88-4621-9cd5-31ad87e83e48',
                               '6cff89d8-1f40-4eb8-bed7-f36e94a3355c',
                               'c8a339e0-95c8-430b-ace6-640f3fd49ab1'],
                       help='Health center UUIDs')
    parser.add_argument('--multiple-timeouts', action='store_true',
                       help='Test with multiple timeout values')
    parser.add_argument('--gender', type=str, default='f', choices=['m', 'f'],
                       help='Patient gender')
    parser.add_argument('--dob', type=str, default='19990106',
                       help='Date of birth in YYYYMMDD format')

    args = parser.parse_args()

    print(f"🧪 Flow Generation API Tester")
    print(f"============================")

    tester = FlowGenerationAPITester(timeout=args.timeout)

    if args.multiple_timeouts:
        # Test with multiple timeout values
        results = tester.test_with_multiple_timeouts(
            args.service_uuid,
            args.health_centers
        )

        # Find minimum successful timeout
        successful_results = [r for r in results if r['success']]
        if successful_results:
            min_timeout = min(r['timeout'] for r in successful_results)
            print(f"\n💡 Recommendation: Use minimum timeout of {min_timeout}s")
    else:
        # Single test
        result = tester.test_flow_generation_api(
            args.service_uuid,
            args.health_centers,
            args.gender,
            args.dob
        )

        if result['success']:
            print(f"\n✅ Test completed successfully!")
            print(f"💡 API is working with {args.timeout}s timeout")
        else:
            print(f"\n❌ Test failed!")
            print(f"💡 Consider increasing timeout or checking network connectivity")


if __name__ == "__main__":
    main()