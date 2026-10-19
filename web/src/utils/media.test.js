import { beforeEach, test } from 'node:test'
import assert from 'node:assert/strict'
import { fetchMedia } from './media.js'

let localToken, sessionToken, calls
beforeEach(() => {
  localToken = 'local-token'
  sessionToken = null
  calls = []
  globalThis.localStorage = { getItem: () => localToken }
  globalThis.sessionStorage = { getItem: () => sessionToken }
  globalThis.fetch = async (...args) => { calls.push(args); return new Response('audio', { status: 200 }) }
})

test('binary request sends local JWT and disables caching', async () => {
  await fetchMedia('/api/music-resources/42/file')
  const [url, options] = calls[0]
  assert.equal(url, '/api/music-resources/42/file')
  assert.equal(options.headers.get('Authorization'), 'Bearer local-token')
  assert.equal(options.cache, 'no-store')
  assert.equal(options.redirect, 'error')
})
test('session-only login also authorizes media', async () => {
  localToken = null
  sessionToken = 'session-token'
  await fetchMedia('/api/file/download/9')
  assert.equal(calls[0][1].headers.get('Authorization'), 'Bearer session-token')
})
test('logged-out requests fail before fetching', async () => {
  localToken = null
  await assert.rejects(fetchMedia('/api/music-resources/42/file'), /log in/)
  assert.equal(calls.length, 0)
})
test('media cannot send bearer tokens to external URLs', async () => {
  await assert.rejects(fetchMedia('https://example.com/file'), /Invalid/)
  await assert.rejects(fetchMedia('//example.com/file'), /Invalid/)
  assert.equal(calls.length, 0)
})
test('abort signals and range headers survive authorization', async () => {
  const controller = new AbortController()
  await fetchMedia('/api/music-resources/42/file', { signal: controller.signal, headers: { Range: 'bytes=0-7' } })
  assert.equal(calls[0][1].signal, controller.signal)
  assert.equal(calls[0][1].headers.get('Range'), 'bytes=0-7')
})
test('denied HTTP responses cannot become playable blobs', async () => {
  for (const status of [401, 403, 404, 500]) {
    globalThis.fetch = async () => new Response('', { status })
    await assert.rejects(fetchMedia('/api/music-resources/42/file'))
  }
})
