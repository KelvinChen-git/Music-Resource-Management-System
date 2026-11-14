import { reviewId, checkRange } from './reviewPack.js'

const fail = () => { throw new Error('检索结果格式无效，请刷新后重试。') }
const hash = (value, size) => typeof value === 'string' && new RegExp(`^[a-f0-9]{${size}}$`).test(value)
const score = value => Number.isFinite(value) && Math.abs(value) <= 1.00001

export function discoveryMediaUrl(row) {
  reviewId(row.track_id)
  if (!hash(row.content_md5, 32) || !hash(row.content_sha256, 64)) fail()
  const expected = `/api/discovery/tracks/${row.track_id}/media?content_md5=${row.content_md5}&content_sha256=${row.content_sha256}`
  if (row.preview_url !== expected) fail()
  return expected
}

/** Validate before rendering or fetching; IDs always remain decimal strings. */
export function discoveryResults(data) {
  if (!data || !['clap_identity', 'synthetic_fixture'].includes(data.engine_kind)
      || !['segment', 'whole_track'].includes(data.retrieval_mode)
      || !Array.isArray(data.results) || data.results.length > 20) fail()
  for (const key of ['index_version', 'model_version']) {
    if (typeof data[key] !== 'string' || !/^[A-Za-z0-9._:-]{1,160}$/.test(data[key])) fail()
  }
  const ids = new Set()
  const results = data.results.map(row => {
    reviewId(row.track_id)
    if (ids.has(row.track_id) || typeof row.title !== 'string' || typeof row.artist !== 'string'
        || !Number.isSafeInteger(row.duration_ms) || row.duration_ms <= 0
        || !Number.isSafeInteger(row.content_bytes) || row.content_bytes <= 0 || row.content_bytes > 30 * 1024 * 1024
        || !score(row.score) || !Array.isArray(row.segments) || row.segments.length < 1 || row.segments.length > 3) fail()
    ids.add(row.track_id); discoveryMediaUrl(row)
    const seen = new Set(), prior = []
    const segments = row.segments.map(segment => {
      if (typeof segment.segment_id !== 'string' || !/^[A-Za-z0-9._:-]{1,100}$/.test(segment.segment_id)
          || seen.has(segment.segment_id) || !score(segment.score)) fail()
      checkRange([segment.start_ms, segment.end_ms], row.duration_ms)
      if (prior.some(s => Math.max(s.start_ms, segment.start_ms) < Math.min(s.end_ms, segment.end_ms))) fail()
      seen.add(segment.segment_id); prior.push(segment)
      return { ...segment }
    })
    return { ...row, segments }
  })
  return { ...data, results }
}
