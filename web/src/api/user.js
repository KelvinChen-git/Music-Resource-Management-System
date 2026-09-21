import request from '@/utils/request'

/**
 * 获取用户列表，支持分页和条件查询
 * @param {Object} params - 查询参数，包括 current, size, username, email, role, locked
 * @returns {Promise} 包含用户列表的Promise
 */
export function getUserList(params) {
  return request({
    url: '/users',
    method: 'get',
    params
  })
}

/**
 * 获取用户详情
 * @param {number} id - 用户ID
 * @returns {Promise} 包含用户详情的Promise
 */
export function getUserDetail(id) {
  return request({
    url: `/users/${id}/detail`,
    method: 'get'
  })
}

/**
 * 创建用户
 * @param {Object} data - 用户信息
 * @returns {Promise} 创建结果的Promise
 */
export function createUser(data) {
  return request({
    url: '/users',
    method: 'post',
    data
  })
}

/**
 * 更新用户信息
 * @param {number} id - 用户ID
 * @param {Object} data - 用户信息
 * @returns {Promise} 更新结果的Promise
 */
export function updateUser(id, data) {
  return request({
    url: `/users/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除用户
 * @param {number} id - 用户ID
 * @returns {Promise} 删除结果的Promise
 */
export function deleteUser(id) {
  return request({
    url: `/users/${id}`,
    method: 'delete'
  })
}

/**
 * 锁定用户（简单锁定，无原因）
 * @param {number} id - 用户ID
 * @returns {Promise} 锁定结果的Promise
 */
export function lockUser(id) {
  return request({
    url: `/users/${id}/lock`,
    method: 'put'
  })
}

/**
 * 锁定用户（带原因）
 * @param {number} id - 用户ID
 * @param {string} reason - 锁定原因
 * @returns {Promise} 锁定结果的Promise
 */
export function lockUserWithReason(id, reason) {
  return request({
    url: `/users/${id}/lock-with-reason`,
    method: 'put',
    data: {
      userId: id,
      reason
    }
  })
}

/**
 * 解锁用户
 * @param {number} id - 用户ID
 * @returns {Promise} 解锁结果的Promise
 */
export function unlockUser(id) {
  return request({
    url: `/users/${id}/unlock`,
    method: 'put'
  })
}

/**
 * 重置用户密码
 * @param {number} id - 用户ID
 * @param {string} newPassword - 新密码
 * @returns {Promise} 重置结果的Promise
 */
export function resetUserPassword(id, newPassword) {
  return request({
    url: `/users/${id}/reset-password`,
    method: 'put',
    params: { newPassword }
  })
}

/**
 * 导出用户音乐文件(ZIP打包)
 * 下载包含用户所有音乐文件的ZIP压缩包
 * @returns {Promise} 返回文件blob的Promise对象
 */
export function exportMusicFiles() {
  return request({
    url: '/music-resources/export-music-files',
    method: 'get',
    responseType: 'blob'
  })
} 