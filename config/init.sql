-- Create FortiGate database schema
CREATE SCHEMA IF NOT EXISTS fortinet;

-- Create tables
CREATE TABLE IF NOT EXISTS fortinet.devices (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    ip_address INET NOT NULL,
    model VARCHAR(50),
    status VARCHAR(20) DEFAULT 'offline',
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.policies (
    id SERIAL PRIMARY KEY,
    policy_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    source_zone VARCHAR(50),
    destination_zone VARCHAR(50),
    action VARCHAR(20),
    enabled BOOLEAN DEFAULT true,
    device_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.logs (
    id SERIAL PRIMARY KEY,
    log_type VARCHAR(50),
    severity VARCHAR(20),
    message TEXT,
    source VARCHAR(100),
    device_id VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS fortinet.sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(50),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_devices_status ON fortinet.devices(status);
CREATE INDEX idx_devices_last_seen ON fortinet.devices(last_seen);
CREATE INDEX idx_policies_device ON fortinet.policies(device_id);
CREATE INDEX idx_logs_timestamp ON fortinet.logs(timestamp);
CREATE INDEX idx_logs_device ON fortinet.logs(device_id);
CREATE INDEX idx_sessions_user ON fortinet.sessions(user_id);
CREATE INDEX idx_sessions_expires ON fortinet.sessions(expires_at);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION fortinet.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_devices_updated_at BEFORE UPDATE ON fortinet.devices
    FOR EACH ROW EXECUTE FUNCTION fortinet.update_updated_at_column();

CREATE TRIGGER update_policies_updated_at BEFORE UPDATE ON fortinet.policies
    FOR EACH ROW EXECUTE FUNCTION fortinet.update_updated_at_column();

-- Insert sample data
INSERT INTO fortinet.devices (device_id, name, ip_address, model, status) VALUES
    ('FGT001', 'FortiGate-HQ-01', '192.168.1.1', 'FGT-100F', 'online'),
    ('FGT002', 'FortiGate-Branch-01', '192.168.2.1', 'FGT-60F', 'online'),
    ('FGT003', 'FortiGate-DC-01', '10.0.0.1', 'FGT-200F', 'offline')
ON CONFLICT (device_id) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA fortinet TO fortinet;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA fortinet TO fortinet;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA fortinet TO fortinet;