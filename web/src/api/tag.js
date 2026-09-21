import request from '@/utils/request'

// 创建标签
export function createTag(data) {
  return request({
    url: '/tags',
    method: 'post',
    data
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to create tag'))
    }
  })
}

// 获取标签列表（分页）
export function getTagList(params) {
  return request({
    url: '/tags',
    method: 'get',
    params
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to get tag list'))
    }
  })
}

// 更新标签
export function updateTag(tagId, data) {
  return request({
    url: `/tags/${tagId}`,
    method: 'put',
    data
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to update tag'))
    }
  })
}

// 删除标签
export function deleteTag(tagId) {
  return request({
    url: `/tags/${tagId}`,
    method: 'delete'
  }).then(res => {
    if (res.code === 200) {
      return res
    } else {
      return Promise.reject(new Error(res.message || 'Failed to delete tag'))
    }
  })
} 