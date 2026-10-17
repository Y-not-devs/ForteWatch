<script setup lang="ts">
import { ref } from 'vue'
import {
  Clock,
  Play,
  Scale,
  ExternalLink,
  ZoomIn,
  Download,
  X,
} from 'lucide-vue-next'
import type { Violation, EvidenceFrame } from '@/types'

defineProps<{
  violation: Violation
  index: number
  active?: boolean
}>()

const emit = defineEmits<{
  (e: 'jump', timecode: number): void
}>()

const activeFrameModal = ref<EvidenceFrame | null>(null)

function formatTime(seconds: number) {
  if (isNaN(seconds)) return '00:00.00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 100)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`
}
</script>

<template>
  <div
    class="bg-[#0f1420] border rounded-2xl p-5 shadow-lg flex flex-col gap-4 transition-all"
    :class="
      active
        ? 'border-[#a51c30] ring-2 ring-[#a51c30]/30 shadow-red-500/10'
        : 'border-white/10 hover:border-white/20'
    "
  >
    <!-- Header: Number, Type and Timecode Jump -->
    <div class="flex items-center justify-between border-b border-white/10 pb-3 gap-2">
      <div class="flex items-center gap-2.5 min-w-0">
        <span class="text-xs font-bold px-2 py-0.5 rounded-md bg-[#a51c30]/20 text-red-300 border border-[#a51c30]/30 shrink-0">
          #{{ index + 1 }}
        </span>
        <h4 class="font-bold text-sm text-slate-100 truncate">{{ violation.type }}</h4>
      </div>

      <button
        type="button"
        class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-[#a51c30]/20 border border-white/10 hover:border-[#a51c30]/40 text-slate-200 hover:text-white transition-all text-xs font-semibold shrink-0 cursor-pointer"
        @click="emit('jump', violation.timecode_sec)"
      >
        <Play class="w-3 h-3 text-red-400 fill-red-400" />
        <span class="font-mono">{{ formatTime(violation.timecode_sec) }}</span>
      </button>
    </div>

    <!-- Description (Раздел 4, п. 6 ТЗ) -->
    <div class="flex flex-col gap-1">
      <span class="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        Наблюдаемое действие:
      </span>
      <p class="text-xs sm:text-sm text-slate-200 leading-relaxed">
        {{ violation.description }}
      </p>
    </div>

    <!-- Evidence Frames (Раздел 4, п. 5 ТЗ) -->
    <div v-if="violation.evidence_frames && violation.evidence_frames.length > 0" class="flex flex-col gap-2">
      <span class="text-xs font-semibold text-slate-400">
        Кадры-доказательства ({{ violation.evidence_frames.length }}):
      </span>

      <div class="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        <div
          v-for="(frame, fIdx) in violation.evidence_frames"
          :key="fIdx"
          class="group relative rounded-lg overflow-hidden border border-white/15 bg-black cursor-pointer hover:border-white/30 transition-all aspect-video"
          @click="activeFrameModal = frame"
        >
          <img
            :src="`data:image/jpeg;base64,${frame.image_base64}`"
            :alt="`Кадр ${fIdx + 1}`"
            class="w-full h-full object-cover"
            loading="lazy"
          />
          <div class="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white">
            <ZoomIn class="w-5 h-5" />
          </div>
          <div class="absolute bottom-1 right-1 bg-black/80 px-1.5 py-0.5 rounded text-[10px] font-mono text-slate-300">
            {{ formatTime(frame.timestamp_sec) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Rule & Document Citation (Раздел 4, п. 7 & Раздел 6) -->
    <div v-if="violation.rule" class="bg-indigo-950/20 border border-indigo-500/20 rounded-xl p-3.5 flex flex-col gap-1.5">
      <div class="flex items-center gap-1.5 text-indigo-300 text-xs font-semibold">
        <Scale class="w-3.5 h-3.5" />
        <span>Нормативное основание:</span>
      </div>

      <div class="text-xs font-semibold text-slate-200">
        {{ violation.rule.document }} <span class="text-slate-400 font-normal">• {{ violation.rule.section }}</span>
      </div>

      <p class="text-xs text-slate-400 leading-normal">
        {{ violation.rule.rationale }}
      </p>

      <a
        v-if="violation.rule.url"
        :href="violation.rule.url"
        target="_blank"
        rel="noreferrer"
        class="inline-flex items-center gap-1 text-xs text-sky-400 hover:underline pt-1 self-start"
      >
        <span>Открыть в базе adilet.zan.kz</span>
        <ExternalLink class="w-3 h-3" />
      </a>
    </div>

    <!-- Full Frame Modal -->
    <div
      v-if="activeFrameModal"
      class="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4"
      @click="activeFrameModal = null"
    >
      <div class="bg-[#0f1420] border border-white/20 rounded-2xl max-w-3xl w-full overflow-hidden shadow-2xl" @click.stop>
        <div class="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <div class="flex items-center gap-2 font-mono text-xs text-slate-200">
            <Clock class="w-3.5 h-3.5 text-slate-400" />
            <span>Таймкод: {{ formatTime(activeFrameModal.timestamp_sec) }}</span>
          </div>
          <button
            type="button"
            class="text-slate-400 hover:text-white p-1 rounded-lg"
            @click="activeFrameModal = null"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="p-2 bg-black flex items-center justify-center max-h-[70vh]">
          <img
            :src="`data:image/jpeg;base64,${activeFrameModal.image_base64}`"
            alt="Кадр в полном размере"
            class="max-w-full max-h-[65vh] object-contain rounded"
          />
        </div>

        <div class="px-4 py-3 border-t border-white/10 flex justify-end">
          <a
            :href="`data:image/jpeg;base64,${activeFrameModal.image_base64}`"
            download="evidence-frame.jpg"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/15 text-xs font-semibold text-white transition-colors"
          >
            <Download class="w-3.5 h-3.5" />
            <span>Скачать кадр (JPEG)</span>
          </a>
        </div>
      </div>
    </div>
  </div>
</template>
