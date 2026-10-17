import { AppLayout } from '@/components/layout/AppLayout'
import { UploadsPage } from '@/features/uploads/UploadsPage'
import { AnalysisPage } from '@/features/analysis/AnalysisPage'

export function App() {
  return (
    <AppLayout>
      {window.location.pathname === '/uploads' ? <UploadsPage /> : <AnalysisPage />}
    </AppLayout>
  )
}
