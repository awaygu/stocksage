<template>
  <div class="flex gap-3" :class="isUser ? 'justify-end' : 'justify-start'">
    <div
      v-if="!isUser"
      class="shrink-0 w-7 h-7 rounded-full bg-accent text-white flex items-center justify-center text-[13px] font-semibold mt-0.5 select-none"
    >S</div>

    <div :class="isUser ? 'max-w-[80%]' : 'min-w-0 flex-1'">
      <div
        v-if="isUser"
        class="bg-surface rounded-[18px] px-4 py-2.5 text-[15px] leading-relaxed text-ink whitespace-pre-wrap break-words"
      >{{ content }}</div>

      <div
        v-else
        class="report animate-type-in break-words pt-1"
        :class="isLast ? 'min-h-[1.5rem]' : ''"
      >
        <VueMarkdown :source="content" />
        <span
          v-if="streaming"
          class="inline-block w-[0.55em] h-[1.05em] -mb-[0.15em] ml-[1px] bg-accent align-baseline animate-caret-blink"
          aria-hidden="true"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VueMarkdown from 'vue-markdown-render'

const props = withDefaults(defineProps<{
  role: 'user' | 'assistant'
  content: string
  isLast?: boolean
  streaming?: boolean
}>(), { isLast: false, streaming: false })

const isUser = computed(() => props.role === 'user')
</script>
