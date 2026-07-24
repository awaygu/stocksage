<template>
  <div class="min-h-screen flex flex-col bg-bg">
    <header class="sticky top-0 z-30 bg-bg/80 backdrop-blur-md border-b border-line">
      <div class="max-w-3xl mx-auto px-5 sm:px-8 h-14 flex items-center justify-between gap-4">
        <span class="text-[15px] font-semibold tracking-tight text-ink">
          StockSage
        </span>

        <div class="flex items-center gap-1.5 text-[13px] shrink-0" :class="connected ? 'text-ink-soft' : 'text-err'">
          <span
            class="w-1.5 h-1.5 rounded-full"
            :class="connected ? 'bg-accent' : 'bg-err'"
          />
          {{ connected ? '已连接' : '未连接' }}
        </div>
      </div>
    </header>

    <main class="flex-1 w-full max-w-3xl self-center px-5 sm:px-8">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
defineProps<{ connected: boolean }>()
</script>
