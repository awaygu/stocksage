<template>
  <div v-if="stages.length > 0" class="animate-node-enter">
    <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar py-2">
      <template v-for="(stage, i) in stages" :key="stage.id">
        <div
          class="flex items-center gap-1.5 flex-shrink-0"
          :class="statusOf(stage) === 'skipped' ? 'opacity-40' : ''"
        >
          <span
            class="w-2 h-2 rounded-full flex-shrink-0"
            :class="[dotClass(stage), isRunning(stage) ? 'pulse-running' : '']"
          />
          <span
            class="text-[12px] leading-none whitespace-nowrap"
            :class="labelClass(stage)"
          >{{ stage.label }}</span>
        </div>

        <span
          v-if="i < stages.length - 1"
          class="flex-shrink-0 h-px w-3"
          :class="statusOf(stage) === 'completed' ? 'bg-accent/40' : 'bg-line'"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { STAGES, type StageMeta } from '../../composables/agents'

interface AgentStatusItem {
  agent_id: string
  status: 'running' | 'completed' | 'failed' | 'skipped'
  data?: Record<string, unknown>
}

const props = defineProps<{
  statuses: Record<string, AgentStatusItem>
}>()

const stages = computed(() =>
  STAGES.filter((s) => props.statuses[s.id]?.status !== undefined),
)

const statusOf = (stage: StageMeta) => props.statuses[stage.id]?.status
const isRunning = (stage: StageMeta) => statusOf(stage) === 'running'

const dotClass = (stage: StageMeta) => {
  switch (statusOf(stage)) {
    case 'running': return 'bg-accent'
    case 'completed': return 'bg-accent'
    case 'failed': return 'bg-err'
    case 'skipped': return 'bg-ink-faint'
    default: return 'bg-line'
  }
}

const labelClass = (stage: StageMeta) => {
  const st = statusOf(stage)
  if (st === 'completed') return 'text-ink'
  if (st === 'running') return 'text-ink font-medium'
  if (st === 'failed') return 'text-err'
  return 'text-ink-faint'
}
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
