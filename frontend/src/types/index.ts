export interface EvidenceFrame {
  timestamp_sec: number
  image_base64: string
}

export interface RuleSource {
  title: string
  document: string
  section: string
  url?: string
  rationale: string
}

export interface Violation {
  type: string
  timecode_sec: number
  description: string
  evidence_frames: EvidenceFrame[]
  rule?: RuleSource
}

export type JobStatus = 'idle' | 'uploading' | 'processing' | 'done' | 'failed'
export type JobVerdict = 'violation' | 'no_violation' | null

export interface AnalysisJob {
  job_id: string
  status: JobStatus
  stage?: string
  progress?: number
  elapsed_sec?: number
  error?: string | null
  verdict?: JobVerdict
  limitations?: string | null
  violations: Violation[]
}
