import request from '@/utils/request'

// 获取音乐资源列表
export function getMusicList(params) {
  return request({
    url: '/music-resources/list',
    method: 'get',
    params
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取音乐列表失败'))
    }
  })
}

// 获取音乐资源详情
export function getMusicDetail(id) {
  return request({
    url: `/music-resources/${id}`,
    method: 'get'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取音乐详情失败'))
    }
  })
}

// 更新音乐资源信息
export function updateMusic(id, data) {
  return request({
    url: `/music-resources/${id}`,
    method: 'put',
    data
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '更新音乐信息失败'))
    }
  })
}

// 删除音乐资源
export function deleteMusic(id, deleteNote) {
  return request({
    url: `/music-resources/${id}`,
    method: 'delete',
    params: deleteNote ? { deleteNote } : {}
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '删除音乐失败'))
    }
  })
}

// 解析音乐元数据
export function parseMusicMetadata(fileId) {
  return request({
    url: '/music-resources/metadata',
    method: 'post',
    params: { fileId }
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '解析音乐元数据失败'))
    }
  })
}

// 保存音乐元数据
export function saveMusicMetadata(fileId, metadata) {
  return request({
    url: '/music-resources/metadata',
    method: 'post',
    params: { fileId },
    data: metadata
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '保存音乐元数据失败'))
    }
  })
}

// 审核音乐
export function approveMusic(id) {
  return request({
    url: `/music-resources/${id}/approve`,
    method: 'post'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '审核音乐失败'))
    }
  })
}

// 下载音乐文件
export function downloadMusic(id, filename) {
  return request({
    url: `/music-resources/${id}/file`,
    method: 'get',
    responseType: 'blob'
  }).then(res => {
    // 创建下载链接
    const blob = new Blob([res.data], { type: 'audio/mpeg' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    // 清理
    window.URL.revokeObjectURL(url)
    document.body.removeChild(link)
  }).catch(error => {
    return Promise.reject(new Error(error.message || '下载音乐失败'))
  })
}

// 创建音乐播放URL
export async function createMusicUrl(id, pay = false) {
  try {
    let url = `/api/music-resources/${id}/file`;
    if (pay) {
      url += '?pay=1';
    }
    const response = await fetch(url, {
      headers: {
        'Accept': 'audio/mpeg, audio/*'
      }
    })
    if (!response.ok) {
      throw new Error('获取音频失败')
    }

    const contentType = response.headers.get('content-type') || 'audio/mpeg'
    const blob = await response.blob()
    const audioBlob = new Blob([blob], { type: contentType })
    return URL.createObjectURL(audioBlob)
  } catch (error) {
    console.error('创建音频URL失败:', error)
    throw new Error('创建音频URL失败')
  }
}

// 获取音乐资源列表（包含已删除选项）
export function getMusicListWithDeleted(params) {
  return request({
    url: '/music-resources/list-with-deleted',
    method: 'get',
    params
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取音乐列表失败'))
    }
  })
}

/**
 * 拒绝音乐资源审核
 * @param {number} id 音乐资源ID
 * @returns {Promise} 返回操作结果
 */
export function rejectMusic(id) {
  return request({
    url: `/music-resources/${id}/reject`,
    method: 'post'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to reject music resource'))
    }
  })
}