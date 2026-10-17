import { request } from '@/lib/api'

export interface AnalysisJob {
  job_id: string
  status: 'processing' | 'done' | 'failed'
  stage: string
  progress: number
  elapsed_sec: number
  error: string | null
  verdict: 'violation' | 'no_violation' | null
  limitations: string | null
  violations: {
    type: string
    timecode_sec: number
    description: string
    evidence_frames: { timestamp_sec: number; image_base64: string }[]
    rule: { title: string; document: string; section: string; url: string; rationale: string }
  }[]
}

export const analysisApi = {
  submit(file: File, key: string) {
    const form = new FormData()
    form.append('file', file)
    return request<AnalysisJob>('/v1/analyze', {
      method: 'POST', body: form, headers: { 'X-API-Key': key },
    })
  },
  get(id: string, key: string, signal?: AbortSignal) {
    return request<AnalysisJob>(`/v1/jobs/${encodeURIComponent(id)}`, { headers: { 'X-API-Key': key }, signal })
  },
}
