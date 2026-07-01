import { onMounted, onUnmounted, ref } from 'vue'

export interface AgentStatus {
  agent_id: string
  status: 'running' | 'completed' | 'failed' | 'skipped'
  data?: Record<string, unknown>
}

export interface WSMessage {
  type: 'agent_status' | 'report' | 'status' | 'error' | 'stream_chunk'
  agent_id?: string
  status?: string
  content?: string
  error?: string
  data?: Record<string, unknown>
  session_id?: string
}

export function useWebSocket(sessionId: string) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isLoading = ref(false)
  const agentStatuses = ref<Record<string, AgentStatus>>({})
  const report = ref('')
  const error = ref('')

  const connect = () => {
    // 使用相对 URL，让 Vite dev server / 生产环境统一代理 WebSocket 请求
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/stream/${sessionId}`
    const socket = new WebSocket(wsUrl)
    ws.value = socket

    socket.onopen = () => {
      isConnected.value = true
      error.value = ''
    }

    socket.onclose = () => {
      isConnected.value = false
    }

    socket.onerror = () => {
      error.value = 'WebSocket连接失败，请检查后端服务是否运行'
      isConnected.value = false
    }

    socket.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data)
        handleMessage(msg)
      } catch {
        // 忽略非JSON消息
      }
    }
  }

  const handleMessage = (msg: WSMessage) => {
    switch (msg.type) {
      case 'status':
        if (msg.status === 'started') {
          isLoading.value = true
          report.value = ''
          agentStatuses.value = {}
        } else if (msg.status === 'completed') {
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

      case 'report':
        if (msg.content) {
          report.value = msg.content
        }
        break

      case 'error':
        error.value = msg.error || '未知错误'
        isLoading.value = false
        break
    }
  }

  const sendQuery = (query: string) => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      isLoading.value = true
      report.value = ''
      agentStatuses.value = {}
      error.value = ''
      ws.value.send(JSON.stringify({ type: 'query', content: query }))
    } else {
      error.value = 'WebSocket未连接，请刷新页面重试'
    }
  }

  onMounted(connect)
  onUnmounted(() => {
    ws.value?.close()
  })

  return {
    isConnected,
    isLoading,
    agentStatuses,
    report,
    error,
    sendQuery,
  }
}
