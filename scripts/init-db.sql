-- NSG VisionAI Platform - Database Initialization Script
-- This script runs automatically when PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for face embeddings
CREATE EXTENSION IF NOT EXISTS "timescaledb";  -- TimescaleDB for time-series data

-- Create database if not exists (handled by POSTGRES_DB env var)
-- Database: nsg_visionai

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nsg_visionai TO nsg_admin;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'NSG VisionAI Database initialized successfully';
    RAISE NOTICE 'Extensions enabled: uuid-ossp, pgcrypto, vector, timescaledb';
END $$;
