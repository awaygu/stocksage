<template>
  <form @submit.prevent="handleSubmit">
    <div
      class="bg-white border border-line rounded-2xl shadow-[0_1px_2px_rgba(0,0,0,0.06)] transition-all focus-within:border-accent/40 focus-within:ring-1 focus-within:ring-accent/15 focus-within:shadow-md"
    >
      <textarea
        ref="textareaRef"
        v-model="input"
        @keydown="handleKeyDown"
        @input="autoResize"
        :disabled="disabled"
        :placeholder="disabled ? '' : '给 StockSage 发送消息'"
        rows="1"
        class="w-full bg-transparent border-0 resize-none text-lg leading-8 text-ink placeholder-ink-soft focus:outline-none max-h-40 min-h-[36px] px-5 pt-5 pb-3"
        style="overflow: hidden;"
      />

      <div class="flex items-end justify-between mt-4">
        <div class="flex items-center gap-2 ml-2 mb-2">
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-2 py-0 rounded-full text-[13px] font-medium border transition-colors duration-200"
            :class="deepMode
              ? 'bg-accent-wash border-accent/30 text-accent'
              : 'bg-surface border-line text-ink-soft hover:bg-line/60 hover:text-ink'"
            @click="deepMode = !deepMode"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 3a9 9 0 100 18 9 9 0 000-18z" />
              <path d="M12 8v4l3 3" />
            </svg>
            深度研究
          </button>
          <button
            type="button"
            class="inline-flex items-center gap-1.5 px-2 py-0 rounded-full text-[13px] font-medium border transition-colors duration-200"
            :class="webMode
              ? 'bg-accent-wash border-accent/30 text-accent'
              : 'bg-surface border-line text-ink-soft hover:bg-line/60 hover:text-ink'"
            @click="webMode = !webMode"
          >
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20" />
              <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
            </svg>
            联网搜索
          </button>
        </div>

        <button
          type="submit"
          :disabled="disabled || !input.trim()"
          :title="input.trim() ? '发送 (Enter)' : '输入问题后发送'"
          class="w-10 h-10 rounded-full flex items-center justify-center transition-colors disabled:bg-line disabled:text-ink-faint bg-accent text-white hover:bg-accent-soft shrink-0 mr-2 mb-2"
        >
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19V5M5 12l7-7 7 7" />
          </svg>
        </button>
      </div>
    </div>
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

const deepMode = ref(false)
const webMode = ref(false)

const handleSubmit = () => {
  if (input.value.trim() && !props.disabled) {
    emit('send', input.value.trim())
    input.value = ''
    deepMode.value = false
    webMode.value = false
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
