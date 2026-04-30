import { useState, useEffect, Component } from 'react'
import { History, CheckCircle, XCircle, Clock, ChevronRight, FileText, Filter, X, ZoomIn } from 'lucide-react'
import type { ImportRecord, ImportItem } from '../../preload/index'

// 图片放大查看组件
function ImageViewer({ src, title, onClose }: { src: string; title: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="absolute top-4 right-4">
        <button onClick={onClose} className="p-2 bg-white rounded-full hover:bg-gray-200">
          <X className="w-6 h-6" />
        </button>
      </div>
      <div className="max-w-4xl max-h-[90vh]">
        <div className="text-white text-center mb-2">{title}</div>
        <img
          src={src}
          alt={title}
          className="max-w-full max-h-[85vh] object-contain"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
    </div>
  )
}

// 错误边界组件
class ErrorBoundary extends Component<{children: React.ReactNode}, {hasError: boolean, error?: Error}> {
  constructor(props: {children: React.ReactNode}) {
    super(props)
    this.state = { hasError: false }
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }
  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ImportHistory] ErrorBoundary caught:', error, errorInfo)
  }
  render() {
    if (this.state.hasError) {
      return <div className="p-4 text-red-500">页面崩溃: {this.state.error?.message}</div>
    }
    return this.props.children
  }
}

function ImportHistoryContent() {
  const [records, setRecords] = useState<ImportRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRecord, setSelectedRecord] = useState<ImportRecord | null>(null)
  const [items, setItems] = useState<ImportItem[]>([])
  const [filter, setFilter] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)
  const [viewerImage, setViewerImage] = useState<{ src: string; title: string } | null>(null)

  useEffect(() => {
    console.log('[ImportHistory] component mounted, filter:', filter)
    loadHistory()
  }, [filter])

  const loadHistory = async () => {
    console.log('[ImportHistory] loading history, filter:', filter)
    setLoading(true)
    setError(null)
    try {
      const status = filter === 'all' ? undefined : filter
      console.log('[ImportHistory] calling getImportHistory API')
      const history = await window.electronAPI.getImportHistory(50, 0, status)
      console.log('[ImportHistory] got history:', history, 'type:', typeof history)
      // 确保返回数组，不是数组则用空数组
      const arr = Array.isArray(history) ? history : []
      setRecords(arr)
      if (arr.length === 0) {
        setError('暂无导入记录')
      }
    } catch (err) {
      console.error('[ImportHistory] Failed to load import history:', err)
      // API 失败时显示空记录，不崩溃
      setRecords([])
      setError('服务未就绪，请重试')
    } finally {
      setLoading(false)
    }
  }

  const loadItems = async (importId: number) => {
    try {
      const result = await window.electronAPI.getImportItems(importId)
      setItems(result || [])
    } catch (err) {
      console.error('Failed to load import items:', err)
    }
  }

  const handleRecordClick = (record: ImportRecord) => {
    setSelectedRecord(record)
    loadItems(record.id)
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-500" />
      case 'running':
        return <Clock className="w-5 h-5 text-blue-500 animate-pulse" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  const getActionColor = (action: string) => {
    switch (action) {
      case 'added':
        return 'bg-green-100 text-green-700'
      case 'skipped':
        return 'bg-yellow-100 text-yellow-700'
      case 'updated':
        return 'bg-blue-100 text-blue-700'
      case 'failed':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  return (
    <div className="h-full flex">
      {/* 错误提示 */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded z-50">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-2 font-bold">&times;</button>
        </div>
      )}

      {/* 左侧列表 */}
      <div className="w-1/2 border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-xl font-semibold flex items-center gap-2">
              <History className="w-6 h-6" />
              导入历史
            </h1>
            <button
              onClick={loadHistory}
              className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
            >
              刷新
            </button>
          </div>

          {/* 筛选 */}
          <div className="flex gap-2">
            {['all', 'completed', 'failed', 'running'].map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFilter(f)
                  setSelectedRecord(null)
                }}
                className={`px-3 py-1 text-sm rounded ${
                  filter === f
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 hover:bg-gray-200'
                }`}
              >
                {f === 'all' ? '全部' : f === 'completed' ? '成功' : f === 'failed' ? '失败' : '进行中'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">加载中...</div>
          ) : records.length === 0 ? (
            <div className="p-4 text-center text-gray-500">暂无导入记录</div>
          ) : (
            <div className="divide-y divide-gray-100">
              {records.map((record) => (
                <div
                  key={record.id}
                  onClick={() => handleRecordClick(record)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 ${
                    selectedRecord?.id === record.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        {getStatusIcon(record.status)}
                        <span className="font-medium">
                          {record.success_count + record.skip_count + record.fail_count} 个文件
                        </span>
                      </div>
                      <div className="text-sm text-gray-500 space-y-1">
                        <div className="truncate" title={record.source_path}>
                          源: {record.source_path}
                        </div>
                        <div className="truncate" title={record.dest_path}>
                          目标: {record.dest_path}
                        </div>
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {formatDate(record.created_at)}
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 flex flex-col">
        {!selectedRecord ? (
          <div className="flex-1 flex items-center justify-center text-gray-400">
            <div className="text-center">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>选择一条记录查看详情</p>
            </div>
          </div>
        ) : (
          <>
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold mb-2">导入详情</h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">源目录:</span>
                  <div className="font-mono text-xs truncate" title={selectedRecord.source_path}>
                    {selectedRecord.source_path}
                  </div>
                </div>
                <div>
                  <span className="text-gray-500">目标目录:</span>
                  <div className="font-mono text-xs truncate" title={selectedRecord.dest_path}>
                    {selectedRecord.dest_path}
                  </div>
                </div>
                <div>
                  <span className="text-gray-500">整理模式:</span>
                  <span className="ml-2">{selectedRecord.mode}</span>
                </div>
                <div>
                  <span className="text-gray-500">去重模式:</span>
                  <span className="ml-2">{selectedRecord.duplicate_mode}</span>
                </div>
                <div>
                  <span className="text-gray-500">成功:</span>
                  <span className="ml-2 text-green-600">{selectedRecord.success_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">跳过:</span>
                  <span className="ml-2 text-yellow-600">{selectedRecord.skip_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">失败:</span>
                  <span className="ml-2 text-red-600">{selectedRecord.fail_count}</span>
                </div>
                <div>
                  <span className="text-gray-500">时间:</span>
                  <span className="ml-2">{formatDate(selectedRecord.created_at)}</span>
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <h3 className="font-medium mb-3">文件明细</h3>
              {items.length === 0 ? (
                <div className="text-center text-gray-500 py-8">暂无数据</div>
              ) : (
                <div className="space-y-2">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className="p-3 bg-gray-50 rounded text-sm"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="font-mono text-xs truncate" title={item.file_path}>
                            {item.file_path}
                          </div>
                          {/* 重复文件：同时显示原路径和目标路径 */}
                          {item.action === 'skipped' && item.organized_path && (
                            <div className="text-xs text-gray-500 mt-1">
                              <span className="text-gray-400">目标:</span> {item.organized_path}
                            </div>
                          )}
                          {item.reason && (
                            <div className="text-gray-500 text-xs mt-1">{item.reason}</div>
                          )}
                          {item.error_msg && (
                            <div className="text-red-500 text-xs mt-1">{item.error_msg}</div>
                          )}
                        </div>
                        <span className={`px-2 py-1 rounded text-xs ${getActionColor(item.action)}`}>
                          {item.action === 'added' ? '新增' : 
                           item.action === 'skipped' ? '跳过' : 
                           item.action === 'updated' ? '更新' : '失败'}
                        </span>
                      </div>
                      
                      {/* 重复文件对比显示 */}
                      {item.action === 'skipped' && item.organized_path && (
                        <div className="mt-3 pt-3 border-t border-gray-200">
                          <div className="text-xs text-gray-500 mb-2">对比原图与已存在图片：</div>
                          <div className="flex gap-4">
                            {/* 原文件 */}
                            <div className="flex-1">
                              <div className="text-xs text-gray-500 mb-1">原文件</div>
                              <div
                                className="relative cursor-pointer group"
                                onClick={() => setViewerImage({ src: `file:///${item.file_path.replace(/\\/g, '/')}`, title: '原文件' })}
                              >
                                <img
                                  src={`file:///${item.file_path.replace(/\\/g, '/')}`}
                                  alt="原文件"
                                  className="w-full h-24 object-cover rounded bg-gray-200 group-hover:opacity-80"
                                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                                />
                                <ZoomIn className="absolute inset-0 m-auto w-6 h-6 text-gray-400 opacity-0 group-hover:opacity-100" />
                              </div>
                            </div>
                            {/* 已存在文件 */}
                            <div className="flex-1">
                              <div className="text-xs text-gray-500 mb-1">已存在</div>
                              <div
                                className="relative cursor-pointer group"
                                onClick={() => setViewerImage({ src: `file:///${item.organized_path.replace(/\\/g, '/')}`, title: '已存在文件' })}
                              >
                                <img
                                  src={`file:///${item.organized_path.replace(/\\/g, '/')}`}
                                  alt="已存在"
                                  className="w-full h-24 object-cover rounded bg-gray-200 group-hover:opacity-80"
                                  onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }}
                                />
                                <ZoomIn className="absolute inset-0 m-auto w-6 h-6 text-gray-400 opacity-0 group-hover:opacity-100" />
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* 图片放大查看 */}
            {viewerImage && (
              <ImageViewer
                src={viewerImage.src}
                title={viewerImage.title}
                onClose={() => setViewerImage(null)}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}

// 带错误边界的导出
export default function ImportHistory() {
  return (
    <ErrorBoundary>
      <ImportHistoryContent />
    </ErrorBoundary>
  )
}
