<script setup lang="ts">
import { computed } from 'vue'
import { AlertTriangle, CheckCircle2, Info, Clock } from 'lucide-vue-next'
import type { JobVerdict } from '@/types'

const props = defineProps<{
  verdict: JobVerdict
  violationsCount: number
  elapsedSec?: number
  limitations?: string | null
}>()

const isViolation = computed(() => props.verdict === 'violation')
</script>

<template>
  <div
    class="rounded-2xl p-6 sm:p-7 shadow-xl border flex flex-col gap-4"
    :class="
      isViolation
        ? 'bg-gradient-to-br from-red-500/15 via-[#0f1420] to-[#0f1420] border-red-500/35'
        : 'bg-gradient-to-br from-emerald-500/15 via-[#0f1420] to-[#0f1420] border-emerald-500/35'
    "
  >
    <div class="flex items-start gap-4 sm:gap-5">
      <div
        class="w-13 h-13 rounded-2xl flex items-center justify-center shrink-0 border"
        :class="
          isViolation
            ? 'bg-red-500/20 text-red-400 border-red-500/30'
            : 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
        "
      >
        <AlertTriangle v-if="isViolation" class="w-7 h-7" />
        <CheckCircle2 v-else class="w-7 h-7" />
      </div>

      <div class="flex-1 min-w-0">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-xl sm:text-2xl font-bold tracking-tight text-white">
            {{
              isViolation
                ? 'Обнаружены признаки возможных нарушений'
                : 'Нарушение не обнаружено'
            }}
          </h2>

          <div class="flex items-center gap-2">
            <span
              v-if="isViolation"
              class="text-xs font-bold px-3 py-1 rounded-full bg-red-500/20 text-red-300 border border-red-500/40"
            >
              Событий: {{ violationsCount }}
            </span>
            <span
              v-else
              class="text-xs font-bold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
            >
              Дисциплина соблюдена
            </span>

            <span v-if="elapsedSec" class="inline-flex items-center gap-1.5 text-xs text-slate-400 bg-white/5 border border-white/10 px-2.5 py-1 rounded-full">
              <Clock class="w-3 h-3" />
              <span>{{ elapsedSec.toFixed(1) }} с</span>
            </span>
          </div>
        </div>

        <p class="text-sm text-slate-300 mt-2 leading-relaxed">
          {{
            isViolation
              ? 'На видеозаписи идентифицированы действия кассира, расходящиеся с требованиями регламентов безопасности и кассовой дисциплины. Ознакомьтесь с таймкодами и кадрами-доказательствами ниже.'
              : 'В ходе автоматического локального анализа предоставленного видео отклонений от установленных правил кассовой дисциплины не выявлено.'
          }}
        </p>
      </div>
    </div>

    <!-- Limitations Notice (Section 7 of TASK.md) -->
    <div class="flex items-start gap-2 pt-3 border-t border-white/10 text-xs text-slate-400">
      <Info class="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
      <span>
        {{
          limitations ||
          'Результат работы сервиса является автоматической подсказкой для проверки человеком (сотрудником службы безопасности / контролером банка), а не окончательным дисциплинарным заключением.'
        }}
      </span>
    </div>
  </div>
</template>
