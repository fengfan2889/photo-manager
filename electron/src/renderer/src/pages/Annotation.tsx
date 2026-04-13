import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { logger } from '../utils/logger'
import { ErrorToast } from '../components/ErrorToast'
import { useError } from '../hooks/useError'
import type { Photo, Face, Tag } from '../../preload/index'

export default function Annotation() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [photo, setPhoto] = useState<Photo | null>(null)
  const [faces, setFaces] = useState<Face[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [allTags, setAllTags] = useState<Tag[]>([])
  const [loading, setLoading] = useState(true)
  const [detecting, setDetecting] = useState(false)
  const { error, showError, clearError } = useError()

  useEffect(() => {
    if (id) {
      loadPhoto(parseInt(id))
      loadAllTags()
    }
  }, [id])

  const loadPhoto = async (photoId: number) => {
    setLoading(true)
    logger.info('Loading photo for annotation', { photoId })
    try {
      const result = await window.electronAPI.pythonExec('get-photo', { id: photoId })
      
      if (result?.success && result.data) {
        setPhoto(result.data as Photo)
        
        // 加载人脸
        const facesResult = await window.electronAPI.pythonExec('get-faces', { photo_id: photoId })
        if (facesResult?.success && facesResult.data) {
          setFaces(facesResult.data as Face[])
        }
        
        // 加载标签
        const tagsResult = await window.electronAPI.pythonExec('get-photo-tags', { photo_id: photoId })
        if (tagsResult?.success && tagsResult.data) {
          setTags(tagsResult.data as Tag[])
        }
      } else {
        showError('加载照片失败', result?.error)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('加载照片失败', msg)
    } finally {
      setLoading(false)
    }
  }

  const loadAllTags = async () => {
    try {
      const result = await window.electronAPI.getTags()
      setAllTags(result || [])
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('加载标签失败', msg)
    }
  }

  const handleRatingChange = async (newRating: number) => {
    if (!photo) return
    logger.debug('Setting rating', { photoId: photo.id, rating: newRating })
    try {
      await window.electronAPI.setRating(photo.id, newRating)
      setPhoto({ ...photo, rating: newRating })
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('设置评分失败', msg)
    }
  }

  const handleDetectFaces = async () => {
    if (!photo) return
    setDetecting(true)
    logger.info('Detecting faces', { photoId: photo.id })
    try {
      const result = await window.electronAPI.pythonExec('detect-faces', { photo_id: photo.id })
      if (result?.success && result.data) {
        const data = result.data as { count: number; faces: Face[] }
        setFaces(data.faces || [])
        setPhoto({ ...photo, is_portrait: data.count > 0 ? 1 : 0 })
        logger.info(`Detected ${data.count} faces`)
      } else {
        showError('人脸检测失败', result?.error)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('人脸检测失败', msg)
    } finally {
      setDetecting(false)
    }
  }

  const handleAddTag = async (tagId: number) => {
    if (!photo) return
    logger.debug('Adding tag', { photoId: photo.id, tagId })
    try {
      await window.electronAPI.addTag(photo.id, tagId)
      const tag = allTags.find(t => t.id === tagId)
      if (tag && !tags.find(t => t.id === tagId)) {
        setTags([...tags, tag])
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('添加标签失败', msg)
    }
  }

  const handleRemoveTag = async (tagId: number) => {
    if (!photo) return
    logger.debug('Removing tag', { photoId: photo.id, tagId })
    try {
      await window.electronAPI.removeTag(photo.id, tagId)
      setTags(tags.filter(t => t.id !== tagId))
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('移除标签失败', msg)
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <p className="text-gray-500">加载中...</p>
      </div>
    )
  }

  if (!photo) {
    return (
      <div className="p-6">
        <p className="text-gray-500">照片不存在</p>
        <button onClick={() => navigate('/')} className="text-blue-500 hover:underline">
          返回
        </button>
      </div>
    )
  }

  return (
    <>
      <ErrorToast error={error} onClose={clearError} />
      
      {/* 返回按钮 */}
      <button
        onClick={() => navigate('/')}
        className="mb-4 text-gray-600 hover:text-gray-800"
      >
        ← 返回
      </button>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 图片预览 */}
        <div className="lg:col-span-2 aspect-video bg-gray-100 rounded-lg overflow-hidden">
          {photo.file_path ? (
            <img
              src={`file:///${photo.file_path.replace(/\\/g, '/')}`}
              alt={photo.file_name}
              className="w-full h-full object-contain"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              {photo.file_name}
            </div>
          )}
        </div>

        {/* 标注面板 */}
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold mb-2">{photo.file_name}</h2>
            <p className="text-sm text-gray-500">{photo.taken_at || '未知时间'}</p>
          </div>

          {/* 星级 */}
          <div>
            <label className="block text-sm font-medium mb-2">评分</label>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  onClick={() => handleRatingChange(star === photo.rating ? 0 : star)}
                  className={`text-2xl ${star <= photo.rating ? 'text-yellow-400' : 'text-gray-300'}`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>

          {/* 人脸检测 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium">人脸检测</label>
              <button
                onClick={handleDetectFaces}
                disabled={detecting}
                className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
              >
                {detecting ? '检测中...' : '检测'}
              </button>
            </div>
            <div className="space-y-2">
              {faces.map((face, index) => (
                <div
                  key={face.id}
                  className="flex items-center justify-between p-2 bg-gray-50 rounded"
                >
                  <span>人脸 #{index + 1}</span>
                  <span className="text-sm text-gray-500">
                    {face.subject_name || '未命名'}
                  </span>
                </div>
              ))}
              {faces.length === 0 && (
                <p className="text-sm text-gray-400">点击「检测」识别人脸</p>
              )}
            </div>
          </div>

          {/* 标签 */}
          <div>
            <label className="block text-sm font-medium mb-2">标签</label>
            
            {/* 当前标签 */}
            <div className="flex flex-wrap gap-2 mb-2">
              {tags.map((tag) => (
                <span
                  key={tag.id}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-sm"
                  style={{ backgroundColor: tag.color + '30' }}
                >
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ backgroundColor: tag.color }}
                  />
                  {tag.name}
                  <button
                    onClick={() => handleRemoveTag(tag.id)}
                    className="ml-1 text-gray-400 hover:text-red-500"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            
            {/* 添加标签 */}
            <div className="flex flex-wrap gap-2">
              {allTags
                .filter(t => !tags.find(tag => tag.id === t.id))
                .map((tag) => (
                  <button
                    key={tag.id}
                    onClick={() => handleAddTag(tag.id)}
                    className="px-2 py-1 text-sm border rounded-full hover:bg-gray-100"
                  >
                    + {tag.name}
                  </button>
                ))}
            </div>
          </div>

          {/* 照片信息 */}
          <div className="text-sm text-gray-500 space-y-1">
            {photo.camera_model && <p>相机: {photo.camera_model}</p>}
            {photo.organized_date && <p>整理日期: {photo.organized_date}</p>}
          </div>
        </div>
      </div>
    </>
  )
}
