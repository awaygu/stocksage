<template>
  <div v-if="entries.length > 0" class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-3">
    <p class="text-xs text-slate-500 mb-2">Agent 执行状态</p>
    <div class="flex flex-wrap gap-2">
      <div
        v-for="[key, status] in entries"
        :key="key"
        class="flex items-center gap-2 px-2.5 py-1.5 bg-slate-900/50 rounded-lg text-xs"
      >
        <span>{{ agentIcons[key] || '🔹' }}</span>
        <span class="text-slate-300">{{ agentLabels[key] || key }}</span>
        <div class="flex items-center gap-1">
          <div class="w-1.5 h-1.5 rounded-full" :class="[statusColor(status.status), status.status === 'running' ? 'animate-pulse' : '']" />
          <span class="text-slate-500">{{ statusText(status.status) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface AgentStatusItem {
  agent_id: string
  status: 'running' | 'completed' | 'failed' | 'skipped'
  data?: Record<string, unknown>
}

const props = defineProps<{
  statuses: Record<string, AgentStatusItem>
}>()

const entries = computed(() => Object.entries(props.statuses))

const agentLabels: Record<string, string> = {
  router: '意图解析',
  market_data: '市场数据',
  technical: '技术分析',
  fundamental: '基本面分析',
  news_sentiment: '新闻情感',
  macro: '宏观分析',
  industry: '行业分析',
  risk: '风险评估',
  synthesis: '综合决策',
  report: '报告生成',
}

const agentIcons: Record<string, string> = {
  router: '🧭',
  market_data: '📊',
  technical: '📈',
  fundamental: '📋',
  news_sentiment: '📰',
  macro: '🌍',
  industry: '🏭',
  risk: '⚠️',
  synthesis: '🧠',
  report: '📝',
}

const statusColor = (status: string) => {
  switch (status) {
    case 'running':
      return 'bg-amber-500'
    case 'completed':
      return 'bg-emerald-500'
    case 'failed':
      return 'bg-red-500'
    case 'skipped':
      return 'bg-slate-500'
    default:
      return 'bg-slate-600'
  }
}

const statusText = (status: string) => {
  switch (status) {
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    case 'skipped':
      return '跳过'
    default:
      return '待执行'
  }
}
</script>
