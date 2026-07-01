<template>
  <form @submit.prevent="handleSubmit" class="relative">
    <textarea
      ref="textareaRef"
      v-model="input"
      @keydown="handleKeyDown"
      @input="autoResize"
      :disabled="disabled"
      :placeholder="disabled ? '分析中...' : '输入股票问题，如分析一下贵州茅台...'"
      class="w-full px-4 py-3 pr-14 bg-slate-800 border border-slate-700/50 rounded-xl text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 resize-none min-h-[52px] max-h-32 disabled:opacity-50"
      rows="1"
      style="height: auto; overflow: hidden;"
    />
    <button
      type="submit"
      :disabled="disabled || !input.trim()"
      class="absolute right-3 top-1/2 -translate-y-1/2 w-8 h-8 bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-lg flex items-center justify-center transition-colors"
    >
      <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
      </svg>
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const input = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const handleSubmit = () => {
  if (input.value.trim() && !props.disabled) {
    emit('send', input.value.trim())
    input.value = ''
    autoResize()
  }
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSubmit()
  }
}

const autoResize = () => {
  const el = textareaRef.value
  if (el) {
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  }
}
</script>
