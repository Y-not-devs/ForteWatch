<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
import { UploadCloud, CheckCircle, Clock, AlertTriangle } from 'lucide-vue-next'
</script>

<template>
  <AppLayout>
    <div class="stack" style="gap: 28px">
      <!-- Page Header -->
      <header class="row between wrap" style="gap: 16px; align-items: flex-start">
        <div>
          <h1 style="font-size: 1.8rem; font-weight: 750; margin-bottom: 6px">
            Мониторинг кассовой дисциплины
          </h1>
          <p class="muted" style="font-size: 0.95rem">
            Базовый шаблон интерфейса ForteWatch. Локальный анализ видео и фиксация нарушений.
          </p>
        </div>

        <button
          type="button"
          style="
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: var(--accent);
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            box-shadow: 0 4px 14px -3px rgba(99, 102, 241, 0.4);
          "
        >
          <UploadCloud :size="18" />
          <span>Загрузить видео</span>
        </button>
      </header>

      <!-- Quick Metrics Grid -->
      <div
        class="grid"
        style="
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
        "
      >
        <div
          style="
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
          "
        >
          <div class="row" style="gap: 12px; align-items: center; margin-bottom: 12px">
            <div
              style="
                width: 36px;
                height: 36px;
                border-radius: 8px;
                background: rgba(99, 102, 241, 0.15);
                color: var(--accent);
                display: grid;
                place-items: center;
              "
            >
              <Clock :size="18" />
            </div>
            <span class="muted" style="font-size: 0.85rem; font-weight: 500">Видео в обработке</span>
          </div>
          <div style="font-size: 1.6rem; font-weight: 700">0</div>
        </div>

        <div
          style="
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
          "
        >
          <div class="row" style="gap: 12px; align-items: center; margin-bottom: 12px">
            <div
              style="
                width: 36px;
                height: 36px;
                border-radius: 8px;
                background: rgba(239, 68, 68, 0.15);
                color: #f87171;
                display: grid;
                place-items: center;
              "
            >
              <AlertTriangle :size="18" />
            </div>
            <span class="muted" style="font-size: 0.85rem; font-weight: 500">Обнаружено нарушений</span>
          </div>
          <div style="font-size: 1.6rem; font-weight: 700">0</div>
        </div>

        <div
          style="
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 20px;
          "
        >
          <div class="row" style="gap: 12px; align-items: center; margin-bottom: 12px">
            <div
              style="
                width: 36px;
                height: 36px;
                border-radius: 8px;
                background: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                display: grid;
                place-items: center;
              "
            >
              <CheckCircle :size="18" />
            </div>
            <span class="muted" style="font-size: 0.85rem; font-weight: 500">Проверено записей</span>
          </div>
          <div style="font-size: 1.6rem; font-weight: 700">0</div>
        </div>
      </div>

      <!-- Main Workspace Card / Layout Placeholder -->
      <section
        style="
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-md);
          padding: 32px 24px;
          text-align: center;
        "
      >
        <div class="stack" style="align-items: center; gap: 12px; max-width: 480px; margin: 0 auto">
          <div
            style="
              width: 52px;
              height: 52px;
              border-radius: 14px;
              background: var(--surface-hover);
              border: 1px solid var(--border);
              display: grid;
              place-items: center;
              color: var(--text-muted);
            "
          >
            <UploadCloud :size="24" />
          </div>
          <h2 style="font-size: 1.25rem; font-weight: 650">Рабочая область готова к разработке</h2>
          <p class="muted" style="font-size: 0.9rem; line-height: 1.5">
            Фронтенд успешно переведён на Vue 3 + Vite. Здесь можно подключать страницы анализа, видеоплеер с таймлайном нарушений и таблицы результатов.
          </p>
        </div>
      </section>
    </div>
  </AppLayout>
</template>
