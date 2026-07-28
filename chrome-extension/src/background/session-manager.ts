/**
 * Workflow Session Manager
 *
 * 管理多个并行的 Workflow Session
 * 职责：
 * - 创建/获取/删除 Session
 * - 更新 lastSequence（断线恢复用）
 * - 状态持久化（chrome.storage.session）
 *
 * Session 数据结构：
 * {
 *   runId: string,           // 后端返回的 run_id
 *   tabId: number,            // 关联的 Tab ID
 *   status: string,          // pending/running/completed/failed/cancelled
 *   lastSequence: number,     // 最后消费的事件序列
 *   createdAt: number,        // 创建时间戳
 *   updatedAt: number,        // 更新时间戳
 *   reconnectCount: number,   // 重连次数
 * }
 */

// Session 状态枚举
export const SessionStatus = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  CANCELLED: 'cancelled',
}

// Storage Key
const SESSION_STORE_KEY = 'workflow_sessions'

class WorkflowSessionManager {
  constructor() {
    // runId -> Session
    this._sessions = {}
    // tabId -> runId 索引
    this._tabIndex = {}
    // 初始化的 Promise
    this._initPromise = null
  }

  /**
   * 初始化（从 storage 恢复）
   */
  async init() {
    if (this._initPromise) {
      return this._initPromise
    }

    this._initPromise = this._restore()
    return this._initPromise
  }

  /**
   * 恢复 Session（Service Worker 启动时）
   */
  async _restore() {
    try {
      const result = await chrome.storage.session.get(SESSION_STORE_KEY)
      const data = result[SESSION_STORE_KEY]

      if (data) {
        this._sessions = data.sessions || {}
        this._tabIndex = data.tabIndex || {}
        console.log('[SessionManager] Restored sessions:', Object.keys(this._sessions).length)
      }
    } catch (error) {
      console.error('[SessionManager] Failed to restore:', error)
    }
  }

  /**
   * 持久化到 storage
   */
  async _persist() {
    try {
      await chrome.storage.session.set({
        [SESSION_STORE_KEY]: {
          sessions: this._sessions,
          tabIndex: this._tabIndex,
        },
      })
    } catch (error) {
      console.error('[SessionManager] Failed to persist:', error)
    }
  }

  /**
   * 创建 Session
   */
  async createSession(runId, tabId) {
    const now = Date.now()

    const session = {
      runId,
      tabId,
      status: SessionStatus.PENDING,
      lastSequence: 0,
      createdAt: now,
      updatedAt: now,
      reconnectCount: 0,
    }

    this._sessions[runId] = session
    this._tabIndex[tabId] = runId

    await this._persist()

    console.log('[SessionManager] Session created:', runId)
    return session
  }

  /**
   * 获取 Session
   */
  getSession(runId) {
    return this._sessions[runId] || null
  }

  /**
   * 通过 Tab ID 获取 Session
   */
  getSessionByTab(tabId) {
    const runId = this._tabIndex[tabId]
    if (runId) {
      return this._sessions[runId] || null
    }
    return null
  }

  /**
   * 更新 Session 状态
   */
  async updateStatus(runId, status) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    session.status = status
    session.updatedAt = Date.now()

    await this._persist()

    console.log('[SessionManager] Status updated:', runId, status)
    return session
  }

  /**
   * 更新 lastSequence（断线恢复用）
   */
  async updateSequence(runId, sequence) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    if (sequence > session.lastSequence) {
      session.lastSequence = sequence
      session.updatedAt = Date.now()
      await this._persist()
    }

    return session
  }

  /**
   * 增加重连次数
   */
  async incrementReconnectCount(runId) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    session.reconnectCount += 1
    session.updatedAt = Date.now()
    await this._persist()

    return session
  }

  /**
   * 重置重连次数
   */
  async resetReconnectCount(runId) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    session.reconnectCount = 0
    await this._persist()

    return session
  }

  /**
   * 关闭 Session（状态标记为 closed，但不删除）
   */
  async closeSession(runId) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    // 更新索引
    delete this._tabIndex[session.tabId]

    // 标记为已关闭
    session.status = SessionStatus.CANCELLED
    session.updatedAt = Date.now()
    session.closedAt = Date.now()

    await this._persist()

    console.log('[SessionManager] Session closed:', runId)
    return session
  }

  /**
   * 删除 Session（彻底清理）
   */
  async removeSession(runId) {
    const session = this._sessions[runId]
    if (session) {
      delete this._tabIndex[session.tabId]
    }

    delete this._sessions[runId]
    await this._persist()

    console.log('[SessionManager] Session removed:', runId)
    return true
  }

  /**
   * 标记 Session 为完成
   */
  async markCompleted(runId, result = null) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    session.status = SessionStatus.COMPLETED
    session.result = result
    session.completedAt = Date.now()
    session.updatedAt = Date.now()

    await this._persist()

    console.log('[SessionManager] Session completed:', runId)
    return session
  }

  /**
   * 标记 Session 为失败
   */
  async markFailed(runId, error = null) {
    const session = this._sessions[runId]
    if (!session) {
      return null
    }

    session.status = SessionStatus.FAILED
    session.error = error
    session.failedAt = Date.now()
    session.updatedAt = Date.now()

    await this._persist()

    console.log('[SessionManager] Session failed:', runId)
    return session
  }

  /**
   * 列出所有 Session
   */
  listSessions() {
    return Object.values(this._sessions)
  }

  /**
   * 获取所有 Running 状态的 Session
   */
  getRunningSessions() {
    return Object.values(this._sessions).filter(
      (s) => s.status === SessionStatus.RUNNING || s.status === SessionStatus.PENDING
    )
  }

  /**
   * 获取 Session 数量
   */
  getCount() {
    return Object.keys(this._sessions).length
  }

  /**
   * 清理过期 Session（超过 24 小时的 completed/failed）
   */
  async cleanup(maxAgeHours = 24) {
    const now = Date.now()
    const maxAge = maxAgeHours * 60 * 60 * 1000

    for (const [runId, session] of Object.entries(this._sessions)) {
      const completedAt = session.completedAt || session.failedAt
      if (completedAt && now - completedAt > maxAge) {
        delete this._sessions[runId]
        if (session.tabId) {
          delete this._tabIndex[session.tabId]
        }
      }
    }

    await this._persist()
    console.log('[SessionManager] Cleanup completed, remaining:', this.getCount())
  }
}

// 单例
let _instance = null

export function getSessionManager() {
  if (!_instance) {
    _instance = new WorkflowSessionManager()
  }
  return _instance
}
