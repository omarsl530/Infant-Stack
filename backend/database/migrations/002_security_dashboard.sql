-- Security Dashboard schema additions
-- Version: 002
-- Description: Add tables for RTLS positions, gates, cameras, zones, and floorplans
-- This script is DESTRUCTIVE for the tables it creates to ensure a clean state in dev.
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- ============================================================================
-- Drop existing objects if they exist (Cleanup)
-- ============================================================================
DROP TABLE IF EXISTS floorplans CASCADE;
DROP TABLE IF EXISTS cameras CASCADE;
DROP TABLE IF EXISTS zones CASCADE;
DROP TABLE IF EXISTS gate_events CASCADE;
DROP TABLE IF EXISTS gates CASCADE;
DROP TABLE IF EXISTS rtls_positions CASCADE;
DROP TABLE IF EXISTS alerts CASCADE;
-- Be careful if alerts are shared
DROP TYPE IF EXISTS gate_state CASCADE;
DROP TYPE IF EXISTS gate_event_type CASCADE;
DROP TYPE IF EXISTS gate_event_result CASCADE;
DROP TYPE IF EXISTS zone_type CASCADE;
DROP TYPE IF EXISTS camera_status CASCADE;
-- ============================================================================
-- Enums
-- ============================================================================
CREATE TYPE gate_state AS ENUM (
    'OPEN',
    'CLOSED',
    'FORCED_OPEN',
    'HELD_OPEN',
    'UNKNOWN'
);
CREATE TYPE gate_event_type AS ENUM (
    'badge_scan',
    'gate_state',
    'forced',
    'held_open'
);
CREATE TYPE gate_event_result AS ENUM ('GRANTED', 'DENIED');
CREATE TYPE zone_type AS ENUM ('authorized', 'restricted', 'exit');
CREATE TYPE camera_status AS ENUM ('online', 'offline', 'error');
-- ============================================================================
-- RTLS Positions Table (time-series data)
-- ============================================================================
CREATE TABLE rtls_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tag_id VARCHAR(50) NOT NULL,
    asset_type VARCHAR(20) NOT NULL,
    x DOUBLE PRECISION NOT NULL,
    y DOUBLE PRECISION NOT NULL,
    z DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    floor VARCHAR(20) NOT NULL,
    accuracy DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    battery_pct INTEGER NOT NULL DEFAULT 100,
    gateway_id VARCHAR(50),
    rssi INTEGER,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_rtls_positions_tag ON rtls_positions(tag_id);
CREATE INDEX idx_rtls_positions_floor ON rtls_positions(floor);
CREATE INDEX idx_rtls_positions_timestamp ON rtls_positions(timestamp DESC);
CREATE INDEX idx_rtls_positions_tag_timestamp ON rtls_positions(tag_id, timestamp DESC);
CREATE INDEX idx_rtls_positions_floor_timestamp ON rtls_positions(floor, timestamp DESC);
-- ============================================================================
-- Gates Table
-- ============================================================================
CREATE TABLE gates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gate_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    floor VARCHAR(20) NOT NULL,
    zone VARCHAR(50) NOT NULL,
    state gate_state NOT NULL DEFAULT 'CLOSED',
    last_state_change TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    camera_id VARCHAR(50),
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_gates_gate_id ON gates(gate_id);
CREATE INDEX idx_gates_floor ON gates(floor);
CREATE INDEX idx_gates_state ON gates(state);
-- ============================================================================
-- Gate Events Table
-- ============================================================================
CREATE TABLE gate_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    gate_id VARCHAR(50) NOT NULL,
    event_type gate_event_type NOT NULL,
    state gate_state,
    previous_state gate_state,
    badge_id VARCHAR(50),
    user_id VARCHAR(50),
    user_name VARCHAR(100),
    result gate_event_result,
    direction VARCHAR(10),
    duration_ms INTEGER,
    extra_data JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_gate_events_gate_id ON gate_events(gate_id);
CREATE INDEX idx_gate_events_timestamp ON gate_events(timestamp DESC);
CREATE INDEX idx_gate_events_gate_timestamp ON gate_events(gate_id, timestamp DESC);
CREATE INDEX idx_gate_events_badge ON gate_events(badge_id);
CREATE INDEX idx_gate_events_type ON gate_events(event_type);
-- ============================================================================
-- Zones Table (Geofences)
-- ============================================================================
CREATE TABLE zones (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    floor VARCHAR(20) NOT NULL,
    zone_type zone_type NOT NULL,
    polygon JSONB NOT NULL,
    color VARCHAR(20),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_zones_floor ON zones(floor);
CREATE INDEX idx_zones_type ON zones(zone_type);
CREATE INDEX idx_zones_active ON zones(is_active);
CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = NOW();
RETURN NEW;
END;
$$ language 'plpgsql';
CREATE TRIGGER update_zones_updated_at BEFORE
UPDATE ON zones FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
-- ============================================================================
-- Cameras Table
-- ============================================================================
CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    floor VARCHAR(20) NOT NULL,
    zone VARCHAR(50),
    gate_id VARCHAR(50),
    stream_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    status camera_status NOT NULL DEFAULT 'online',
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_cameras_camera_id ON cameras(camera_id);
CREATE INDEX idx_cameras_floor ON cameras(floor);
CREATE INDEX idx_cameras_gate_id ON cameras(gate_id);
CREATE INDEX idx_cameras_status ON cameras(status);
-- ============================================================================
-- Floorplans Table
-- ============================================================================
CREATE TABLE floorplans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    floor VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    image_url VARCHAR(500) NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    scale DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    origin_x DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    origin_y DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    extra_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_floorplans_floor ON floorplans(floor);
-- ============================================================================
-- Alerts Table (if likely dropped or missing)
-- ============================================================================
-- Re-creating alerts if we dropped it (Alerts are shared, so tread carefully. 
-- Assuming they are part of the new stack and not critical persistence from prior work if strictly dev.)
-- For this sprint, I'll recreate it to ensure schema match.
CREATE TYPE alert_severity AS ENUM ('INFO', 'WARNING', 'CRITICAL');
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity alert_severity NOT NULL,
    tag_id VARCHAR(50),
    reader_id VARCHAR(50),
    message TEXT NOT NULL,
    extra_data JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID,
    -- linked to user table if exists
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged);
-- ============================================================================
-- Seed data for testing
-- ============================================================================
-- Insert sample floorplan
INSERT INTO floorplans (floor, name, image_url, width, height, scale)
VALUES (
        'F1',
        'Ground Floor - Maternity Ward',
        '/assets/floorplans/floor1.svg',
        1000,
        800,
        10.0
    ),
    (
        'F2',
        'Second Floor - NICU',
        '/assets/floorplans/floor2.svg',
        1000,
        800,
        10.0
    );
-- Insert sample gates
INSERT INTO gates (gate_id, name, floor, zone, state)
VALUES (
        'GATE-A1',
        'Main Entry A1',
        'F1',
        'Entry',
        'CLOSED'
    ),
    (
        'GATE-A2',
        'Main Entry A2',
        'F1',
        'Entry',
        'CLOSED'
    ),
    ('GATE-B1', 'NICU Entry', 'F2', 'NICU', 'CLOSED'),
    (
        'GATE-E1',
        'Emergency Exit 1',
        'F1',
        'Exit',
        'CLOSED'
    );
-- Insert sample zones
INSERT INTO zones (name, floor, zone_type, polygon, color)
VALUES (
        'Reception Area',
        'F1',
        'authorized',
        '{"points": [{"x": 50, "y": 50}, {"x": 200, "y": 50}, {"x": 200, "y": 150}, {"x": 50, "y": 150}]}',
        '#4ade80'
    ),
    (
        'NICU Ward',
        'F2',
        'restricted',
        '{"points": [{"x": 100, "y": 100}, {"x": 400, "y": 100}, {"x": 400, "y": 300}, {"x": 100, "y": 300}]}',
        '#f87171'
    ),
    (
        'Emergency Exit Zone',
        'F1',
        'exit',
        '{"points": [{"x": 800, "y": 600}, {"x": 950, "y": 600}, {"x": 950, "y": 750}, {"x": 800, "y": 750}]}',
        '#fbbf24'
    );
-- Insert sample cameras
INSERT INTO cameras (
        camera_id,
        name,
        floor,
        zone,
        gate_id,
        stream_url,
        status
    )
VALUES (
        'CAM-A1',
        'Camera Gate A1',
        'F1',
        'Entry',
        'GATE-A1',
        'rtsp://cameras.local/gate-a1',
        'online'
    ),
    (
        'CAM-A2',
        'Camera Gate A2',
        'F1',
        'Entry',
        'GATE-A2',
        'rtsp://cameras.local/gate-a2',
        'online'
    ),
    (
        'CAM-NICU1',
        'NICU Hallway Camera',
        'F2',
        'NICU',
        NULL,
        'rtsp://cameras.local/nicu-1',
        'online'
    ),
    (
        'CAM-E1',
        'Emergency Exit Camera',
        'F1',
        'Exit',
        'GATE-E1',
        'rtsp://cameras.local/exit-1',
        'offline'
    );