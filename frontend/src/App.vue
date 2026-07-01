<template>
  <div class="min-h-screen bg-slate-900 text-slate-200">
    <header class="border-b border-slate-700/50 bg-slate-800/50 backdrop-blur-sm">
      <div class="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          </div>
          <div>
            <h1 class="text-lg font-bold text-white">StockSage</h1>
            <p class="text-xs text-slate-400">多Agent股票研究系统</p>
          </div>
        </div>
        <div class="text-xs text-slate-500">
          v1.0.0 · MVP
        </div>
      </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 py-6">
      <ChatContainer />
    </main>
  </div>
</template>

<script setup lang="ts">
import ChatContainer from './components/Chat/ChatContainer.vue'
</script>
