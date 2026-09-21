/**
 * 权限工具类
 * 提供用户权限相关的工具函数
 */
import { useUserStore } from '@/stores/user'

/**
 * 检查当前用户是否为管理员
 * @returns {boolean} 如果当前用户是管理员则返回true，否则返回false
 */
export function isAdmin() {
  try {
    const userStore = useUserStore()
    
    // 检查用户是否已登录且有用户信息
    if (!userStore.token || !userStore.userInfo) {
      return false
    }
    
    // 检查用户角色是否为ADMIN
    console.log(userStore.userInfo.role === 'ADMIN');
    
    return userStore.userInfo.role === 'ADMIN'
  } catch (error) {
    console.error('检查管理员权限失败:', error)
    return false
  }
}

/**
 * 检查当前用户是否有特定权限
 * @param {string} permission 权限名称或代码
 * @returns {boolean} 如果当前用户有指定权限则返回true，否则返回false
 */
export function hasPermission(permission) {
  try {
    // 管理员默认拥有所有权限
    if (isAdmin()) {
      return true
    }
    
    // 这里可以根据实际需求扩展其他角色的权限判断逻辑
    // 例如从用户信息中获取权限列表并检查
    
    return false
  } catch (error) {
    console.error('检查权限失败:', error)
    return false
  }
}

/**
 * 获取当前用户ID
 * @returns {number|null} 当前用户ID，未登录时返回null
 */
export function getCurrentUserId() {
  try {
    const userStore = useUserStore()
    return userStore.userInfo?.userid || null
  } catch (error) {
    console.error('获取用户ID失败:', error)
    return null
  }
}

/**
 * 判断当前用户是否可以编辑特定资源
 * @param {Object} resource 资源对象，必须包含userid或uploaderId属性
 * @returns {boolean} 如果用户可以编辑该资源则返回true，否则返回false
 */
export function canEdit(resource) {
  try {
    // 管理员可以编辑任何资源
    if (isAdmin()) {
      return true
    }
    
    // 获取当前用户ID
    const currentUserId = getCurrentUserId()
    if (!currentUserId) {
      return false
    }
    
    // 检查资源是否属于当前用户
    const resourceOwnerId = resource.userid || (resource.uploader?.userid)
    return currentUserId === resourceOwnerId
  } catch (error) {
    console.error('检查编辑权限失败:', error)
    return false
  }
} 