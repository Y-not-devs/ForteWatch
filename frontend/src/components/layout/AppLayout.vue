<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ShieldCheck, Cpu, ExternalLink } from 'lucide-vue-next'

const backendStatus = ref<'online' | 'offline' | 'checking'>('checking')

onMounted(async () => {
  try {
    const res = await fetch('/api/health')
    backendStatus.value = res.ok ? 'online' : 'offline'
  } catch {
    backendStatus.value = 'offline'
  }
})
</script>

<template>
  <div class="min-h-screen bg-[#090c13] text-slate-100 flex flex-col">
    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-30 border-b border-white/10 bg-[#0f1420]/80 backdrop-blur-md">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <!-- Brand / Identity -->
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-[#a51c30] to-indigo-600 flex items-center justify-center shadow-lg shadow-[#a51c30]/20 text-white">
            <ShieldCheck class="w-5 h-5" />
          </div>
          <div class="flex items-center gap-2">
            <span class="font-bold text-lg tracking-tight text-white">ForteWatch</span>
            <span class="text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider bg-[#a51c30]/20 text-red-400 border border-[#a51c30]/40">
              AI
            </span>
          </div>
          <span class="hidden md:inline-block text-xs text-slate-400 pl-2 border-l border-white/10">
            ForteBank Datathon 26 • Кассовая дисциплина
          </span>
        </div>

        <!-- Right Side: System Status & Actions -->
        <div class="flex items-center gap-3 sm:gap-4">
          <!-- Local On-Premise Badge -->
          <div class="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Cpu class="w-3.5 h-3.5" />
            <span>100% On-Premise</span>
          </div>

          <!-- Backend Status Indicator -->
          <div class="flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border"
            :class="{
              'bg-emerald-500/10 text-emerald-400 border-emerald-500/25': backendStatus === 'online',
              'bg-red-500/10 text-red-400 border-red-500/25': backendStatus === 'offline',
              'bg-slate-500/10 text-slate-400 border-slate-500/25': backendStatus === 'checking',
            }"
          >
            <span class="w-2 h-2 rounded-full"
              :class="{
                'bg-emerald-400 animate-pulse': backendStatus === 'online',
                'bg-red-400': backendStatus === 'offline',
                'bg-slate-400': backendStatus === 'checking',
              }"
            />
            <span>{{ backendStatus === 'online' ? 'API Online' : backendStatus === 'offline' ? 'API Offline' : 'Проверка...' }}</span>
          </div>

          <!-- API Docs Swagger Link -->
          <a
            href="/api/docs"
            target="_blank"
            rel="noreferrer"
            class="hidden sm:inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors px-2 py-1 rounded hover:bg-white/5"
            title="Открыть документацию Swagger OpenAPI"
          >
            <span>Swagger</span>
            <ExternalLink class="w-3.5 h-3.5" />
          </a>

          <!-- Custom Slot for Header Actions (e.g. New Review Button) -->
          <slot name="header-actions" />
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <slot />
    </main>

    <!-- Footer -->
    <footer class="border-t border-white/5 py-4 text-center text-xs text-slate-500">
      ForteWatch • Локальный видеомониторинг кассовой дисциплины • Регламенты НПА РК
    </footer>
  </div>
</template>
