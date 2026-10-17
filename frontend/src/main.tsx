import React from 'react'
import ReactDOM from 'react-dom/client'
import { App } from './App'
import { MetaProvider } from './context/MetaContext'
import { ToastProvider } from './components/ui'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <MetaProvider>
      <ToastProvider>
        <App />
      </ToastProvider>
    </MetaProvider>
  </React.StrictMode>
)
