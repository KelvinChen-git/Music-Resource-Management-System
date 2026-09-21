import request from '@/utils/request'

/**
 * 用户登录
 * @param {Object} data - 登录信息
 * @param {string} data.email - 用户邮箱
 * @param {string} data.password - 用户密码
 * @returns {Promise} 返回包含token的Promise对象
 */
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

/**
 * 用户注册
 * @param {Object} data - 注册信息
 * @param {string} data.email - 用户邮箱
 * @param {string} data.password - 用户密码
 * @param {string} data.name - 用户名
 * @returns {Promise} 返回包含用户信息的Promise对象
 */
export function register(data) {
  return request({
    url: '/auth/register',
    method: 'post',
    data
  })
}

/**
 * 获取当前用户信息
 * @returns {Promise} 返回包含用户信息的Promise对象
 */
export function getProfile() {
  return request({
    url: '/auth/profile',
    method: 'get'
  })
}

/**
 * 修改密码
 * @param {Object} data - 密码信息
 * @param {string} data.oldPassword - 旧密码
 * @param {string} data.newPassword - 新密码
 * @param {string} data.confirmPassword - 确认新密码
 * @returns {Promise} 返回包含操作结果的Promise对象
 */
export function changePassword(data) {
  return request({
    url: '/auth/change-password',
    method: 'post',
    data
  })
}

/**
 * 退出登录
 * @returns {Promise} 返回Promise对象
 */
export function logout() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}

export function getInfo() {
  return request({
    url: '/auth/info',
    method: 'get'
  })
}

/**
 * 导出用户账户数据
 * 下载包含用户基本信息的 JSON 文件
 * @returns {Promise} 返回数据 blob 的 Promise 对象
 */
export function exportAccountData() {
  return request({
    url: '/users/export-account-data',
    method: 'get',
    responseType: 'blob'
  })
}

/**
 * 导出用户音乐数据
 * 下载包含用户上传的音乐信息的 JSON 文件
 * @returns {Promise} 返回数据 blob 的 Promise 对象
 */
export function exportMusicData() {
  return request({
    url: '/music-resources/export-music-data',
    method: 'get',
    responseType: 'blob'
  })
}

/**
 * 导出所有用户数据
 * 下载包含用户账户和音乐数据的完整 JSON 文件
 * @returns {Promise} 返回数据 blob 的 Promise 对象
 */
export function exportAllData() {
  return request({
    url: '/users/export-all-data',
    method: 'get',
    responseType: 'blob'
  })
}

/**
 * 删除用户账户
 * 完全删除当前用户的账户及相关数据
 * @returns {Promise} 返回操作结果的 Promise 对象
 */
export function deleteAccount() {
  return request({
    url: '/users/delete-account',
    method: 'delete'
  })
}

/**
 * Update current user's profile information
 * @param {Object} data - Profile data
 * @param {string} [data.name] - New username
 * @param {string} [data.avatar] - New avatar path/URL
 * @returns {Promise} Promise object representing the operation result
 */
export function updateProfile(data) {
  return request({
    url: '/auth/profile',
    method: 'put',
    data
  })
}

/**
 * Upload an avatar image
 * @param {File} file - The avatar image file
 * @returns {Promise} Promise object containing the upload result (expected: { data: { filePath: string } })
 */
export function uploadAvatar(file) {
  const formData = new FormData()
  formData.append('file', file)

  return request({
    url: '/file/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * Request a password reset code to be sent via email.
 * @param {Object} data - Email data
 * @param {string} data.email - The user's email address.
 * @returns {Promise} Promise object representing the operation result.
 */
export function forgotPassword(data) {
  return request({
    url: '/auth/forgot-password',
    method: 'post',
    data
  })
}

/**
 * Reset the user's password using the verification code.
 * @param {Object} data - Reset password data
 * @param {string} data.email - User's email
 * @param {string} data.code - Verification code received via email
 * @param {string} data.newPassword - The new password
 * @param {string} data.confirmPassword - Confirmation of the new password
 * @returns {Promise} Promise object representing the operation result.
 */
export function resetPassword(data) {
  return request({
    url: '/auth/reset-password',
    method: 'post',
    data
  })
} 