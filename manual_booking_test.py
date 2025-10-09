#!/usr/bin/env python3
"""
Manual booking test script
Based on data from log file: 20251006_095456_bc375e99_393333319326.log
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.booking_api import create_booking

# Booking data based on your log file
booking_data = {
    "patient": {
        "name": "MARIO",  # From log: patient collected name
        "surname": "ROSSI",  # From log: patient collected surname
        "email": "invictusblaze7@gmail.com",  # Example email
        "phone": "393333319326",  # From log: caller phone
        "date_of_birth": "1980-04-13",  # From log: collected DOB
        "fiscal_code": "RSSMRA80D13F205X",  # Generated fiscal code
        "gender": "M"  # From log: collected gender (male)
    },
    "booking_type": "private",
    "health_services": [
        {
            "uuid": "9a93d65f-396a-45e4-9284-94481bdd2b51",  # RX Caviglia Destra UUID from log
            "slot": "33e5b651-b413-465b-9e9a-bd925e62e737"  # You need the exact slot UUID from the booking
        }
    ],
    "reminder_authorization": True,
    "marketing_authorization": False
}

def test_manual_booking():
    """Test the manual booking creation"""
    print("🧪 Testing manual booking creation...")
    print(f"📋 Booking data: {booking_data}")

    # Call the booking API
    result = create_booking(booking_data)

    print("\n📊 RESULT:")
    print(f"Success: {result.get('success', False)}")
    print(f"Message: {result.get('message', 'N/A')}")

    if result.get('success'):
        booking = result.get('booking', {})
        print(f"🎉 Booking Code: {booking.get('code', 'N/A')}")
        print(f"📋 Booking UUID: {booking.get('uuid', 'N/A')}")
        print(f"📅 Created At: {booking.get('created_at', 'N/A')}")
    else:
        print(f"❌ Booking failed: {result.get('message', 'Unknown error')}")

    return result

if __name__ == "__main__":
    test_manual_booking()