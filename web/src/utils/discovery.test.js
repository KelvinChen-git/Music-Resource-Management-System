import test from 'node:test'
import assert from 'node:assert/strict'
import { discoveryResults, discoveryMediaUrl } from './discovery.js'

function fixture() {
  const md5 = 'a'.repeat(32), sha = 'b'.repeat(64)
  return { engine_kind: 'synthetic_fixture', retrieval_mode: 'segment', index_version: 'test-v1', model_version: 'test-v1',
    results: [{ track_id: '9007199254740993', title: '<script>plain text</script>', artist: 'Synthetic', duration_ms: 25000,
      content_md5: md5, content_sha256: sha, content_bytes: 1234, score: .7,
      preview_url: `/api/discovery/tracks/9007199254740993/media?content_md5=${md5}&content_sha256=${sha}`,
      segments: [{ segment_id: 'a', start_ms: 10000, end_ms: 20000, score: .7 }] }] }
}
test('preserves large string IDs, explicit fixture marker and local fingerprint URL', () => {
  const value = fixture(), result = discoveryResults(value)
  assert.equal(result.results[0].track_id, '9007199254740993')
  assert.equal(result.engine_kind, 'synthetic_fixture')
  assert.equal(discoveryMediaUrl(result.results[0]), value.results[0].preview_url)
  assert.notEqual(result.results[0].segments[0], value.results[0].segments[0])
})
test('empty results are a valid success', () => { assert.deepEqual(discoveryResults({ ...fixture(), results: [] }).results, []) })
test('rejects remote, broader old media and altered preview URLs', () => {
  for (const url of ['https://example.invalid/file', '/api/music-resources/42/file', '/api/discovery/tracks/42/media']) {
    const value = fixture(); value.results[0].preview_url = url
    assert.throws(() => discoveryResults(value))
  }
})
test('rejects duplicates, nonfinite scores and invalid times before playback', () => {
  for (const mutate of [x => { x.results.push(x.results[0]) }, x => { x.results[0].score = NaN },
    x => { x.results[0].segments[0].end_ms = 25001 }, x => { x.results[0].segments[0].start_ms = -1 },
    x => { x.results[0].segments.push({ segment_id: 'b', start_ms: 15000, end_ms: 21000, score: .5 }) }]) {
    const value = fixture(); mutate(value); assert.throws(() => discoveryResults(value))
  }
})
test('rejects unsupported mode/model markers and malformed hashes', () => {
  for (const mutate of [x => { x.retrieval_mode = 'hybrid' }, x => { x.engine_kind = 'unknown' },
    x => { x.results[0].content_sha256 = 'bad' }, x => { x.model_version = '' }]) {
    const value = fixture(); mutate(value); assert.throws(() => discoveryResults(value))
  }
})
