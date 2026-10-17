import { request } from '@/lib/api'
import type { AnalysisJob } from '@/types'

export type { AnalysisJob }

export const analysisApi = {
  submit(file: File, key: string) {
    const form = new FormData()
    form.append('file', file)
    return request<AnalysisJob>('/v1/analyze', {
      method: 'POST',
      body: form,
      headers: { 'X-API-Key': key },
    })
  },
  get(id: string, key: string, signal?: AbortSignal) {
    return request<AnalysisJob>(`/v1/jobs/${id}`, {
      headers: { 'X-API-Key': key },
      signal,
    })
  },
}
