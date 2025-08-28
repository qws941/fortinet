-- FortiGate Nextrade Database Schema

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS fortinet;

-- Set search path
SET search_path TO fortinet, public;

-- Create tables
CREATE TABLE IF NOT EXISTS fortinet.configurations (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE NOT NULL,
    value JSONB NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(20) NOT NULL,
    source VARCHAR(100),
    message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    data JSONB,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.policies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    source VARCHAR(255),
    destination VARCHAR(255),
    service VARCHAR(255),
    action VARCHAR(50),
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.alerts (
    id BIGSERIAL PRIMARY KEY,
    alert_id VARCHAR(255) UNIQUE NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source VARCHAR(100),
    title TEXT NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fortinet.metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name VARCHAR(255) NOT NULL,
    metric_value NUMERIC,
    unit VARCHAR(50),
    source VARCHAR(100),
    tags JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON fortinet.logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_level ON fortinet.logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_source ON fortinet.logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_metadata ON fortinet.logs USING GIN(metadata);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON fortinet.sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON fortinet.sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_policies_enabled ON fortinet.policies(enabled);
CREATE INDEX IF NOT EXISTS idx_policies_priority ON fortinet.policies(priority);
CREATE INDEX IF NOT EXISTS idx_policies_metadata ON fortinet.policies USING GIN(metadata);

CREATE INDEX IF NOT EXISTS idx_alerts_severity ON fortinet.alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON fortinet.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at ON fortinet.alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_metadata ON fortinet.alerts USING GIN(metadata);

CREATE INDEX IF NOT EXISTS idx_metrics_name ON fortinet.metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON fortinet.metrics(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_metrics_tags ON fortinet.metrics USING GIN(tags);

-- Create update trigger function
CREATE OR REPLACE FUNCTION fortinet.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON fortinet.configurations
    FOR EACH ROW EXECUTE FUNCTION fortinet.update_updated_at_column();

CREATE TRIGGER update_sessions_updated_at BEFORE UPDATE ON fortinet.sessions
    FOR EACH ROW EXECUTE FUNCTION fortinet.update_updated_at_column();

CREATE TRIGGER update_policies_updated_at BEFORE UPDATE ON fortinet.policies
    FOR EACH ROW EXECUTE FUNCTION fortinet.update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON fortinet.alerts
    FOR EACH ROW EXECUTE FUNCTION fortinet.update_updated_at_column();