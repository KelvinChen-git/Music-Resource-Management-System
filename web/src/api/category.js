import request from '@/utils/request'

// 获取分类列表
export function getCategoryList(params) {
  return request({
    url: '/music-categories',
    method: 'get',
    params
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取分类列表失败'))
    }
  })
}

// 获取分类详情
export function getCategoryDetail(id) {
  return request({
    url: `/music-categories/${id}`,
    method: 'get'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '获取分类详情失败'))
    }
  })
}

// 创建分类
export function createCategory(data) {
  return request({
    url: '/music-categories',
    method: 'post',
    data
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '创建分类失败'))
    }
  })
}

// 更新分类
export function updateCategory(id, data) {
  return request({
    url: `/music-categories/${id}`,
    method: 'put',
    data
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '更新分类失败'))
    }
  })
}

// 删除分类
export function deleteCategory(id) {
  return request({
    url: `/music-categories/${id}`,
    method: 'delete'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || '删除分类失败'))
    }
  })
} 