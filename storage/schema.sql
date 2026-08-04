-- Workflow Event Store Schema
-- PostgreSQL

-- ═══════════════════════════════════════════════════════════════════════════════
-- workflow_runs 表：Workflow Run 生命周期
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS workflow_runs (
    id VARCHAR(64) PRIMARY KEY,
    workflow_name VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    thread_id VARCHAR(128),
    input_data JSONB,
    result JSONB,
    error TEXT,
    canceled VARCHAR(1) DEFAULT '0',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX idx_workflow_runs_thread_id ON workflow_runs(thread_id);
CREATE INDEX idx_workflow_runs_created_at ON workflow_runs(created_at);

-- ═══════════════════════════════════════════════════════════════════════════════
-- workflow_events 表：事件持久化（Event Store）
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS workflow_events (
    id VARCHAR(64) NOT NULL,
    workflow_id VARCHAR(64) NOT NULL,
    sequence INTEGER NOT NULL,
    category VARCHAR(32) NOT NULL,
    kind VARCHAR(64) NOT NULL,
    source VARCHAR(128),
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (workflow_id, sequence)
);

CREATE INDEX idx_workflow_events_workflow_id ON workflow_events(workflow_id);
CREATE INDEX idx_workflow_events_sequence ON workflow_events(workflow_id, sequence);
CREATE INDEX idx_workflow_events_created_at ON workflow_events(created_at);

COMMENT ON TABLE workflow_events IS 'Event Sourcing store for workflow events';
COMMENT ON COLUMN workflow_events.workflow_id IS 'References workflow_runs.id';
COMMENT ON COLUMN workflow_events.sequence IS 'Monotonically increasing sequence (like Kafka offset)';

-- ═══════════════════════════════════════════════════════════════════════════════
-- invite_codes 表：邀请码
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS invite_codes (
    code VARCHAR(32) PRIMARY KEY,
    hotel_id VARCHAR(64),
    user_name VARCHAR(128),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_invite_codes_expires ON invite_codes(expires_at);
CREATE INDEX idx_invite_codes_active ON invite_codes(is_active);

COMMENT ON TABLE invite_codes IS '商家邀请码，有效期 7 天';
COMMENT ON COLUMN invite_codes.expires_at IS '过期时间，到期后自动失效';

-- ═══════════════════════════════════════════════════════════════════════════════
-- invite_requests 表：邀请码申请记录（官网表单提交）
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS invite_requests (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(32) NOT NULL,
    name VARCHAR(128) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE invite_requests IS '官网邀请码申请记录，供客服手动发放邀请码';
