import request from '@/utils/request'

/**
 * 获取回收站设置
 * @returns {Promise} 返回包含设置信息的Promise
 */
export function getRecycleBinSettings() {
  return request({
    url: '/admin/recycle-bin/settings', // 注意 URL 路径
    method: 'get'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to get recycle bin settings'))
    }
  })
}

/**
 * 更新回收站设置
 * @param {Object} settingsData - 新的设置数据
 * @param {number} settingsData.defaultRetentionDays - 默认保留天数
 * @param {boolean} settingsData.autoCleanupEnabled - 是否启用自动清理
 * @param {string} settingsData.autoCleanupTime - 自动清理时间 (HH:mm:ss)
 * @returns {Promise} 返回操作结果的Promise
 */
export function updateRecycleBinSettings(settingsData) {
  return request({
    url: '/admin/recycle-bin/settings', // 注意 URL 路径
    method: 'put',
    data: settingsData
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to update recycle bin settings'))
    }
  })
}

/**
 * 重置回收站设置为默认值
 * @returns {Promise<Object>} 重置结果
 */
export function resetRecycleBinSettings() {
  return request({
    url: '/recyclebin/settings/reset',
    method: 'post'
  })
}

/**
 * 获取回收站统计信息
 * @returns {Promise<Object>} 回收站统计数据
 */
export function getRecycleBinStats() {
  return request({
    url: '/recyclebin/stats',
    method: 'get'
  })
}

/**
 * 获取回收站内容列表
 * @param {Object} params 查询参数
 * @returns {Promise<Object>} 回收站项目列表
 */
export function getRecycleBinItems(params) {
  return request({
    url: '/recyclebin/items',
    method: 'get',
    params
  })
}

/**
 * 还原回收站项目
 * @param {Array<number>|number} ids 项目ID或ID数组
 * @returns {Promise<Object>} 还原结果
 */
export function restoreRecycleBinItems(ids) {
  const data = Array.isArray(ids) ? { ids } : { ids: [ids] }
  return request({
    url: '/recyclebin/restore',
    method: 'post',
    data
  })
}

/**
 * 永久删除回收站项目
 * @param {Array<number>|number} ids 项目ID或ID数组
 * @returns {Promise<Object>} 删除结果
 */
export function deleteRecycleBinItems(ids) {
  const data = Array.isArray(ids) ? { ids } : { ids: [ids] }
  return request({
    url: '/recyclebin/delete',
    method: 'delete',
    data
  })
}

/**
 * 清空回收站
 * @returns {Promise<Object>} 清空结果
 */
export function emptyRecycleBin() {
  return request({
    url: '/recyclebin/empty',
    method: 'delete'
  })
} 