/**
 * Workflow State Store
 *
 * 管理当前工作流的状态。
 * 类型定义明确了跨模块消息协议的字段。
 */

// ── 公共类型 ───────────────────────────────────────────────────────────────

export type WorkflowStatus = 'idle' | 'running' | 'completed' | 'failed';

export interface WorkflowEvent {
  // 基类（与后端 WorkflowEvent 对齐）
  id?: string;
  workflow_id?: string;
  sequence?: number;
  category?: string;
  kind: string;
  display_name?: string | null;
  timestamp?: number;
  source?: string | null;

  // TokenDeltaEvent
  delta?: string;

  // NodeStartedEvent / NodeCompletedEvent
  node_name?: string;

  // NodeFailedEvent / WorkflowFailedEvent
  error?: string;

  // StateUpdatedEvent
  state?: Record<string, unknown>;

  // WorkflowCompletedEvent
  result?: Record<string, unknown> | null;

  // CustomEvent
  event_type?: string;
  data?: Record<string, unknown>;

  // ToolCallEvent
  tool_name?: string;
  tool_input?: Record<string, unknown>;
}

export interface WorkflowStateSnapshot {
  runId: string | null;
  status: WorkflowStatus;
  replyContent: string;
  hotelId: string | null;
  error: string | null;
  lastSequence: number;
  events: WorkflowEvent[];
}

type UpdateCallback = (state: WorkflowStateSnapshot) => void;

// ── 常量 ───────────────────────────────────────────────────────────────────

const State = {
  IDLE: 'idle' as WorkflowStatus,
  RUNNING: 'running' as WorkflowStatus,
  COMPLETED: 'completed' as WorkflowStatus,
  FAILED: 'failed' as WorkflowStatus,
};

const EventKind = {
  WORKFLOW_STARTED: 'workflow_started',
  WORKFLOW_COMPLETED: 'workflow_completed',
  WORKFLOW_FAILED: 'workflow_failed',
  NODE_STARTED: 'node_started',
  NODE_COMPLETED: 'node_completed',
  TOKEN_DELTA: 'token_delta',
  CUSTOM_EVENT: 'custom_event',
};

// ── Store ──────────────────────────────────────────────────────────────────

interface InternalState {
  runId: string | null;
  status: WorkflowStatus;
  replyContent: string;
  hotelId: string | null;
  error: string | null;
  lastSequence: number;
  events: WorkflowEvent[];
  onUpdate: UpdateCallback | null;
}

let _state: InternalState = {
  runId: null,
  status: State.IDLE,
  replyContent: '',
  hotelId: null,
  error: null,
  lastSequence: 0,
  events: [],
  onUpdate: null,
};

function notifyUpdate(): void {
  if (_state.onUpdate) {
    const snapshot: WorkflowStateSnapshot = {
      runId: _state.runId,
      status: _state.status,
      replyContent: _state.replyContent,
      hotelId: _state.hotelId,
      error: _state.error,
      lastSequence: _state.lastSequence,
      events: [..._state.events],
    };
    _state.onUpdate(snapshot);
  }
}

export interface WorkflowStore {
  getState(): WorkflowStateSnapshot;
  getReply(): string;
  setReply(content: string): void;
  getStatus(): WorkflowStatus;
  getRunId(): string | null;
  getError(): string | null;
  isRunning(): boolean;
  setUpdateCallback(cb: UpdateCallback): void;
  reset(): void;
  startRun(runId: string | null, hotelId?: string): void;
  handleEvent(event: WorkflowEvent): void;
  setError(error: string): void;
}

export function createStore(): WorkflowStore {
  return {
    getState: () => ({
      runId: _state.runId,
      status: _state.status,
      replyContent: _state.replyContent,
      hotelId: _state.hotelId,
      error: _state.error,
      lastSequence: _state.lastSequence,
      events: [..._state.events],
    }),

    getReply: () => _state.replyContent,

    setReply: (content: string) => {
      _state.replyContent = content;
      notifyUpdate();
    },

    getStatus: () => _state.status,

    getRunId: () => _state.runId,

    getError: () => _state.error,

    isRunning: () => _state.status === State.RUNNING,

    setUpdateCallback: (cb: UpdateCallback) => {
      _state.onUpdate = cb;
    },

    reset: () => {
      _state.runId = null;
      _state.status = State.IDLE;
      _state.replyContent = '';
      _state.hotelId = null;
      _state.error = null;
      _state.lastSequence = 0;
      _state.events = [];
      notifyUpdate();
    },

    startRun: (runId: string | null, hotelId?: string) => {
      _state.runId = runId;
      _state.status = State.RUNNING;
      _state.replyContent = '';
      if (hotelId !== undefined) _state.hotelId = hotelId;
      _state.error = null;
      _state.events = [];
      notifyUpdate();
    },

    handleEvent: (event: WorkflowEvent) => {
      _state.events.push(event);
      _state.lastSequence = event.sequence || 0;

      if (event.kind === EventKind.TOKEN_DELTA) {
        _state.replyContent += (event.delta as string) || '';
      }

      switch (event.kind) {
        case EventKind.WORKFLOW_COMPLETED: {
          _state.status = State.COMPLETED;
          break;
        }
        case EventKind.WORKFLOW_FAILED:
          _state.status = State.FAILED;
          _state.error = (event.error as string) || 'Unknown error';
          break;
      }

      notifyUpdate();
    },

    setError: (error: string) => {
      _state.status = State.FAILED;
      _state.error = error;
      notifyUpdate();
    },
  };
}

export const store = createStore();
