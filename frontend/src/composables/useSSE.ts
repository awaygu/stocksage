import { ref } from 'vue'

export interface AgentStatus {
  agent_id: string
  status: 'running' | 'completed' | 'failed' | 'skipped'
  data?: Record<string, unknown>
}

// 与后端 /api/chat/stream 的 event_bus 透传帧一一对应(见 backend/api/chat.py)
export interface SSEMessage {
  type: 'agent_status' | 'stream_chunk' | 'status' | 'error'
  agent_id?: string
  status?: string
  content?: string
  error?: string
  data?: Record<string, unknown>
  session_id?: string
}

/**
 * SSE 流式会话:每条 query 新开一个 POST /api/chat/stream 连接,
 * 用 ReadableStream 逐块解析 SSE 帧。一条连接承载 agent_status 与
 * 报告 token 流(后端桥接 event_bus)。无长连保活需求,故不做重连。
 */
export function useChatSession() {
  const isConnected = ref(false)
  const isLoading = ref(false)
  const agentStatuses = ref<Record<string, AgentStatus>>({})
  const report = ref('')
  const error = ref('')

  // 启动时探活一次后端,驱动顶栏连接状态
  void checkHealth()

  async function checkHealth() {
    try {
      const resp = await fetch('/health')
      isConnected.value = resp.ok
    } catch {
      isConnected.value = false
    }
  }

  const handleMessage = (msg: SSEMessage) => {
    switch (msg.type) {
      case 'status':
        if (msg.status === 'completed') {
          isLoading.value = false
        }
        break

      case 'agent_status':
        if (msg.agent_id && msg.status) {
          agentStatuses.value[msg.agent_id] = {
            agent_id: msg.agent_id,
            status: msg.status as AgentStatus['status'],
            data: msg.data,
          }
        }
        break

      case 'stream_chunk':
        // 报告 token 增量累积,前端逐字渲染
        if (msg.content) report.value += msg.content
        break

      case 'error':
        error.value = msg.error || '未知错误'
        isLoading.value = false
        break
    }
  }

  async function sendQuery(query: string) {
    isLoading.value = true
    report.value = ''
    agentStatuses.value = {}
    error.value = ''

    const sessionId = crypto.randomUUID()
    let resp: Response
    try {
      resp = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
      })
    } catch {
      error.value = '无法连接后端,请检查服务是否在 :8000 运行'
      isLoading.value = false
      return
    }

    if (!resp.ok || !resp.body) {
      error.value = `请求失败(${resp.status})`
      isLoading.value = false
      return
    }

    const reader = resp.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })

        // SSE 事件以空行(\n\n)分隔;末段可能不完整,留到下次拼接
        const parts = buf.split('\n\n')
        buf = parts.pop() ?? ''

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith('data:')) continue
          const data = line.slice(5).trim()
          if (data === '[DONE]') {
            isLoading.value = false
            return
          }
          try {
            handleMessage(JSON.parse(data))
          } catch {
            // 忽略非 JSON 帧
          }
        }
      }
    } finally {
      // 连接中断兜底:标记结束
      isLoading.value = false
    }
  }

  return {
    isConnected,
    isLoading,
    agentStatuses,
    report,
    error,
    sendQuery,
  }
}
