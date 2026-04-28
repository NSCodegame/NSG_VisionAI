-- NSG VisionAI — Database Setup Script
-- Run as postgres superuser

-- 1. Create user
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'nsg_admin') THEN
    CREATE USER nsg_admin WITH PASSWORD 'change_me_in_production';
    RAISE NOTICE 'User nsg_admin created';
  ELSE
    ALTER USER nsg_admin WITH PASSWORD 'change_me_in_production';
    RAISE NOTICE 'User nsg_admin password updated';
  END IF;
END
$$;

-- 2. Create database
SELECT 'CREATE DATABASE nsg_visionai OWNER nsg_admin'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nsg_visionai') \gexec

-- 3. Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nsg_visionai TO nsg_admin;

-- 4. Connect to the new database and enable extensions
\c nsg_visionai

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- pgvector (if installed)
DO $$
BEGIN
  CREATE EXTENSION IF NOT EXISTS vector;
  RAISE NOTICE 'pgvector extension enabled';
EXCEPTION WHEN OTHERS THEN
  RAISE NOTICE 'pgvector not available — skipping (face recognition will be limited)';
END
$$;

-- Grant schema permissions
GRANT ALL ON SCHEMA public TO nsg_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nsg_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nsg_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nsg_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO nsg_admin;

\echo 'Database setup complete!'
