<template>
  <div class="flex gap-3" :class="isUser ? 'flex-row-reverse' : ''">
    <!-- Avatar -->
    <div class="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center" :class="isUser ? 'bg-emerald-500/20' : 'bg-blue-500/20'">
      <svg v-if="isUser" class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
      <svg v-else class="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    </div>

    <!-- Content -->
    <div class="max-w-[85%]" :class="isUser ? 'items-end' : 'items-start'">
      <div class="px-4 py-3 rounded-xl text-sm" :class="isUser ? 'bg-emerald-500/20 text-emerald-100' : 'bg-slate-800 text-slate-300'">
        <p v-if="isUser">{{ content }}</p>
        <div v-else class="prose prose-invert prose-sm max-w-none">
          <VueMarkdown :source="content" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VueMarkdown from 'vue-markdown-render'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
}>()

const isUser = computed(() => props.role === 'user')
</script>
