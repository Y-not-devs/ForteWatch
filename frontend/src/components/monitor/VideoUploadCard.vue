<script setup lang="ts">
import { ref } from 'vue'
import { UploadCloud, FileVideo, Key, AlertCircle, Sparkles, X } from 'lucide-vue-next'

const props = defineProps<{
  apiKey: string
  busy: boolean
}>()

const emit = defineEmits<{
  (e: 'update:apiKey', key: string): void
  (e: 'start-analysis', file: File): void
}>()

const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const validationError = ref('')

function handleDrop(event: DragEvent) {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) validateAndSetFile(file)
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) validateAndSetFile(file)
}

function validateAndSetFile(file: File) {
  validationError.value = ''
  const validExtensions = /\.(mov|mp4|avi|webm)$/i
  if (!validExtensions.test(file.name)) {
    validationError.value = 'Поддерживаются видео в формате .mov, .mp4 или .avi'
    return
  }
  if (file.size > 512 * 1024 * 1024) {
    validationError.value = 'Максимальный размер видеофайла — 512 МБ'
    return
  }
  selectedFile.value = file
}

function clearFile() {
  selectedFile.value = null
  validationError.value = ''
}

function triggerSubmit() {
  if (!selectedFile.value) {
    validationError.value = 'Пожалуйста, выберите видеофайл для анализа'
    return
  }
  if (!props.apiKey.trim()) {
    validationError.value = 'Укажите API-ключ для авторизации проверки'
    return
  }
  emit('start-analysis', selectedFile.value)
}
</script>

<template>
  <div class="bg-[#0f1420] border border-white/10 rounded-2xl p-6 sm:p-8 shadow-2xl flex flex-col gap-6">
    <!-- Header -->
    <div class="border-b border-white/10 pb-5">
      <h2 class="text-xl font-bold tracking-tight text-white">Загрузка видеозаписи для проверки</h2>
      <p class="text-slate-400 text-sm mt-1">
        Видео анализируется полностью локально без передачи во внешние облачные сервисы (On-Premise контур ForteBank).
      </p>
    </div>

    <!-- API Key Input -->
    <div class="flex flex-col gap-2">
      <label for="api-key-input" class="flex items-center gap-2 text-xs font-semibold text-slate-300">
        <Key class="w-4 h-4 text-slate-400" />
        <span>Ключ авторизации (X-API-Key для жюри):</span>
      </label>
      <input
        id="api-key-input"
        type="password"
        class="w-full bg-white/[0.03] border border-white/15 focus:border-[#a51c30] rounded-xl px-4 py-2.5 font-mono text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-colors"
        placeholder="Введите ключ доступа (X-API-Key)..."
        :value="apiKey"
        :disabled="busy"
        autocomplete="off"
        @input="$emit('update:apiKey', ($event.target as HTMLInputElement).value)"
      />
      <span class="text-[11px] text-slate-500">
        Ключ передаётся в заголовке <code class="text-slate-400 bg-white/5 px-1 rounded">X-API-Key</code> при каждом запросе к API.
      </span>
    </div>

    <!-- Drag & Drop Area -->
    <div
      class="border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center transition-all cursor-pointer relative"
      :class="[
        isDragging ? 'border-[#a51c30] bg-[#a51c30]/10' : 'border-white/15 bg-white/[0.02] hover:border-[#a51c30]/60 hover:bg-[#a51c30]/5',
        selectedFile ? 'border-emerald-500/40 bg-emerald-500/5' : '',
      ]"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
    >
      <input
        id="video-upload-input"
        type="file"
        class="absolute inset-0 opacity-0 cursor-pointer w-full h-full z-10"
        accept=".mov,.mp4,.avi,video/quicktime,video/mp4"
        :disabled="busy"
        @change="handleFileSelect"
      />

      <div v-if="!selectedFile" class="flex flex-col items-center gap-3">
        <div class="w-14 h-14 rounded-2xl bg-[#a51c30]/15 text-red-400 border border-[#a51c30]/30 flex items-center justify-center">
          <UploadCloud class="w-7 h-7" />
        </div>
        <div>
          <span class="text-base font-semibold text-slate-200">Перетащите видеофайл сюда или </span>
          <label for="video-upload-input" class="text-red-400 underline cursor-pointer font-semibold">выберите на диске</label>
        </div>
        <p class="text-xs text-slate-400 max-w-md">
          Форматы: <strong class="text-slate-300">.MOV</strong>, <strong class="text-slate-300">.MP4</strong> (до 512 МБ). Рекомендуется видеозапись работы кассира над рабочей зоной.
        </p>
      </div>

      <!-- File Selected State -->
      <div v-else class="flex items-center justify-between bg-[#151c2c] border border-white/15 p-4 rounded-xl text-left relative z-20">
        <div class="flex items-center gap-3 min-w-0">
          <div class="w-10 h-10 rounded-lg bg-red-500/15 text-red-400 flex items-center justify-center shrink-0">
            <FileVideo class="w-5 h-5" />
          </div>
          <div class="min-w-0">
            <div class="font-semibold text-sm text-slate-100 truncate">{{ selectedFile.name }}</div>
            <div class="text-xs text-slate-400">
              {{ (selectedFile.size / (1024 * 1024)).toFixed(2) }} МБ • Готов к инференсу
            </div>
          </div>
        </div>

        <button
          type="button"
          class="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors shrink-0"
          title="Удалить файл"
          :disabled="busy"
          @click.stop="clearFile"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </div>

    <!-- Error Banner -->
    <div v-if="validationError" class="flex items-center gap-2 text-sm text-red-400 bg-red-500/10 border border-red-500/20 px-4 py-3 rounded-xl">
      <AlertCircle class="w-4 h-4 shrink-0" />
      <span>{{ validationError }}</span>
    </div>

    <!-- Submit Section -->
    <div class="flex items-center justify-between pt-2">
      <span class="text-xs text-slate-500 hidden sm:inline">
        Сценарий: Загрузка → Локальный AI-анализ → Вердикт с кадрами-доказательствами
      </span>

      <button
        type="button"
        class="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-sm text-white bg-gradient-to-r from-[#a51c30] to-rose-700 hover:from-[#c41e3a] hover:to-rose-600 shadow-lg shadow-[#a51c30]/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none ml-auto"
        :disabled="busy || !selectedFile || !apiKey.trim()"
        @click="triggerSubmit"
      >
        <Sparkles v-if="!busy" class="w-4 h-4" />
        <span>{{ busy ? 'Обработка запущена…' : 'Запустить AI-анализ' }}</span>
      </button>
    </div>
  </div>
</template>
