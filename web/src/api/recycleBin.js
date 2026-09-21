import request from '@/utils/request'

/**
 * 获取回收站音乐列表
 * @param {Object} params - 查询参数
 * @param {string} params.title - 音乐标题（可选）
 * @param {string} params.artist - 艺术家（可选）
 * @param {number} params.current - 当前页码
 * @param {number} params.pageSize - 每页记录数
 * @returns {Promise} - 返回回收站列表数据
 */
export function getRecycleBinList(params) {
  return request({
    url: '/recycle-bin/list',
    method: 'get',
    params
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to get recycle bin list'))
    }
  })
}

/**
 * 从回收站恢复音乐资源
 * @param {number} id - 回收站记录ID
 * @returns {Promise} - 返回恢复后的音乐资源数据
 */
export function restoreFromRecycleBin(id) {
  return request({
    url: `/recycle-bin/${id}/restore`,
    method: 'post'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to restore music resource'))
    }
  })
}

/**
 * 从回收站永久删除音乐资源
 * @param {number} id - 回收站记录ID
 * @returns {Promise} - 返回删除结果
 */
export function deleteFromRecycleBin(id) {
  return request({
    url: `/recycle-bin/${id}`,
    method: 'delete'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to permanently delete music resource'))
    }
  })
}

/**
 * 清空回收站
 * @returns {Promise} - 返回清空结果
 */
export function emptyRecycleBin() {
  return request({
    url: '/recycle-bin/empty',
    method: 'delete'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to empty recycle bin'))
    }
  })
}

/**
 * 获取回收站统计数据
 * @returns {Promise} - 返回统计数据
 */
export function getRecycleBinStats() {
  return request({
    url: '/recycle-bin/stats',
    method: 'get'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to get recycle bin statistics'))
    }
  })
}

/**
 * 清空当前用户自己的回收站项目
 * @returns {Promise} 包含删除数量的Promise
 */
export function emptyMyRecycleBin() {
  return request({
    url: '/recycle-bin/empty-mine', // 确保这个 URL 与您后端 Controller 中的 @DeleteMapping 匹配
    method: 'delete'
  })
} 