# 🗄️ Supabase Database Schema

## 📋 Overview

This directory contains the **Supabase (PostgreSQL) database schema** for the Voilà Voice Dashboard + Pipecat Agent integration.

## 📁 Files

- `supabase_schema.sql` - Complete database schema for Supabase

## 🚀 Quick Setup

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Create a new project
3. Note your project URL and API keys

### Step 2: Run Schema in Supabase

1. Open your Supabase project
2. Go to **SQL Editor**
3. Click **New Query**
4. Copy and paste `supabase_schema.sql`
5. Click **Run** or press `Ctrl+Enter`

### Step 3: Verify Tables Created

Go to **Table Editor** and verify these tables exist:
- ✅ users
- ✅ user_sessions
- ✅ tb_voice_agent
- ✅ tb_stat
- ✅ qa_entries
- ✅ region_exam_pricing
- ✅ sport_requisiti
- ✅ sport_preparazione
- ✅ pipecat_sessions
- ✅ pipecat_function_calls
- ✅ knowledge_base_sync_log
- ✅ tb_prompt

### Step 4: Get Database Credentials

In Supabase Dashboard:
1. Go to **Settings** → **Database**
2. Note these connection details:
   - Host
   - Database name
   - Port
   - User
   - Password

## 🔧 Update Environment Variables

### For FastAPI Backend (`app.py`)

Update `D:\freelancing_projects\DashboardVoilaVoice\DashboardVoilaVoice\.env`:

```bash
# Supabase PostgreSQL Configuration
DB_HOST=db.your-project.supabase.co
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-password-here
DB_NAME=postgres
DB_CHARSET=utf8

# Supabase API Keys
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key
```

### For Pipecat Agent

Update `D:\freelancing_projects\pipecat-booking-agent\.env`:

```bash
# Supabase PostgreSQL Configuration  
DB_HOST=db.your-project.supabase.co
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-password-here
DB_NAME=postgres

# Supabase API
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-key
```

## 📊 Database Schema

### Core Tables:

1. **users** - Dashboard users
2. **user_sessions** - Authentication tokens
3. **tb_voice_agent** - Voice agent configurations
4. **tb_stat** - Call statistics (main analytics table)
5. **qa_entries** - Knowledge base Q&A

### Pipecat-Specific Tables:

6. **pipecat_sessions** - Detailed session tracking
7. **pipecat_function_calls** - Function call logging

### Supporting Tables:

8. **region_exam_pricing** - Pricing data
9. **sport_requisiti** - Sport requirements
10. **sport_preparazione** - Preparation requirements
11. **knowledge_base_sync_log** - Q&A sync tracking
12. **tb_prompt** - System prompts

## 🔐 Security (Row Level Security)

The schema includes RLS policies:

- **Users**: Can only see their own data
- **Admins**: Can see all data
- **Regional users**: Can see calls from their region

## 📈 Views & Functions

### Views:
- `daily_call_stats` - Aggregated daily statistics
- `qa_stats_by_region` - Q&A statistics per region

### Functions:
- `get_call_stats()` - Get statistics for date range
- `update_updated_at_column()` - Auto-update timestamps

## 🌱 Seed Data

The schema includes:
- Default admin user (email: `admin@voila.com`, password: `admin123`)
- Sample voice agents for 3 regions

**⚠️ IMPORTANT: Change the admin password immediately in production!**

## 🔄 Migration from MySQL

If you have existing MySQL data:

1. Export data from MySQL:
```sql
-- In MySQL
SELECT * INTO OUTFILE 'users.csv' FROM users;
SELECT * INTO OUTFILE 'qa_entries.csv' FROM qa_entries;
-- etc.
```

2. Import to Supabase:
   - Use Supabase Table Editor
   - Click **Insert** → **Import CSV**
   - Upload your CSV files

Or use a migration tool like `pgloader`:
```bash
pgloader mysql://user:pass@mysql-host/db_name postgresql://postgres:pass@supabase-host/postgres
```

## 📝 Notes

### PostgreSQL vs MySQL Differences:

- **AUTO_INCREMENT** → **SERIAL**
- **DATETIME** → **TIMESTAMP WITH TIME ZONE**
- **TINYINT** → **BOOLEAN**
- **ENUM** → **CHECK** constraint
- **FULLTEXT** → **GIN** indexes with `to_tsvector`

### Supabase Features Used:

- ✅ Row Level Security (RLS)
- ✅ UUID generation
- ✅ Full-text search
- ✅ JSONB for metadata
- ✅ Array fields
- ✅ Triggers for auto-updates
- ✅ Views for analytics

## 🆘 Troubleshooting

### Issue: Permission denied

**Solution**: Ensure you're using the service key, not anon key

### Issue: UUID extension not found

**Solution**: Run `CREATE EXTENSION IF NOT EXISTS "uuid-ossp";`

### Issue: RLS blocking queries

**Solution**: Use service key or disable RLS for development:
```sql
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;
```

## 📖 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)

---

**Schema Version:** 1.0  
**Last Updated:** November 13, 2025  
**Compatible with:** Supabase, PostgreSQL 14+
