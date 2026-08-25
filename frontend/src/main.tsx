import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ApiClientProvider } from './api/ApiClientContext.tsx'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ApiClientProvider>
      <App />
    </ApiClientProvider>
  </StrictMode>,
)
