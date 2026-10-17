<script setup lang="ts">
import { ref, computed } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import VideoUploadCard from '@/components/monitor/VideoUploadCard.vue'
import ProcessingCard from '@/components/monitor/ProcessingCard.vue'
import VerdictBanner from '@/components/monitor/VerdictBanner.vue'
import VideoPlayerCard from '@/components/monitor/VideoPlayerCard.vue'
import ViolationCard from '@/components/monitor/ViolationCard.vue'
import { analysisApi } from '@/features/analysis/api'
import type { AnalysisJob } from '@/types'
import { PlusCircle, AlertCircle, ShieldAlert, CheckCircle2 } from 'lucide-vue-next'

const apiKey = ref('')
const uploadedVideoUrl = ref<string | null>(null)
const selectedTimecode = ref<number | null>(null)

// Analysis state
const job = ref<AnalysisJob | null>(null)
const uploading = ref(false)
const errorMessage = ref('')
const activeViolationIndex = ref<number | null>(null)

const busy = computed(() => uploading.value || job.value?.status === 'processing')

async function handleStartAnalysis(file: File) {
  errorMessage.value = ''
  uploading.value = true
  job.value = null
  selectedTimecode.value = null
  activeViolationIndex.value = null

  if (uploadedVideoUrl.value) {
    URL.revokeObjectURL(uploadedVideoUrl.value)
  }
  uploadedVideoUrl.value = URL.createObjectURL(file)

  try {
    const response = await analysisApi.submit(file, apiKey.value)
    job.value = response
    pollJobStatus(response.job_id)
  } catch (err) {
    errorMessage.value =
      err instanceof Error ? err.message : 'Не удалось связаться с локальным бэкендом.'
  } finally {
    uploading.value = false
  }
}

async function pollJobStatus(jobId: string) {
  const interval = setInterval(async () => {
    try {
      const res = await analysisApi.get(jobId, apiKey.value)
      job.value = res
      if (res.status === 'done' || res.status === 'failed') {
        clearInterval(interval)
      }
    } catch (err) {
      errorMessage.value =
        err instanceof Error ? err.message : 'Ошибка при получении статуса задачи.'
      clearInterval(interval)
    }
  }, 1500)
}

function resetAnalysis() {
  job.value = null
  if (uploadedVideoUrl.value) {
    URL.revokeObjectURL(uploadedVideoUrl.value)
    uploadedVideoUrl.value = null
  }
  selectedTimecode.value = null
  activeViolationIndex.value = null
  errorMessage.value = ''
}

function onJumpToTimecode(sec: number, index?: number) {
  selectedTimecode.value = sec
  if (index !== undefined) {
    activeViolationIndex.value = index
  }
}
</script>

<template>
  <AppLayout>
    <template #header-actions>
      <button
        v-if="job"
        type="button"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-slate-200 transition-colors"
        @click="resetAnalysis"
      >
        <PlusCircle class="w-3.5 h-3.5" />
        <span>Новая проверка</span>
      </button>
    </template>

    <div class="flex flex-col gap-6">
      <!-- Title & Context -->
      <div class="flex flex-col gap-1">
        <h1 class="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
          Мониторинг кассовой дисциплины
        </h1>
        <p class="text-sm text-slate-400 max-w-2xl">
          Автоматический On-Premise анализ видеозаписей кассовых операций на предмет соблюдения регламентов ForteBank и нормативных требований Республики Казахстан.
        </p>
      </div>

      <!-- 1. Video Upload State -->
      <VideoUploadCard
        v-if="!job"
        :api-key="apiKey"
        :busy="busy"
        @update:api-key="apiKey = $event"
        @start-analysis="handleStartAnalysis"
      />

      <!-- 2. Processing State -->
      <ProcessingCard
        v-if="busy || job?.status === 'processing'"
        :progress="job?.progress || 0"
        :stage="job?.stage"
        :elapsed-sec="job?.elapsed_sec"
      />

      <!-- 3. Error Banner -->
      <div
        v-if="errorMessage || job?.status === 'failed'"
        class="bg-red-500/10 border border-red-500/25 text-red-300 p-4 rounded-2xl flex items-start justify-between gap-3"
      >
        <div class="flex items-start gap-3">
          <AlertCircle class="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <h4 class="font-bold text-sm text-red-200">Ошибка обработки</h4>
            <p class="text-xs text-red-300/90 mt-0.5">
              {{ errorMessage || job?.error || 'Произошла непредвиденная ошибка при анализе видеозаписи.' }}
            </p>
          </div>
        </div>

        <button
          type="button"
          class="text-xs font-semibold px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-200 border border-red-500/30 transition-colors shrink-0"
          @click="resetAnalysis"
        >
          Повторить
        </button>
      </div>

      <!-- 4. Done State: Verdict & Workspace -->
      <div v-if="job?.status === 'done'" class="flex flex-col gap-6 animate-fade-in">
        <!-- Verdict Banner -->
        <VerdictBanner
          :verdict="job.verdict ?? 'no_violation'"
          :violations-count="job.violations.length"
          :elapsed-sec="job.elapsed_sec"
          :limitations="job.limitations"
        />

        <!-- Two-column Workspace -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          <!-- Left: Video Player (lg: 7 cols) -->
          <div class="lg:col-span-7 lg:sticky lg:top-24 flex flex-col gap-4">
            <VideoPlayerCard
              :video-url="uploadedVideoUrl"
              :violations="job.violations"
              :selected-timecode="selectedTimecode"
              @select-timecode="onJumpToTimecode($event)"
            />
          </div>

          <!-- Right: Violations List (lg: 5 cols) -->
          <div class="lg:col-span-5 flex flex-col gap-4">
            <div class="flex items-center gap-2 border-b border-white/10 pb-2">
              <ShieldAlert class="w-4 h-4 text-red-400" />
              <h3 class="font-bold text-sm text-slate-100">
                Зафиксированные события ({{ job.violations.length }})
              </h3>
            </div>

            <!-- List of Violations -->
            <div v-if="job.violations.length > 0" class="flex flex-col gap-3.5">
              <ViolationCard
                v-for="(violation, idx) in job.violations"
                :key="idx"
                :violation="violation"
                :index="idx"
                :active="activeViolationIndex === idx"
                @jump="onJumpToTimecode($event, idx)"
              />
            </div>

            <!-- Clean / No Violations State -->
            <div
              v-else
              class="bg-[#0f1420] border border-white/10 rounded-2xl p-8 flex flex-col items-center text-center gap-2"
            >
              <div class="w-12 h-12 rounded-full bg-emerald-500/15 text-emerald-400 flex items-center justify-center">
                <CheckCircle2 class="w-6 h-6" />
              </div>
              <h4 class="font-bold text-sm text-slate-200 mt-2">Нарушений не обнаружено</h4>
              <p class="text-xs text-slate-400 max-w-xs">
                Все действия кассира на проанализированном отрезке соответствуют регламенту.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
