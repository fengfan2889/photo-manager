import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Gallery from './pages/Gallery'
import Organizer from './pages/Organizer'
import Annotation from './pages/Annotation'
import Tags from './pages/Tags'
import Settings from './pages/Settings'
import './index.css'
import { logger } from './utils/logger'

// 初始化日志
logger.info('[App]', 'PhotoManager starting...')

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Gallery />} />
          <Route path="/organize" element={<Organizer />} />
          <Route path="/photo/:id" element={<Annotation />} />
          <Route path="/tags" element={<Tags />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </React.StrictMode>
)
