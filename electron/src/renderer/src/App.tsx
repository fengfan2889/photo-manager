import React, { useEffect } from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import Gallery from './pages/Gallery'
import Organizer from './pages/Organizer'
import Annotation from './pages/Annotation'
import Tags from './pages/Tags'
import Settings from './pages/Settings'
import ImportHistory from './pages/ImportHistory'
import './index.css'
import { logger } from './utils/logger'

// 初始化日志
logger.info('[App]', 'PhotoManager starting...')

// 路由监听组件
function RouteLogger() {
  const location = useLocation()
  useEffect(() => {
    console.log('[Route] changed to:', location.pathname)
  }, [location])
  return null
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <RouteLogger />
      <Layout>
        <Routes>
          <Route path="/" element={<Gallery />} />
          <Route path="/organize" element={<Organizer />} />
          <Route path="/photo/:id" element={<Annotation />} />
          <Route path="/tags" element={<Tags />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/history" element={<ImportHistory />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  </React.StrictMode>
)
