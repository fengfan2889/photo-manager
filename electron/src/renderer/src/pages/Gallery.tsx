import { useEffect, useState } from 'react'
import { logger } from '../utils/logger'
import PhotoGrid from '../components/PhotoGrid'
import { ErrorToast } from '../components/ErrorToast'
import { useError } from '../hooks/useError'
import type { Photo, PhotoFilters, Tag } from '../../preload/index'

interface TagWithCount extends Tag {
  photo_count?: number
}

export default function Gallery() {
  const [photos, setPhotos] = useState<Photo[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [ratingMin, setRatingMin] = useState<number | null>(null)
  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)
  const [tags, setTags] = useState<TagWithCount[]>([])
  const [selectedTags, setSelectedTags] = useState<number[]>([])
  const { error, showError, clearError } = useError()

  useEffect(() => {
    logger.info('Gallery page mounted')
    loadPhotos()
    loadTags()
  }, [])

  // 当过滤条件变化时重新加载照片
  useEffect(() => {
    loadPhotos()
  }, [selectedTags])

  const loadTags = async () => {
    try {
      const result = await window.electronAPI.pythonExec('get-tags', {})
      const allTags = result?.data || result || []
      // 只显示有照片的标签
      const tagsWithPhotos = allTags.filter((t: TagWithCount) => (t.photo_count || 0) > 0)
      setTags(tagsWithPhotos)
    } catch (error) {
      logger.error('Failed to load tags', error)
    }
  }

  const loadPhotos = async () => {
    setLoading(true)
    logger.debug('Loading photos')
    try {
      const filters: PhotoFilters = {}
      if (search.trim()) {
        filters.search = search.trim()
      }
      if (ratingMin !== null) {
        filters.rating_min = ratingMin
      }
      if (dateFrom) {
        filters.date_from = dateFrom
      }
      if (dateTo) {
        filters.date_to = dateTo
      }
      if (selectedTags.length > 0) {
        filters.tag_ids = selectedTags
      }

      const result = await window.electronAPI.pythonExec('query-photos', {
        limit: 100,
        offset: 0,
        ...filters
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
    await loadPhotos()
  }

  const handleReset = () => {
    setSearch('')
    setRatingMin(null)
    setDateFrom(null)
    setDateTo(null)
    setSelectedTags([])
    loadPhotos()
  }

  const handleTagToggle = (tagId: number) => {
    // 切换标签选中状态，useEffect 会自动触发重新加载
    if (selectedTags.includes(tagId)) {
      setSelectedTags(selectedTags.filter(id => id !== tagId))
    } else {
      setSelectedTags([...selectedTags, tagId])
    }
    // 不需要手动调用 loadPhotos，useEffect 会监听 selectedTags 变化
  }

  return (
    <>
      <ErrorToast error={error} onClose={clearError} />
      
      {/* 搜索和过滤栏 */}
      <div className="flex flex-col gap-4 mb-6">
        {/* 搜索行 */}
        <div className="flex gap-4">
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
            onClick={handleReset}
            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            重置
          </button>
        </div>
        
        {/* 高级过滤行 */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-sm font-medium mb-1">最低评分</label>
            <select
              value={ratingMin === null ? '' : String(ratingMin)}
              onChange={(e) => {
                const value = e.target.value
                setRatingMin(value === '' ? null : parseInt(value))
              }}
              className="w-full px-3 py-2 border rounded-lg"
            >
              <option value="">不限制</option>
              <option value="1">1星及以上</option>
              <option value="2">2星及以上</option>
              <option value="3">3星及以上</option>
              <option value="4">4星及以上</option>
              <option value="5">5星及以上</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">开始日期</label>
            <input
              type="date"
              value={dateFrom || ''}
              onChange={(e) => setDateFrom(e.target.value || null)}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">结束日期</label>
            <input
              type="date"
              value={dateTo || ''}
              onChange={(e) => setDateTo(e.target.value || null)}
              className="w-full px-3 py-2 border rounded-lg"
            />
          </div>
        </div>
        
        {/* 标签过滤 */}
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm text-gray-600">标签:</span>
          {tags.map(tag => {
            const isSelected = selectedTags.includes(tag.id)
            return (
              <button
                key={tag.id}
                onClick={() => { handleTagToggle(tag.id); loadPhotos() }}
                className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm cursor-pointer ${
                  isSelected 
                    ? 'text-white hover:opacity-90' 
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                style={isSelected ? { backgroundColor: tag.color } : {}}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: isSelected ? '#fff' : tag.color }}
                />
                {tag.name}
                <span className={`text-xs ${isSelected ? 'text-white/80' : 'text-gray-500'}`}>
                  ({tag.photo_count})
                </span>
              </button>
            )
          })}
          {selectedTags.length > 0 && (
            <button
              onClick={() => setSelectedTags([])}
              className="text-sm text-gray-500 hover:text-gray-700 ml-2"
            >
              清除
            </button>
          )}
        </div>
      </div>
      
      {/* 照片网格 */}
      <PhotoGrid photos={photos} loading={loading} />
    </>
  )
}
