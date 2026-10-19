// Binary requests use the same stored JWT as the JSON API client.
export async function fetchMedia(url, options = {}) {
  if (typeof url !== 'string' || !url.startsWith('/api/')) {
    throw new Error('Invalid media URL')
  }
  const token = localStorage.getItem('token') || sessionStorage.getItem('token')
  if (!token) throw new Error('Please log in to access media')
  const headers = new Headers(options.headers)
  headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(url, { ...options, headers, cache: 'no-store', redirect: 'error' })
  if (!response.ok) {
    const message = response.status === 401 ? 'Please log in again'
      : response.status === 403 ? 'Media access denied'
        : response.status === 404 ? 'Media is unavailable' : 'Media request failed'
    throw new Error(message)
  }
  return response
}
