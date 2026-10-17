<script setup lang="ts">
import { computed } from 'vue'
import { Loader2, Video, Cpu, FileCheck } from 'lucide-vue-next'

const props = defineProps<{
  progress: number
  stage?: string
  elapsedSec?: number
}>()

const stageSteps = [
  { key: 'reading_video', label: 'Чтение кадров', icon: Video },
  { key: 'local_inference', label: 'Локальный AI-анализ', icon: Cpu },
  { key: 'preparing_evidence', label: 'Подготовка доказательств', icon: FileCheck },
]

const currentStepIndex = computed(() => {
  if (props.stage === 'reading_video') return 0
  if (props.stage === 'local_inference') return 1
  if (props.stage === 'preparing_evidence') return 2
  return 1
})
</script>

<template>
  <div class="bg-[#0f1420] border border-[#a51c30]/40 rounded-2xl p-6 sm:p-7 shadow-xl shadow-[#a51c30]/10 flex flex-col gap-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3.5">
        <div class="w-10 h-10 rounded-xl bg-[#a51c30]/20 text-red-400 flex items-center justify-center shrink-0">
          <Loader2 class="w-5 h-5 animate-spin" />
        </div>
        <div>
          <h3 class="text-base font-bold text-white">Выполняется локальная проверка кассы…</h3>
          <p class="text-xs text-slate-400">
            Нейросетевые модели анализируют видеозапись в локальном контуре без передачи данных в интернет.
          </p>
        </div>
      </div>

      <div v-if="elapsedSec !== undefined" class="text-xs bg-white/5 border border-white/10 px-3 py-1 rounded-full text-slate-300">
        Прошло: <strong class="text-white">{{ elapsedSec.toFixed(1) }} с</strong>
      </div>
    </div>

    <!-- Progress Bar -->
    <div class="flex flex-col gap-1.5">
      <div class="w-full h-2.5 bg-white/10 rounded-full overflow-hidden border border-white/10">
        <div
          class="h-full bg-gradient-to-r from-[#a51c30] to-indigo-500 rounded-full transition-all duration-300"
          :style="{ width: `${progress}%` }"
        />
      </div>
      <div class="flex items-center justify-between text-xs">
        <span class="text-slate-400">Этап: <strong class="text-slate-200">{{ stage || 'Обработка' }}</strong></span>
        <span class="font-mono font-semibold text-slate-200">{{ progress }}%</span>
      </div>
    </div>

    <!-- Stages Pipeline -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
      <div
        v-for="(step, idx) in stageSteps"
        :key="step.key"
        class="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border text-xs font-medium transition-all"
        :class="{
          'border-emerald-500/40 bg-emerald-500/10 text-emerald-300': idx < currentStepIndex,
          'border-[#a51c30]/60 bg-[#a51c30]/20 text-white shadow-md shadow-[#a51c30]/20': idx === currentStepIndex,
          'border-white/10 bg-white/[0.02] text-slate-500 opacity-60': idx > currentStepIndex,
        }"
      >
        <component :is="step.icon" class="w-4 h-4 shrink-0" />
        <span>{{ step.label }}</span>
      </div>
    </div>
  </div>
</template>
