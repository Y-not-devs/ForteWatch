<script setup lang="ts">
import { ref, watch } from 'vue'
import { Play, Pause, RotateCcw, AlertCircle, Bookmark } from 'lucide-vue-next'
import type { Violation } from '@/types'

const props = defineProps<{
  videoUrl: string | null
  violations: Violation[]
  selectedTimecode?: number | null
}>()

const emit = defineEmits<{
  (e: 'select-timecode', sec: number): void
}>()

const videoRef = ref<HTMLVideoElement | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const videoError = ref(false)
const videoReady = ref(false)

function formatTime(seconds: number) {
  if (isNaN(seconds)) return '00:00.00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 100)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
}

function togglePlay() {
  if (!videoRef.value) return
  if (isPlaying.value) {
    videoRef.value.pause()
  } else {
    videoRef.value.play()
  }
}

function seekTo(sec: number) {
  if (!videoRef.value) return
  videoRef.value.currentTime = sec
  videoRef.value.focus()
  emit('select-timecode', sec)
}

function handleTimeUpdate() {
  if (!videoRef.value) return
  currentTime.value = videoRef.value.currentTime
}

function handleLoadedMetadata() {
  if (!videoRef.value) return
  duration.value = videoRef.value.duration
  videoReady.value = true
  videoError.value = false
}

function handleError() {
  videoError.value = true
  videoReady.value = false
}

watch(
  () => props.selectedTimecode,
  (newSec) => {
    if (newSec !== null && newSec !== undefined && videoRef.value) {
      videoRef.value.currentTime = newSec
    }
  },
)

defineExpose({
  seekTo,
})
</script>

<template>
  <div class="bg-[#0f1420] border border-white/10 rounded-2xl p-5 sm:p-6 shadow-xl flex flex-col gap-4">
    <div class="flex items-center justify-between border-b border-white/10 pb-3">
      <div class="flex items-center gap-2">
        <Bookmark class="w-4 h-4 text-red-400" />
        <h3 class="font-semibold text-sm text-slate-100">Видеоконтроль кассы</h3>
      </div>
      <div class="font-mono text-xs font-semibold px-2.5 py-1 rounded-md bg-white/5 border border-white/10 text-slate-200">
        <span>{{ formatTime(currentTime) }}</span>
        <span class="text-slate-500"> / {{ formatTime(duration) }}</span>
      </div>
    </div>

    <!-- Video Stage -->
    <div class="w-full aspect-video bg-black rounded-xl overflow-hidden border border-white/10 relative flex items-center justify-center">
      <video
        v-if="videoUrl"
        ref="videoRef"
        :src="videoUrl"
        class="w-full h-full object-contain"
        playsinline
        preload="metadata"
        @timeupdate="handleTimeUpdate"
        @loadedmetadata="handleLoadedMetadata"
        @play="isPlaying = true"
        @pause="isPlaying = false"
        @error="handleError"
      />

      <div v-else class="flex flex-col items-center justify-center text-center p-6 gap-3">
        <div class="w-12 h-12 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-slate-400">
          <Play class="w-6 h-6 ml-0.5" />
        </div>
        <p class="text-xs text-slate-400 max-w-xs">
          Видеофайл готов к воспроизведению после загрузки
        </p>
      </div>

      <!-- Codec Warning -->
      <div v-if="videoError" class="absolute bottom-3 inset-x-3 bg-[#0f1420]/95 backdrop-blur-md border border-amber-500/40 text-amber-300 p-3 rounded-xl flex items-start gap-2.5 text-xs">
        <AlertCircle class="w-4 h-4 shrink-0 mt-0.5" />
        <div>
          <strong>Браузер не поддерживает данный кодек MOV напрямую.</strong>
          <p class="text-amber-400/80 mt-0.5">
            Кадры-доказательства и точные таймкоды доступны в списке нарушений справа.
          </p>
        </div>
      </div>
    </div>

    <!-- Timeline & Jump Markers -->
    <div v-if="videoUrl && duration > 0" class="flex flex-col gap-2.5">
      <div
        class="w-full h-2 bg-white/10 rounded-full relative cursor-pointer border border-white/10"
        @click="(e) => {
          const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
          const clickRatio = (e.clientX - rect.left) / rect.width
          seekTo(clickRatio * duration)
        }"
      >
        <div
          class="h-full bg-gradient-to-r from-[#a51c30] to-indigo-500 rounded-full pointer-events-none"
          :style="{ width: `${(currentTime / duration) * 100}%` }"
        />

        <!-- Markers for violations -->
        <div
          v-for="(v, idx) in violations"
          :key="idx"
          class="absolute -top-1 w-4 h-4 rounded-full bg-red-500 border-2 border-white -translate-x-1/2 cursor-pointer shadow-lg hover:scale-125 transition-transform z-10"
          :style="{ left: `${(v.timecode_sec / duration) * 100}%` }"
          :title="`${v.type} (${formatTime(v.timecode_sec)})`"
          @click.stop="seekTo(v.timecode_sec)"
        />
      </div>

      <!-- Chips list -->
      <div v-if="violations.length > 0" class="flex flex-wrap items-center gap-1.5 pt-1">
        <span class="text-[11px] text-slate-500 mr-1">Метки:</span>
        <button
          v-for="(v, idx) in violations"
          :key="idx"
          type="button"
          class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono border transition-all"
          :class="
            Math.abs(currentTime - v.timecode_sec) < 1.5
              ? 'bg-[#a51c30]/25 border-[#a51c30] text-white shadow-sm'
              : 'bg-white/5 border-white/10 text-slate-400 hover:text-white hover:bg-white/10'
          "
          @click="seekTo(v.timecode_sec)"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-red-400" />
          <span>{{ formatTime(v.timecode_sec) }}</span>
        </button>
      </div>
    </div>

    <!-- Controls -->
    <div v-if="videoUrl" class="flex items-center justify-between pt-2 border-t border-white/10">
      <div class="flex items-center gap-2">
        <button
          type="button"
          class="w-9 h-9 rounded-lg bg-white/5 border border-white/15 text-slate-200 flex items-center justify-center hover:bg-white/10 transition-colors disabled:opacity-40"
          :disabled="!videoReady"
          @click="togglePlay"
        >
          <Pause v-if="isPlaying" class="w-4 h-4" />
          <Play v-else class="w-4 h-4 ml-0.5" />
        </button>

        <button
          type="button"
          class="w-9 h-9 rounded-lg bg-white/5 border border-white/15 text-slate-200 flex items-center justify-center hover:bg-white/10 transition-colors disabled:opacity-40"
          title="В начало"
          :disabled="!videoReady"
          @click="seekTo(0)"
        >
          <RotateCcw class="w-4 h-4" />
        </button>
      </div>

      <span class="text-xs text-slate-500">
        Кликните по таймкоду для перемотки видео
      </span>
    </div>
  </div>
</template>
