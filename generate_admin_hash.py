#!/usr/bin/env python3
"""Generate admin password hash for admin123"""

import bcrypt

password = "admin123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
hashed_str = hashed.decode('utf-8')

print(f"Password: {password}")
print(f"Generated Hash: {hashed_str}")
print()

# Test verification
test_verify = bcrypt.checkpw(password.encode('utf-8'), hashed)
print(f"Verification test: {test_verify}")
print()

# SQL update command
print("Run this SQL in Supabase:")
print(f"UPDATE users SET password_hash = '{hashed_str}' WHERE email = 'admin@voila.com';")
