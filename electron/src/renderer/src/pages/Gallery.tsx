import { useEffect, useState } from 'react'
import { logger } from '../utils/logger'
import PhotoGrid from '../components/PhotoGrid'
import { ErrorToast } from '../components/ErrorToast'
import { useError } from '../hooks/useError'
import type { Photo } from '../../preload/index'

export default function Gallery() {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const { error, showError, clearError } = useError()

  useEffect(() => {
    logger.info('Gallery page mounted')
    loadPhotos()
  }, [])

  const loadPhotos = async () => {
    setLoading(true)
    logger.debug('Loading photos')
    try {
      const result = await window.electronAPI.pythonExec('query-photos', {
        limit: 100,
        offset: 0
      })
      
      // 兼容两种返回格式：{ success, data } 或直接返回 data
      const photos = result?.data || result || []
      logger.info(`Loaded ${photos.length} photos`)
      setPhotos(photos)
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('加载照片失败', msg)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!search.trim()) {
      loadPhotos()
      return
    }

    setLoading(true)
    try {
      const result = await window.electronAPI.pythonExec('query-photos', {
        search: search.trim()
      })
      
      if (result?.success && result.data) {
        setPhotos(result.data as Photo[])
      } else {
        showError('搜索失败', result?.error)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('搜索失败', msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <ErrorToast error={error} onClose={clearError} />
      
      {/* 搜索栏 */}
      <div className="flex gap-4 mb-6">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索照片..."
          className="flex-1 px-4 py-2 border rounded-lg"
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          onClick={handleSearch}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          搜索
        </button>
        <button
          onClick={loadPhotos}
          className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          刷新
        </button>
      </div>

      {/* 照片网格 */}
      <PhotoGrid photos={photos} loading={loading} />
    </>
  )
}
