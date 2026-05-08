import { useNavigate } from 'react-router-dom'
import type { Photo } from '../../preload/index'

interface PhotoGridProps {
  photos: Photo[]
  loading?: boolean
}

export default function PhotoGrid({ photos, loading }: PhotoGridProps) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加载中...</div>
      </div>
    )
  }

  if (photos.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <p>暂无照片</p>
        <a
          href="/organize"
          className="mt-4 text-blue-500 hover:underline"
        >
          去整理照片
        </a>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {photos.map((photo) => (
        <div
          key={photo.id}
          onClick={() => navigate(`/photo/${photo.id}`)}
          className="aspect-square bg-gray-100 rounded-lg overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all group relative"
        >
          {photo.file_path ? (
            <img
              src={`file:///${photo.file_path.replace(/\\/g, '/')}`}
              alt={photo.file_name}
              className="w-full h-full object-cover"
              onError={(e) => {
                console.error('Image load error:', photo.file_path)
                e.currentTarget.style.display = 'none'
              }}
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400 text-sm p-2 text-center">
              {photo.file_name}
            </div>
          )}

          {/* 悬浮显示更多信息 */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-2">
            <div className="text-white text-xs">
              <div className="truncate">{photo.file_name}</div>
              {photo.rating > 0 && (
                <div className="text-yellow-400">
                  {'★'.repeat(photo.rating)}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
