<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ExternalLink, Film, LayoutDashboard, Settings, ShieldAlert, Zap } from 'lucide-vue-next'
import './layout.css'

const apiTarget = '/api/docs'
const backendStatus = ref<'online' | 'offline' | 'checking'>('checking')

onMounted(async () => {
  try {
    const res = await fetch('/api/health')
    if (res.ok) {
      backendStatus.value = 'online'
    } else {
      backendStatus.value = 'offline'
    }
  } catch {
    backendStatus.value = 'offline'
  }
})
</script>

<template>
  <div class="app-layout">
    <aside class="app-sidebar">
      <div>
        <div class="app-brand">
          <div class="app-brand__icon">
            <Zap :size="20" />
          </div>
          <div>
            <div class="app-brand__title">ForteWatch</div>
            <div class="small faint">v0.1.0 • dev</div>
          </div>
        </div>

        <nav class="app-nav">
          <a href="#" class="app-nav__item app-nav__item--active">
            <LayoutDashboard :size="18" />
            <span class="grow">Дашборд</span>
          </a>
          <a href="#" class="app-nav__item">
            <Film :size="18" />
            <span class="grow">Видеозаписи</span>
          </a>
          <a href="#" class="app-nav__item">
            <ShieldAlert :size="18" />
            <span class="grow">Нарушения</span>
          </a>
          <a href="#" class="app-nav__item">
            <Settings :size="18" />
            <span class="grow">Настройки</span>
          </a>
          <a :href="apiTarget" target="_blank" rel="noreferrer" class="app-nav__item">
            <ExternalLink :size="18" />
            <span class="grow">API Docs</span>
          </a>
        </nav>
      </div>

      <div class="app-sidebar__bottom">
        <div class="row between" style="font-size: 0.82rem">
          <span class="muted">Бэкенд</span>
          <span
            :style="{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '2px 8px',
              borderRadius: '999px',
              fontSize: '0.75rem',
              fontWeight: 600,
              background:
                backendStatus === 'online'
                  ? 'rgba(34, 197, 94, 0.15)'
                  : backendStatus === 'offline'
                    ? 'rgba(239, 68, 68, 0.15)'
                    : 'rgba(148, 163, 184, 0.15)',
              color:
                backendStatus === 'online'
                  ? '#4ade80'
                  : backendStatus === 'offline'
                    ? '#f87171'
                    : '#94a3b8',
            }"
          >
            <span
              :style="{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'currentColor',
              }"
            />
            {{ backendStatus === 'online' ? 'Online' : backendStatus === 'offline' ? 'Offline' : 'Checking…' }}
          </span>
        </div>
        <div class="small faint" style="text-align: center; font-size: 0.75rem">
          Local video review
        </div>
      </div>
    </aside>

    <main class="app-main">
      <slot />
    </main>
  </div>
</template>
