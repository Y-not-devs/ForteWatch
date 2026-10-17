import { useRef, useState, type CSSProperties, type DragEvent } from 'react'
import { Download, FileVideo, UploadCloud } from 'lucide-react'
import { Button, Card, EmptyState, ErrorState, PageHeader, Skeleton, useToast } from '@/components/ui'
import { useAppMeta } from '@/context/MetaContext'
import { useQuery } from '@/lib/hooks'
import { formatBytes, formatDate } from '@/lib/format'
import { uploadsApi } from './api'

const MAX_VIDEO_BYTES = 512 * 1024 * 1024

export function UploadsPage() {
  const { meta } = useAppMeta()
  const toast = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const { data: files, loading, error, refetch } = useQuery(
    uploadsApi.list,
    [],
    { enabled: meta?.features.uploads ?? true },
  )

  const handleUpload = async (file: File) => {
    const isVideo = file.type.startsWith('video/') || /\.(mov|mp4|m4v|avi|mkv)$/i.test(file.name)
    if (!isVideo) {
      toast('Choose a video file (MOV, MP4, M4V, AVI, or MKV).', 'error')
      return
    }
    if (file.size > MAX_VIDEO_BYTES) {
      toast('The video exceeds the 512 MB upload limit.', 'error')
      return
    }

    setUploading(true)
    try {
      await uploadsApi.upload(file)
      toast(`Uploaded ${file.name}.`, 'success')
      refetch()
    } catch (err: any) {
      toast(err.message || 'Video upload failed.', 'error')
    } finally {
      setUploading(false)
    }
  }

  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragOver(false)
    const file = event.dataTransfer.files?.[0]
    if (file) void handleUpload(file)
  }

  return (
    <div className="stack" style={{ gap: 24 }}>
      <PageHeader
        title="Cashier video review"
        description="Store and list recordings. Open Analyze video from the sidebar for automated checks."
        actions={
          <Button
            variant="primary"
            icon={<UploadCloud />}
            loading={uploading}
            onClick={() => fileInputRef.current?.click()}
          >
            Choose video
          </Button>
        }
      />

      <input
        ref={fileInputRef}
        type="file"
        accept="video/*,.mov,.mp4,.m4v,.avi,.mkv"
        style={{ display: 'none' }}
        onChange={(event) => {
          const file = event.target.files?.[0]
          if (file) void handleUpload(file)
          event.target.value = ''
        }}
      />

      <div
        onDragOver={(event) => {
          event.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? 'var(--accent)' : 'var(--border-strong)'}`,
          borderRadius: 'var(--radius-lg)',
          padding: '36px 20px',
          textAlign: 'center',
          background: dragOver ? 'var(--surface-hover)' : 'var(--surface)',
          cursor: 'pointer',
        }}
      >
        <div className="stack" style={{ alignItems: 'center', gap: 10 }}>
          <UploadCloud size={26} />
          <div>
            <h3 style={{ fontSize: '1.05rem', marginBottom: 4 }}>Drop a cashier video here or choose a file</h3>
            <p className="small muted">MOV, MP4, M4V, AVI, or MKV · up to 512 MB · stored on this server</p>
          </div>
        </div>
      </div>

      <section>
        <h2 style={{ fontSize: '1.2rem', marginBottom: 16 }}>Uploaded recordings</h2>
        {loading && !files ? (
          <div className="grid"><Skeleton height={100} /><Skeleton height={100} /></div>
        ) : error ? (
          <ErrorState error={error} onRetry={refetch} />
        ) : !files?.length ? (
          <EmptyState
            title="No recordings yet"
            description="Uploaded clips will appear here. Automated findings and evidence are available on the analysis page."
          />
        ) : (
          <div className="grid" style={{ '--min': '260px' } as CSSProperties}>
            {files.map((file) => (
              <Card key={file.name} className="stack" style={{ gap: 12 }}>
                <div className="row" style={{ gap: 8 }}><FileVideo size={20} /><strong className="mono small">{file.name}</strong></div>
                <span className="faint small">{formatBytes(file.size)} · {formatDate(file.created_at)}</span>
                <a href={file.url} download target="_blank" rel="noreferrer">
                  <Button variant="secondary" size="sm" icon={<Download size={14} />}>Download</Button>
                </a>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
