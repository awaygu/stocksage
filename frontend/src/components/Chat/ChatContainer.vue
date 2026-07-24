<template>
  <div class="flex flex-col h-[calc(100vh-3.5rem-1.5rem)]">
    <div v-if="hasActivity" class="mb-2 border-b border-line">
      <AgentStatus :statuses="agentStatuses" />
    </div>

    <div
      v-if="error"
      class="mb-3 flex gap-3 bg-err-wash border-l-2 border-err px-3.5 py-2.5 rounded-r-[2px]"
    >
      <svg class="w-4 h-4 text-err flex-shrink-0 mt-px" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <div class="text-[13px] leading-snug">
        <p class="text-err font-medium">{{ error }}</p>
        <p class="text-ink-soft mt-0.5 text-[12px]">检查后端服务是否在 <span class="font-mono">:8000</span> 运行，或刷新页面重试。</p>
      </div>
    </div>

    <div ref="scrollRef" class="flex-1 overflow-y-auto -mx-1 px-1">
      <template v-if="messages.length === 0 && !isLoading">
        <div class="h-full flex flex-col justify-center items-center text-center w-full">
          <div class="w-7 h-7 rounded-full bg-accent text-white flex items-center justify-center text-[13px] font-semibold mb-5 select-none">S</div>
          <h1 class="text-[28px] sm:text-[32px] leading-tight text-ink mb-2 tracking-tight font-semibold">
            今天想看哪只股票？
          </h1>
          <p class="text-[15px] text-ink-soft mb-8 max-w-md leading-relaxed">
            多个分析师会沿依赖关系协作——从意图解析到报告生成，逐站给出结论。
          </p>
          <div class="w-full max-w-2xl mb-10">
            <ChatInput :disabled="!isConnected" @send="handleSend" />
          </div>

          <div class="flex flex-wrap items-center justify-center gap-2 max-w-2xl">
            <button
              v-for="ex in examples"
              :key="ex.text"
              @click="handleSend(ex.text)"
              :disabled="!isConnected"
              class="group inline-flex items-center gap-1.5 rounded-full border border-line bg-bg px-3.5 py-1.5 text-[13px] text-ink-soft hover:border-accent/40 hover:text-ink disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <span class="font-mono text-[10px] text-accent/70 tracking-wider">{{ ex.tag }}</span>
              <span class="w-px h-3 bg-line group-hover:bg-accent/40 transition-colors" />
              <span>{{ ex.text }}</span>
            </button>
          </div>
        </div>
      </template>

      <div v-else class="space-y-6 py-1">
        <ChatMessage
          v-for="(msg, i) in messages"
          :key="i"
          :role="msg.role"
          :content="msg.content"
          :is-last="i === messages.length - 1 && msg.role === 'assistant'"
          :streaming="i === messages.length - 1 && msg.role === 'assistant' && isStreamingLast"
        />

        <div v-if="isLoading && !report" class="flex gap-3 justify-start">
          <div class="shrink-0 w-7 h-7 rounded-full bg-accent text-white flex items-center justify-center text-[13px] font-semibold mt-0.5 select-none">S</div>
          <div class="flex items-center gap-2 text-[15px] text-ink-soft">
            <span class="w-1.5 h-1.5 rounded-full bg-accent/60 animate-bounce" />
            <span class="w-1.5 h-1.5 rounded-full bg-accent/60 animate-bounce [animation-delay:0.15s]" />
            <span class="w-1.5 h-1.5 rounded-full bg-accent/60 animate-bounce [animation-delay:0.3s]" />
            <span class="ml-1">分析中…</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="messages.length > 0 || isLoading" class="pt-5 pb-6">
      <ChatInput :disabled="isLoading || !isConnected" @send="handleSend" />
      <p class="mt-3 text-center text-[11px] text-ink-faint">
        内容由 AI 生成，不构成投资建议。请独立核实关键数据。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import AgentStatus from '../Agent/AgentStatus.vue'
import ChatInput from './ChatInput.vue'
import ChatMessage from './ChatMessage.vue'

interface AgentStatusItem {
  agent_id: string
  status: 'running' | 'completed' | 'failed' | 'skipped'
  data?: Record<string, unknown>
}

const props = defineProps<{
  isConnected: boolean
  isLoading: boolean
  agentStatuses: Record<string, AgentStatusItem>
  report: string
  error: string
  sendQuery: (q: string) => void
}>()

const messages = ref<Array<{ role: 'user' | 'assistant'; content: string }>>([])
const scrollRef = ref<HTMLElement | null>(null)

const examples = [
  { text: '分析一下贵州茅台', tag: '综合' },
  { text: '宁德时代的技术面如何？', tag: '技术' },
  { text: '对比比亚迪和特斯拉', tag: '行业' },
  { text: '当前 A 股的风险评估', tag: '风险' },
]

const hasActivity = computed(() => Object.keys(props.agentStatuses).length > 0)

const streamingText = ref('')
const finalizedReport = ref('')
const queue = ref('')
let typewriter: ReturnType<typeof setInterval> | null = null
const TICK_MS = 16

function charsForQueue(qlen: number): number {
  if (qlen <= 8) return 1
  if (qlen <= 32) return 2
  if (qlen <= 96) return 4
  return 8
}

function stopTypewriter() {
  if (typewriter) {
    clearInterval(typewriter)
    typewriter = null
  }
}

function pumpTick() {
  if (!queue.value) {
    stopTypewriter()
    return
  }
  const n = charsForQueue(queue.value.length)
  streamingText.value += queue.value.slice(0, n)
  queue.value = queue.value.slice(n)
  nextTick(scrollToBottom)
}

watch(
  () => props.report,
  (newReport, oldReport) => {
    if (newReport) finalizedReport.value = newReport

    if (!newReport) {
      if (oldReport) {
        stopTypewriter()
        queue.value = ''
        const lastAssistant = [...messages.value].reverse().find((m) => m.role === 'assistant')
        if (lastAssistant) lastAssistant.content = finalizedReport.value
        streamingText.value = ''
      }
      return
    }
    if (!oldReport) {
      messages.value.push({ role: 'assistant', content: '' })
    }
    const consumed = streamingText.value.length + queue.value.length
    const fresh = newReport.slice(consumed)
    if (fresh) queue.value += fresh
    if (!typewriter && queue.value) {
      typewriter = setInterval(pumpTick, TICK_MS)
    }
  },
)

const isStreamingLast = computed(
  () => queue.value.length > 0 || (props.isLoading && !!props.report),
)

watch(streamingText, (text) => {
  const last = messages.value[messages.value.length - 1]
  if (last && last.role === 'assistant') {
    last.content = text
  }
})

watch(
  () => messages.value.length,
  () => nextTick(scrollToBottom),
)

onUnmounted(stopTypewriter)

function scrollToBottom() {
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function handleSend(query: string) {
  messages.value.push({ role: 'user', content: query })
  props.sendQuery(query)
  nextTick(scrollToBottom)
}
</script>
