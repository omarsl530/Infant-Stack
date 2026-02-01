-- Initial schema for Infant-Stack database
-- Version: 001
-- Description: Create core tables for infant security ecosystem
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- ============================================================================
-- Enums
-- ============================================================================
CREATE TYPE tag_status AS ENUM ('active', 'inactive', 'alert', 'maintenance');
CREATE TYPE pairing_status AS ENUM ('active', 'discharged', 'suspended');
CREATE TYPE alert_severity AS ENUM ('info', 'warning', 'critical');
CREATE TYPE user_role AS ENUM ('admin', 'nurse', 'security', 'viewer');
-- ============================================================================
-- Users Table (created first for foreign key references)
-- ============================================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    role user_role NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login TIMESTAMPTZ
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
-- ============================================================================
-- Infants Table
-- ============================================================================
CREATE TABLE infants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id VARCHAR(50) NOT NULL UNIQUE,
    medical_record_number VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth TIMESTAMPTZ NOT NULL,
    ward VARCHAR(50) NOT NULL,
    room VARCHAR(20),
    tag_status tag_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_infants_tag_id ON infants(tag_id);
CREATE INDEX idx_infants_ward ON infants(ward);
CREATE INDEX idx_infants_status ON infants(tag_status);
-- ============================================================================
-- Mothers Table
-- ============================================================================
CREATE TABLE mothers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id VARCHAR(50) NOT NULL UNIQUE,
    medical_record_number VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(20),
    ward VARCHAR(50) NOT NULL,
    room VARCHAR(20),
    tag_status tag_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_mothers_tag_id ON mothers(tag_id);
CREATE INDEX idx_mothers_ward ON mothers(ward);
-- ============================================================================
-- Pairings Table
-- ============================================================================
CREATE TABLE pairings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    infant_id UUID NOT NULL REFERENCES infants(id) ON DELETE CASCADE,
    mother_id UUID NOT NULL REFERENCES mothers(id) ON DELETE CASCADE,
    status pairing_status NOT NULL DEFAULT 'active',
    paired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    discharged_at TIMESTAMPTZ,
    paired_by_user_id UUID REFERENCES users(id),
    UNIQUE(infant_id, mother_id, status)
);
CREATE INDEX idx_pairings_infant ON pairings(infant_id);
CREATE INDEX idx_pairings_mother ON pairings(mother_id);
CREATE INDEX idx_pairings_status ON pairings(status);
-- ============================================================================
-- Movement Logs Table
-- ============================================================================
CREATE TABLE movement_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id VARCHAR(50) NOT NULL,
    reader_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    zone VARCHAR(50),
    metadata JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_movement_logs_tag ON movement_logs(tag_id);
CREATE INDEX idx_movement_logs_reader ON movement_logs(reader_id);
CREATE INDEX idx_movement_logs_timestamp ON movement_logs(timestamp);
CREATE INDEX idx_movement_logs_tag_time ON movement_logs(tag_id, timestamp DESC);
-- ============================================================================
-- Alerts Table
-- ============================================================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity alert_severity NOT NULL,
    tag_id VARCHAR(50),
    reader_id VARCHAR(50),
    message TEXT NOT NULL,
    metadata JSONB,
    acknowledged BOOLEAN NOT NULL DEFAULT false,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_tag ON alerts(tag_id);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
-- ============================================================================
-- Audit Logs Table
-- ============================================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_user_created ON audit_logs(user_id, created_at DESC);
-- ============================================================================
-- Trigger for updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ language 'plpgsql';
CREATE TRIGGER update_infants_updated_at BEFORE
UPDATE ON infants FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_mothers_updated_at BEFORE
UPDATE ON mothers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();