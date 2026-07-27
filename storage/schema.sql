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

-- 索引：按 workflow_id 快速查询 + 断线恢复
CREATE INDEX idx_workflow_events_workflow_id ON workflow_events(workflow_id);
CREATE INDEX idx_workflow_events_sequence ON workflow_events(workflow_id, sequence);
CREATE INDEX idx_workflow_events_created_at ON workflow_events(created_at);

COMMENT ON TABLE workflow_events IS 'Event Sourcing store for workflow events';
COMMENT ON COLUMN workflow_events.workflow_id IS 'References workflow_runs.id';
COMMENT ON COLUMN workflow_events.sequence IS 'Monotonically increasing sequence (like Kafka offset)';
