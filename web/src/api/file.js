import request from '@/utils/request'

// 创建文件记录
export function createFile(data) {
  return request({
    url: '/file/create',
    method: 'post',
    data
  })
}

// 检查文件是否已存在（秒传）
export function checkFile(fileMd5) {
  return request({
    url: '/file/check',
    method: 'get',
    params: { fileMd5 }
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '文件检查失败'))
    }
  })
}

// 上传分片
export function uploadChunk(data) {
  return request({
    url: '/file/chunk',
    method: 'post',
    data,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '分片上传失败'))
    }
  })
}

// 合并分片
export function mergeChunks(fileId) {
  return request({
    url: '/file/merge',
    method: 'post',
    params: { fileId }
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '文件合并失败'))
    }
  })
}

// 获取文件缺失的分片
export function getMissingChunks(fileId) {
  return request({
    url: '/file/missing-chunks',
    method: 'get',
    params: { fileId }
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取缺失分片失败'))
    }
  })
}

// 获取文件列表
export function getFileList(params) {
  return request({
    url: '/file/list',
    method: 'get',
    params
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取文件列表失败'))
    }
  })
}

// 删除文件
export function deleteFile(fileId) {
  return request({
    url: `/file/${fileId}`,
    method: 'delete'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '删除文件失败'))
    }
  })
}

// 获取文件详情
export function getFileDetail(fileId) {
  return request({
    url: `/file/${fileId}`,
    method: 'get'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取文件详情失败'))
    }
  })
}

// 获取文件上传状态
export function getUploadStatus(fileId) {
  return request({
    url: `/file/status/${fileId}`,
    method: 'get'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取上传状态失败'))
    }
  })
}

// 解析并保存音乐元数据
export function parseAndSaveMetadata(fileId, metadata = null) {
  return request({
    url: '/music-resources/metadata',
    method: 'post',
    params: { fileId },
    data: metadata,
    headers: {
      'Content-Type': 'application/json'
    }
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '处理音乐元数据失败'))
    }
  })
} 