<template>
  <div class="flex flex-col h-[calc(100vh-120px)]">
    <!-- 连接状态 -->
    <div class="flex items-center gap-2 mb-4 px-2">
      <div class="w-2 h-2 rounded-full" :class="isConnected ? 'bg-emerald-500' : 'bg-red-500'" />
      <span class="text-xs text-slate-500">
        {{ isConnected ? '已连接' : '未连接' }}
      </span>
    </div>

    <!-- Agent 状态面板 -->
    <div v-if="isLoading && Object.keys(agentStatuses).length > 0" class="mb-4 px-2">
      <AgentStatus :statuses="agentStatuses" />
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="mb-4 px-4 py-3 bg-red-900/30 border border-red-700/50 rounded-lg text-red-400 text-sm">
      {{ error }}
    </div>

    <!-- 消息列表 -->
    <div class="flex-1 overflow-y-auto space-y-4 px-2 pb-4">
      <template v-if="messages.length === 0">
        <div class="flex flex-col items-center justify-center h-full text-slate-600">
          <div class="w-16 h-16 bg-slate-800 rounded-2xl flex items-center justify-center mb-4">
            <svg class="w-8 h-8 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <p class="text-lg font-medium mb-2">StockSage</p>
          <p class="text-sm">输入股票问题，多个AI Agent将协作分析</p>
          <div class="mt-6 flex flex-wrap gap-2 justify-center max-w-md">
            <button
              v-for="example in examples"
              :key="example"
              @click="handleSend(example)"
              class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded-full text-xs text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            >
              {{ example }}
            </button>
          </div>
        </div>
      </template>

      <ChatMessage
        v-for="(msg, index) in messages"
        :key="index"
        :role="msg.role"
        :content="msg.content"
      />

      <!-- 加载中提示 -->
      <div v-if="isLoading && !report" class="flex items-center gap-3 px-4 py-3">
        <div class="w-6 h-6 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
        <span class="text-sm text-slate-500">多Agent协作分析中...</span>
      </div>
    </div>

    <!-- 输入框 -->
    <div class="mt-4 pt-4 border-t border-slate-700/50">
      <ChatInput @send="handleSend" :disabled="isLoading || !isConnected" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useWebSocket } from '../../composables/useWebSocket'
import AgentStatus from '../Agent/AgentStatus.vue'
import ChatInput from './ChatInput.vue'
import ChatMessage from './ChatMessage.vue'

const sessionId = crypto.randomUUID()
const { isConnected, isLoading, agentStatuses, report, error, sendQuery } = useWebSocket(sessionId)

const messages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([])
const examples = [
  '分析一下贵州茅台',
  '宁德时代的技术面如何？',
  '对比比亚迪和特斯拉',
  '当前A股的风险评估',
]

const handleSend = (query: string) => {
  messages.value.push({ role: 'user', content: query })
  sendQuery(query)
}

watch(report, (newReport) => {
  if (newReport && !messages.value.some(m => m.role === 'assistant' && m.content === newReport)) {
    messages.value.push({ role: 'assistant', content: newReport })
  }
})
</script>
