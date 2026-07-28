/**
 * Workflow API Client
 *
 * 职责：
 * 1. 创建 Workflow Run
 * 2. SSE 订阅事件
 * 3. 管理连接生命周期
 */

export class WorkflowClient {
  constructor(baseUrl = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
    this.eventSource = null;
    this.onEvent = null;
    this.onError = null;
    this.onComplete = null;
  }

  /**
   * 创建 Workflow Run
   * @param {string} reviewsContent - 评论内容
   * @param {string} threadId - 可选的 thread_id
   * @returns {Promise<{run_id: string, status: string, thread_id: string}>}
   */
  async createRun(reviewsContent, threadId = null) {
    const response = await fetch(`${this.baseUrl}/review/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        reviews_content: reviewsContent,
        thread_id: threadId,
      }),
    });

    if (!response.ok) {
      throw new Error(`Failed to create run: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * 获取 Run 状态
   * @param {string} runId
   * @returns {Promise<{run_id: string, status: string, result: any}>}
   */
  async getRunStatus(runId) {
    const response = await fetch(`${this.baseUrl}/review/run/${runId}`);

    if (!response.ok) {
      throw new Error(`Failed to get run status: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * 订阅事件流
   * @param {string} runId
   * @param {number} lastSequence - 断线恢复起点
   */
  subscribe(runId, lastSequence = 0) {
    const url = `${this.baseUrl}/review/stream/${runId}?last_sequence=${lastSequence}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (event) => {
      try {
        const workflowEvent = JSON.parse(event.data);

        if (this.onEvent) {
          this.onEvent(workflowEvent);
        }

        // workflow_completed 后自动关闭
        if (workflowEvent.kind === 'workflow_completed') {
          this.close();
          if (this.onComplete) {
            this.onComplete(workflowEvent);
          }
        }
      } catch (e) {
        console.error('Failed to parse event:', e);
      }
    };

    this.eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      if (this.onError) {
        this.onError(error);
      }
      // 自动重连由 EventSource 处理
    };

    this.eventSource.onopen = () => {
      console.log('SSE connected');
    };
  }

  /**
   * 关闭连接
   */
  close() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  /**
   * 运行工作流（创建 + 订阅）
   * @param {string} reviewsContent
   * @param {Object} callbacks
   * @param {Function} callbacks.onEvent - 事件回调
   * @param {Function} callbacks.onError - 错误回调
   * @param {Function} callbacks.onComplete - 完成回调
   * @returns {Promise<string>} runId
   */
  async run(reviewsContent, callbacks = {}) {
    this.onEvent = callbacks.onEvent || null;
    this.onError = callbacks.onError || null;
    this.onComplete = callbacks.onComplete || null;

    const { run_id } = await this.createRun(reviewsContent);
    this.subscribe(run_id);

    return run_id;
  }
}

/**
 * WorkflowClient 单例
 */
export const workflowClient = new WorkflowClient();
