from datetime import datetime
from zoneinfo import ZoneInfo

# ============================================
# COMPLETE FLOW - API TO USER TO API
# ============================================

# ============================================
# STEP 1: GET slots from API (UTC format)
# ============================================
# API: GET https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/{ambiente}/amb/health-center/{health_center_uuid}/slot
# API returns slots in UTC format
api_slot_utc = "2025-11-08T09:55:00+00:00"

print(f"1. Received from API (UTC): {api_slot_utc}")


# ============================================
# STEP 2: Convert to Italian time for display
# ============================================
# Parse the UTC datetime
dt_utc = datetime.fromisoformat(api_slot_utc)

# Convert to Italian timezone
dt_italian = dt_utc.astimezone(ZoneInfo("Europe/Rome"))

# Format for user display (dd-mm-yyyy hh:mm)
italian_display = dt_italian.strftime("%d-%m-%Y %H:%M")

print(f"2. Display to user (Italian): {italian_display}")
# Output: 08-11-2025 10:55


# ============================================
# STEP 3: User selects this slot
# ============================================
# The user sees and selects: "08-11-2025 10:55"
user_selected_slot = italian_display  # This is what user selected

print(f"3. User selected (Italian): {user_selected_slot}")


# ============================================
# STEP 4: Convert back to UTC for booking API
# ============================================
# Parse the Italian datetime
dt_italian = datetime.strptime(user_selected_slot, "%d-%m-%Y %H:%M")

# Set timezone to Italy
dt_italian = dt_italian.replace(tzinfo=ZoneInfo("Europe/Rome"))

# Convert back to UTC
dt_utc = dt_italian.astimezone(ZoneInfo("UTC"))

# Format for booking API
utc_for_booking = dt_utc.isoformat()

print(f"4. Send to booking API (UTC): {utc_for_booking}")
# Output: 2025-11-08T09:55:00+00:00


# ============================================
# VERIFY: Same datetime!
# ============================================
print(f"\n✓ Original API UTC: {api_slot_utc}")
print(f"✓ Converted back UTC: {utc_for_booking}")
print(f"✓ Match: {api_slot_utc == utc_for_booking}")


# ============================================
# HELPER FUNCTIONS FOR YOUR CODE
# ============================================

def convert_api_slot_to_display(utc_from_api):
    """
    Step 1: Convert slot from API (UTC) to user display (Italian)
    """
    dt = datetime.fromisoformat(utc_from_api).astimezone(ZoneInfo("Europe/Rome"))
    return dt.strftime("%d-%m-%Y %H:%M")


def convert_user_selection_to_api(italian_datetime):
    """
    Step 2: Convert user selection (Italian) back to API format (UTC)
    """
    dt = datetime.strptime(italian_datetime, "%d-%m-%Y %H:%M")
    dt = dt.replace(tzinfo=ZoneInfo("Europe/Rome"))
    return dt.astimezone(ZoneInfo("UTC")).isoformat()


# ============================================
# USAGE IN YOUR APPLICATION
# ============================================
print("\n" + "="*50)
print("USAGE EXAMPLE")
print("="*50)

# 1. Get slot from API
slot_from_api = "2025-11-08T09:55:00+00:00"
print(f"API returns: {slot_from_api}")

# 2. Show to user in Italian
slot_italian = convert_api_slot_to_display(slot_from_api)
print(f"Show user: {slot_italian}")

# 3. User selects this slot, convert back to UTC for booking
slot_for_booking = convert_user_selection_to_api(slot_italian)
print(f"Send to booking: {slot_for_booking}")

# Verify it's the same
print(f"✓ Conversion successful: {slot_from_api == slot_for_booking}")