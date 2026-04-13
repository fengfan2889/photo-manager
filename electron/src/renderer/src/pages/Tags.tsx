import { useEffect, useState } from 'react'
import { logger } from '../utils/logger'
import { ErrorToast } from '../components/ErrorToast'
import { useError } from '../hooks/useError'

interface Tag {
  id: number
  name: string
  color: string
}

export default function Tags() {
  const [tags, setTags] = useState<Tag[]>([])
  const [loading, setLoading] = useState(true)
  const [newTagName, setNewTagName] = useState('')
  const [newTagColor, setNewTagColor] = useState('#808080')
  const { error, showError, clearError } = useError()

  useEffect(() => {
    logger.info('Tags page mounted')
    loadTags()
  }, [])

  const loadTags = async () => {
    setLoading(true)
    try {
      const result = await window.electronAPI.pythonExec('get-tags', {})
      if (result?.success) {
        setTags(result.data || [])
      } else {
        showError('加载标签失败', result?.error)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('加载标签失败', msg)
    } finally {
      setLoading(false)
    }
  }

  const createTag = async () => {
    if (!newTagName.trim()) return

    logger.debug('Creating tag', { name: newTagName, color: newTagColor })

    try {
      const result = await window.electronAPI.pythonExec('create-tag', {
        name: newTagName.trim(),
        color: newTagColor
      })

      if (result?.success) {
        setNewTagName('')
        setNewTagColor('#808080')
        loadTags()
      } else {
        showError('创建标签失败', result?.error)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('创建标签失败', msg)
    }
  }

  const deleteTag = async (id: number) => {
    if (!confirm('确定要删除这个标签吗？')) return

    logger.debug('Deleting tag', { id })

    try {
      const result = await window.electronAPI.pythonExec('delete-tag', { id })
      if (result?.success) {
        loadTags()
      } else {
        showError('删除标签失败', result?.error)
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error)
      showError('删除标签失败', msg)
    }
  }

  return (
    <>
      <ErrorToast error={error} onClose={clearError} />
      
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">标签管理</h1>
        </div>

        {/* 添加标签 */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <h2 className="text-lg font-medium mb-4">添加新标签</h2>
          <div className="flex gap-4">
            <input
              type="text"
              value={newTagName}
              onChange={(e) => setNewTagName(e.target.value)}
              placeholder="标签名称"
              className="flex-1 px-3 py-2 border rounded-lg"
              onKeyDown={(e) => e.key === 'Enter' && createTag()}
            />
            <input
              type="color"
              value={newTagColor}
              onChange={(e) => setNewTagColor(e.target.value)}
              className="w-12 h-10 border rounded cursor-pointer"
            />
            <button
              onClick={createTag}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
            >
              添加
            </button>
          </div>
        </div>

        {/* 标签列表 */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <h2 className="text-lg font-medium">已有标签 ({tags.length})</h2>
          </div>

          {loading ? (
            <div className="p-8 text-center text-gray-500">加载中...</div>
          ) : tags.length === 0 ? (
            <div className="p-8 text-center text-gray-500">暂无标签</div>
          ) : (
            <div className="p-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {tags.map((tag) => (
                <div
                  key={tag.id}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100"
                >
                  <div className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: tag.color }}
                    />
                    <span className="text-sm">{tag.name}</span>
                  </div>
                  <button
                    onClick={() => deleteTag(tag.id)}
                    className="text-gray-400 hover:text-red-500"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}
