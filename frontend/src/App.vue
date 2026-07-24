<template>
  <AppShell :connected="isConnected">
    <ChatContainer
      :is-connected="isConnected"
      :is-loading="isLoading"
      :agent-statuses="agentStatuses"
      :report="report"
      :error="error"
      :send-query="sendQuery"
    />
  </AppShell>
</template>

<script setup lang="ts">
import AppShell from './components/App/AppShell.vue'
import ChatContainer from './components/Chat/ChatContainer.vue'
import { useChatSession } from './composables/useSSE'

// SSE 会话生于 app 根:报告流需跨 ChatContainer 局部消息状态留存,
// 顶栏连接状态也读同一来源。每次 sendQuery 新建一条 SSE 连接,
// 故无需 per-page-load 的稳定 session id(WS 时代的 refresh-reset 限制不再适用)。
const {
  isConnected,
  isLoading,
  agentStatuses,
  report,
  error,
  sendQuery,
} = useChatSession()
</script>
