"""
Create an admin user for testing the dashboard
Run this once to create a test user in Supabase
"""

import asyncio
import os
from dotenv import load_dotenv
import asyncpg
import bcrypt
from datetime import datetime

load_dotenv()

async def create_admin_user():
    """Create an admin user in Supabase"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in .env")
        return
    
    # Admin user details
    email = "admin@voila.com"
    password = "admin@123"# Change this to your preferred password
    name = "Admin User"
    role = "admin"
    region = "master"
    
    try:
        # Connect to database
        conn = await asyncpg.connect(dsn=database_url)
        print("✅ Connected to PostgreSQL")
        
        # Check if user already exists
        existing = await conn.fetchrow(
            "SELECT user_id FROM users WHERE email = $1",
            email
        )
        
        if existing:
            print(f"⚠️ User {email} already exists!")
            print(f"   User ID: {existing['user_id']}")
            print("\nYou can login with:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            await conn.close()
            return
        
        # Hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Insert user
        current_time = datetime.now()
        user_id = await conn.fetchval(
            """
            INSERT INTO users (email, name, password_hash, role, region, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, true, $6, $7)
            RETURNING user_id
            """,
            email, name, password_hash, role, region, current_time, current_time
        )
        
        print(f"✅ Admin user created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Role: {role}")
        print(f"   Region: {region}")
        print("\n🎉 You can now login to the dashboard with these credentials!")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=" * 50)
    print("Creating Admin User for Dashboard")
    print("=" * 50)
    asyncio.run(create_admin_user())
