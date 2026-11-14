import request from '@/utils/request'

export function searchDiscovery(data, signal) {
  return request({ url: '/discovery/search', method: 'post', data, signal })
}
