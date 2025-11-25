# Multi-Region Dashboard Deployment Guide

## Overview

This guide covers deploying the updated system with **region-based filtering** using a simplified architecture:
- ✅ **No tb_voice_agent mapping table** needed
- ✅ Region stored directly in `tb_stat` table
- ✅ Dashboard connects to **bot.py** (port 8000) production server
- ✅ Supports multiple regions (Lombardia, Piemonte, Veneto, etc.)

---

## 📋 What Changed

### **Backend Changes:**
1. ✅ `info_agent/services/call_data_extractor.py` - Now stores `region` from environment variable
2. ✅ `info_agent/api/dashboard.py` - Filters by `region` column directly (removed tb_voice_agent dependency)
3. ✅ `.env` - Added `INFO_AGENT_REGION` variable

### **Frontend Changes:**
1. ✅ `info_frontend/.env` - Updated to point to port 8000 (bot.py)
2. ✅ `info_frontend/.env.local` - Updated to port 8000
3. ✅ `info_frontend/.env.production` - Already correct (port 8000)

### **Database Changes:**
1. ✅ Migration script created: `info_agent/sql_schema/migration_add_region_column.sql`

---

## 🗄️ Step 1: Database Migration

### Run SQL Migration on Supabase

**Login to Supabase:**
1. Go to: https://supabase.com/dashboard
2. Select your project
3. Navigate to **SQL Editor**

**Execute Migration Script:**

```sql
-- ============================================
-- Migration: Add Region Column & Required Tables
-- ============================================

-- 1. ADD REGION COLUMN TO tb_stat
ALTER TABLE tb_stat
ADD COLUMN IF NOT EXISTS region VARCHAR(100);

-- Create index for fast filtering
CREATE INDEX IF NOT EXISTS idx_stat_region ON tb_stat(region);

-- Backfill existing data (extract region from assistant_id)
UPDATE tb_stat
SET region = CASE
    WHEN assistant_id ILIKE '%lombardia%' OR assistant_id ILIKE '%lombardy%' THEN 'Lombardia'
    WHEN assistant_id ILIKE '%piemonte%' OR assistant_id ILIKE '%piedmont%' THEN 'Piemonte'
    WHEN assistant_id ILIKE '%veneto%' THEN 'Veneto'
    ELSE 'Unknown'
END
WHERE region IS NULL;

-- 2. USERS & AUTHENTICATION TABLES
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'operator',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    session_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);

-- 3. Q/A MANAGEMENT TABLE
CREATE TABLE IF NOT EXISTS qa_entries (
    qa_id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    region VARCHAR(100) NOT NULL DEFAULT 'Piemonte',
    pinecone_id VARCHAR(255) UNIQUE,
    id_domanda VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_qa_region ON qa_entries(region);

-- 4. CREATE DEFAULT ADMIN USER
INSERT INTO users (email, name, password_hash, role)
VALUES (
    'admin@voila.com',
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvQGvF4a7cOy',
    'admin'
) ON CONFLICT (email) DO NOTHING;
```

**Verify Migration:**
```sql
-- Check region column exists and is populated
SELECT region, COUNT(*) as call_count
FROM tb_stat
GROUP BY region;

-- Check admin user created
SELECT email, name, role FROM users WHERE email = 'admin@voila.com';
```

---

## ⚙️ Step 2: Configure Each Voice Agent VM

### **Lombardia VM**

**Update `.env` file:**
```bash
# Database (SAME for all regions)
DATABASE_URL=postgresql://postgres.yxqconubtqdskcxiobsp:2YdCPz7Aiya8@aws-1-eu-north-1.pooler.supabase.com:6543/postgres?pgbouncer=true

# Region Identity (UNIQUE per VM)
INFO_AGENT_REGION=Lombardia
INFO_AGENT_ASSISTANT_ID=pipecat-lombardia-001
```

**Restart bot.py:**
```bash
# If using Docker
docker-compose down
docker-compose pull
docker-compose up -d

# Or if running directly
pkill -f "python bot.py"
python bot.py
```

### **Piemonte VM**

**Update `.env` file:**
```bash
# Database (SAME for all regions)
DATABASE_URL=postgresql://postgres.yxqconubtqdskcxiobsp:2YdCPz7Aiya8@aws-1-eu-north-1.pooler.supabase.com:6543/postgres?pgbouncer=true

# Region Identity (UNIQUE per VM)
INFO_AGENT_REGION=Piemonte
INFO_AGENT_ASSISTANT_ID=pipecat-piemonte-001
```

**Restart bot.py** (same as above)

### **Veneto VM (Future)**

**Update `.env` file:**
```bash
# Database (SAME for all regions)
DATABASE_URL=postgresql://postgres.yxqconubtqdskcxiobsp:2YdCPz7Aiya8@aws-1-eu-north-1.pooler.supabase.com:6543/postgres?pgbouncer=true

# Region Identity (UNIQUE per VM)
INFO_AGENT_REGION=Veneto
INFO_AGENT_ASSISTANT_ID=pipecat-veneto-001
```

---

## 🖥️ Step 3: Frontend Deployment

### **Local Development**

```bash
cd info_frontend
npm install
npm run dev
```

**Access:** http://localhost:3000

### **Production Deployment**

**Option 1: Same Server as bot.py**
```bash
cd info_frontend
npm run build
npm start  # or use PM2
```

**Option 2: Separate Server**

Update `.env.production`:
```bash
# Point to bot.py production server
NEXT_PUBLIC_API_URL=http://98.66.139.255:8000/api

# Or with domain:
# NEXT_PUBLIC_API_URL=https://api-lombardia.yourcompany.com/api
```

Then build and deploy:
```bash
npm run build
npm start
```

---

## ✅ Step 4: Testing

### **Test 1: Database Migration**

```sql
-- Verify region column
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'tb_stat' AND column_name = 'region';

-- Check data populated
SELECT region, COUNT(*) FROM tb_stat GROUP BY region;
```

**Expected Output:**
```
region      | call_count
------------|----------
Lombardia   | 150
Unknown     | 0
```

### **Test 2: Backend APIs**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test regions endpoint
curl http://localhost:8000/api/dashboard/regions

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@voila.com","password":"admin123"}'
```

**Expected Output:**
```json
{
  "success": true,
  "access_token": "eyJ...",
  "user": {
    "email": "admin@voila.com",
    "role": "admin"
  }
}
```

### **Test 3: Frontend Dashboard**

1. Open browser: http://localhost:3000
2. Login: `admin@voila.com` / `admin123`
3. Verify dashboard loads
4. Check region dropdown shows regions from actual call data
5. Select different regions and verify data filters correctly

### **Test 4: Make Test Call**

1. Make a test call to Lombardia voice agent
2. Check Supabase `tb_stat` table
3. Verify new row has `region = 'Lombardia'`

```sql
SELECT call_id, phone_number, region, started_at
FROM tb_stat
ORDER BY started_at DESC
LIMIT 5;
```

---

## 🎯 Multi-Region Setup

### **Architecture**

```
┌─────────────────────────────────────────────────┐
│         CENTRALIZED DASHBOARD                    │
│         (info_frontend)                          │
│         http://dashboard.yourcompany.com         │
└──────────────┬──────────────────────────────────┘
               │
               │ Queries: ?region=Lombardia
               ▼
┌─────────────────────────────────────────────────┐
│         CENTRALIZED SUPABASE DATABASE            │
│                                                  │
│  tb_stat:                                       │
│  ┌──────────────────────────────────────────┐  │
│  │ call_id | phone | region    | transcript│  │
│  ├──────────────────────────────────────────┤  │
│  │ abc123  | +39.. | Lombardia | ...       │  │
│  │ def456  | +39.. | Piemonte  | ...       │  │
│  │ ghi789  | +39.. | Veneto    | ...       │  │
│  └──────────────────────────────────────────┘  │
└──────────────▲───────────────▲──────────────────┘
               │               │
       ┌───────┴───┐      ┌────┴──────┐
       │ bot.py    │      │ bot.py    │
       │ Lombardia │      │ Piemonte  │
       │ VM        │      │ VM        │
       │ Port 8000 │      │ Port 8000 │
       └───────────┘      └───────────┘
```

### **How Region Filtering Works**

**Frontend sends:**
```
GET /api/dashboard/stats?region=Lombardia
```

**Backend queries:**
```sql
SELECT COUNT(*), SUM(duration_seconds)
FROM tb_stat
WHERE region = 'Lombardia'  -- Direct filter!
AND started_at >= '2025-01-01';
```

**No mapping table needed!** ✅

---

## 🔧 Troubleshooting

### **Issue 1: Dashboard shows "No regions available"**

**Cause:** No call data in `tb_stat` or region column not populated

**Fix:**
```sql
-- Check if region column exists
SELECT * FROM tb_stat LIMIT 1;

-- Backfill if needed
UPDATE tb_stat
SET region = 'Lombardia'
WHERE region IS NULL
AND assistant_id LIKE '%lombardia%';
```

### **Issue 2: Login fails with 500 error**

**Cause:** Users table doesn't exist or admin user not created

**Fix:**
```sql
-- Check users table
SELECT * FROM users WHERE email = 'admin@voila.com';

-- Recreate admin user if missing
INSERT INTO users (email, name, password_hash, role)
VALUES (
    'admin@voila.com',
    'System Administrator',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5yvQGvF4a7cOy',
    'admin'
);
```

### **Issue 3: New calls don't show region**

**Cause:** `INFO_AGENT_REGION` not set in bot.py `.env`

**Fix:**
```bash
# Add to .env
INFO_AGENT_REGION=Lombardia

# Restart bot.py
docker-compose restart
```

### **Issue 4: Frontend can't reach backend**

**Cause:** Frontend pointing to wrong port or IP

**Fix:**
```bash
# Check frontend .env
cat info_frontend/.env
# Should show: NEXT_PUBLIC_API_URL=http://localhost:8000/api

# Check bot.py is running
curl http://localhost:8000/health
```

---

## 📊 Success Criteria

✅ **Database:**
- tb_stat has `region` column with index
- Existing calls backfilled with region
- users, user_sessions, qa_entries tables exist
- Default admin user can login

✅ **Backend:**
- bot.py stores region in tb_stat for new calls
- Dashboard APIs filter by region directly
- GET /api/dashboard/regions returns regions from tb_stat
- All authentication endpoints work

✅ **Frontend:**
- Connects to bot.py on port 8000
- Login works with admin@voila.com
- Dashboard displays call statistics
- Region dropdown populated from actual data
- Filtering by region works correctly

✅ **Multi-Region:**
- Each VM writes to same database with different region value
- Dashboard shows combined data from all regions
- Users can filter by specific region or view all

---

## 🚀 Production Deployment Checklist

- [ ] Run SQL migration on Supabase
- [ ] Verify admin user created (admin@voila.com)
- [ ] Update `.env` on each voice agent VM with `INFO_AGENT_REGION`
- [ ] Restart all bot.py instances
- [ ] Make test call and verify region stored correctly
- [ ] Deploy frontend to production server
- [ ] Update `.env.production` with production bot.py URL
- [ ] Test login to dashboard
- [ ] Test region filtering
- [ ] Test Q/A management (add/edit/delete)
- [ ] Monitor logs for errors

---

## 📞 Support

**Issues? Check logs:**
```bash
# bot.py logs
docker-compose logs -f pipecat-agent

# Frontend logs
npm run dev  # Shows console logs

# Supabase query logs
# Navigate to: Supabase Dashboard → SQL Editor → Query History
```

**Common Log Messages:**
- ✅ `"✅ Database connection pool initialized"` - Database connected
- ✅ `"✅ Call data updated in tb_stat table"` - Call data saved with region
- ❌ `"❌ Database connection failed"` - Check DATABASE_URL in .env
- ❌ `"region column does not exist"` - Run migration script

---

**Deployment Date:** 2025-01-20
**Version:** 2.0 (Region-based filtering)
