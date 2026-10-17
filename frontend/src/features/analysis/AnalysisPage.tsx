import { useEffect, useRef, useState } from 'react'
import { Button, Card, Input, PageHeader } from '@/components/ui'
import { analysisApi, type AnalysisJob } from './api'
import './analysis.css'

const stages: Record<string, string> = {
  accepted: 'Видео принято', reading_video: 'Чтение кадров',
  local_inference: 'Локальный анализ', preparing_evidence: 'Подготовка доказательств',
}
const timecode = (seconds: number) =>
  `${Math.floor(seconds / 60).toString().padStart(2, '0')}:${(seconds % 60).toFixed(2).padStart(5, '0')}`

export function AnalysisPage() {
  // Credentials stay in component memory: never localStorage, URLs or build-time env.
  const [key, setKey] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [reviewFile, setReviewFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [videoReady, setVideoReady] = useState(false)
  const [videoError, setVideoError] = useState(false)
  const video = useRef<HTMLVideoElement>(null)
  const [job, setJob] = useState<AnalysisJob | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const pollingKey = useRef('')
  const busy = uploading || job?.status === 'processing'

  useEffect(() => {
    setVideoReady(false); setVideoError(false)
    if (!reviewFile) return
    const url = URL.createObjectURL(reviewFile)
    setVideoUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [reviewFile])

  useEffect(() => {
    if (!job || job.status !== 'processing') return
    const controller = new AbortController()
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const next = await analysisApi.get(job.job_id, pollingKey.current, controller.signal)
        if (controller.signal.aborted) return
        setJob(next)
        setError('')
        if (next.status === 'processing') timer = setTimeout(poll, 1500)
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Не удалось получить статус')
        }
      }
    }
    timer = setTimeout(poll, 500)
    return () => { controller.abort(); clearTimeout(timer) }
  }, [job?.job_id, job?.status, retry])

  async function submit() {
    if (!file || !key.trim() || busy) return
    if (!/\.mov$/i.test(file.name)) { setError('Выберите видео в формате .mov'); return }
    if (!file.size || file.size > 512 * 1024 * 1024) {
      setError('Размер видео должен быть от 1 байта до 512 МБ'); return
    }
    setError(''); setUploading(true); setJob(null)
    setVideoReady(false); setVideoError(false)
    setReviewFile(file)
    pollingKey.current = key.trim()
    try {
      setJob(await analysisApi.submit(file, pollingKey.current))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не удалось загрузить видео')
    } finally { setUploading(false) }
  }

  return (
    <div className="stack analysis-page" style={{ gap: 24 }}>
      <PageHeader title="Проверка кассового видео" description="Загрузите MOV-запись для локальной проверки признаков возможных нарушений." />
      <Card className="stack" style={{ gap: 16 }}>
        <Input label="API-ключ" type="password" autoComplete="off" value={key}
          onChange={e => setKey(e.target.value)} disabled={busy}
          hint="Ключ доступа к сервису. Хранится только до закрытия страницы." />
        <label className="stack" style={{ gap: 8 }}>
          <span>Видеозапись (.mov, до 512 МБ)</span>
          <input type="file" accept=".mov,video/quicktime" disabled={busy}
            onChange={e => { setFile(e.target.files?.[0] ?? null); setError('') }} />
        </label>
        <Button variant="primary" onClick={() => void submit()} disabled={busy || !file || !key.trim()}
          loading={uploading}>{uploading ? 'Загрузка видео…' : 'Запустить анализ'}</Button>
      </Card>
      {error && <div role="alert" className="analysis-error">
        <p>{error}</p>
        {job?.status === 'processing' && <Button onClick={() => { setError(''); setRetry(v => v + 1) }}>Повторить получение статуса</Button>}
      </div>}
      {job?.status === 'processing' && <Card className="stack" style={{ gap: 12 }}>
        <p role="status">{stages[job.stage] || 'Обработка'} — {job.progress}%</p>
        <progress aria-label="Ход обработки" value={job.progress} max={100} />
        <p className="small muted">Обычно до 5 минут. Вы можете оставить эту страницу открытой.</p>
      </Card>}
      {job?.status === 'failed' && <div role="alert" className="analysis-error">
        <h2>Обработка не завершена</h2><p>{job.error}</p>
        <p>Можно повторно загрузить запись после устранения причины.</p>
      </div>}
      {job?.status === 'done' && <section className="stack" style={{ gap: 20 }} aria-label="Результат анализа">
        <Card className="stack" style={{ gap: 10 }}>
          <h2>{job.verdict === 'violation' ? 'Обнаружены признаки возможных нарушений' : 'Нарушение не обнаружено'}</h2>
          <p className="small muted">Обработано за {job.elapsed_sec.toFixed(1)} с</p>
          <p className="small">{job.limitations}</p>
        </Card>
        {videoUrl && <Card className="stack" style={{ gap: 10 }}>
          <h3>Исходное видео</h3>
          <video ref={video} src={videoUrl} controls playsInline preload="metadata"
            aria-label="Исходное видео" className="analysis-video"
            onLoadedMetadata={() => setVideoReady(true)}
            onError={() => { setVideoReady(false); setVideoError(true) }} />
          {videoError && <p role="status">Браузер не поддерживает кодек этой записи.
            Кадры-доказательства доступны ниже.</p>}
        </Card>}
        {job.violations.map((event, index) => <Card key={index} className="stack" style={{ gap: 12 }}>
          <h3>{event.type} — {timecode(event.timecode_sec)}</h3>
          <Button disabled={!videoReady} onClick={() => {
            if (video.current) {
              video.current.currentTime = event.timecode_sec
              video.current.focus()
            }
          }}>Перейти к {timecode(event.timecode_sec)}</Button>
          <p>{event.description}</p>
          <div className="analysis-evidence">{event.evidence_frames.map((frame, i) => <figure key={i}>
            <a href={`data:image/jpeg;base64,${frame.image_base64}`} download={`evidence-${index + 1}-${i + 1}.jpg`}>
              <img src={`data:image/jpeg;base64,${frame.image_base64}`} alt={`Кадр события ${index + 1}, ${timecode(frame.timestamp_sec)}`} />
            </a>
            <figcaption>{timecode(frame.timestamp_sec)}</figcaption>
          </figure>)}</div>
          <p>{event.rule.rationale}</p>
          <a href={event.rule.url} target="_blank" rel="noreferrer">{event.rule.document} · {event.rule.section}</a>
        </Card>)}
      </section>}
    </div>
  )
}
