// Local exploratory packages. Final provenance still needs the pinned-run Python CLI.
export const REVIEW_SCHEMA = 'sonora-judgment-pack-v1'
export const DIAGNOSTIC_SCHEMA = 'sonora-diagnostic-pack-v1'
export const SOURCE_REVIEW_SCHEMA = 'sonora-source-review-pack-v1'
export const SOURCE_REVIEW_SPLIT = 'development_source_candidates_not_held_out'
export const REVIEW_SPLIT = 'exploratory_only_not_held_out'
const human = ['relevance', 'human_intervals_ms', 'annotator', 'judged_at']
const artifacts = ['corpus-manifest.json', 'queries.json', 'rankings.json', 'segments.json']
const candidateFields = ['track_id', 'source_id', 'title', 'artist', 'source_url', 'license_url',
  'content_sha256', 'content_bytes', 'duration_ms', 'model_suggested_intervals_ms', ...human]
function ensure(ok, message = '标注包格式或内容不符合约定。') { if (!ok) throw new Error(message) }
function object(value, keys) {
  ensure(value && typeof value === 'object' && !Array.isArray(value))
  ensure(Object.keys(value).sort().join('|') === [...keys].sort().join('|'))
}
function int(value, min, max) { ensure(Number.isSafeInteger(value) && value >= min && value <= max) }
function text(value, max) {
  ensure(typeof value === 'string' && value.length > 0 && [...value].length <= max && value.trim() === value && !/[\u0000-\u001f\ud800-\udfff]/u.test(value))
}
function hash(value) { ensure(typeof value === 'string' && /^[a-f0-9]{64}$/.test(value)) }
export function reviewId(value) {
  ensure(typeof value === 'string' && /^[1-9][0-9]{0,18}$/.test(value) && BigInt(value) <= 9223372036854775807n, '账号或曲目 ID 无效。')
  return value
}
export function validAlias(value) { return typeof value === 'string' && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/.test(value) }
export function checkRange(range, duration) {
  ensure(Array.isArray(range) && range.length === 2, '人工区间需填写起点与终点。')
  ensure(Number.isSafeInteger(range[0]) && Number.isSafeInteger(range[1]) && range[0] >= 0 && range[0] < range[1] && range[1] <= duration, '区间超出曲目时长，或起止时间无效。')
}
function checkHuman(row) {
  if (row.relevance === null) {
    ensure(human.every(key => row[key] === null), '未判断条目的人工字段必须保持为空。')
    return
  }
  int(row.relevance, 0, 3)
  ensure(validAlias(row.annotator), '请填写匿名标注代号（字母、数字、点、横线或下划线）。')
  ensure(typeof row.judged_at === 'string' && /^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$/.test(row.judged_at))
  const stamp = new Date(row.judged_at)
  ensure(Number.isFinite(stamp.getTime()) && stamp.getUTCFullYear() > 0 && stamp.toISOString() === row.judged_at.replace('Z', '.000Z'))
  if (row.human_intervals_ms !== null) {
    ensure(row.relevance > 0 && Array.isArray(row.human_intervals_ms) && row.human_intervals_ms.length >= 1 && row.human_intervals_ms.length <= 20)
    let end = -1
    for (const range of row.human_intervals_ms) {
      checkRange(range, row.duration_ms); ensure(range[0] >= end); end = range[1]
    }
  }
}
export function strictReviewJson(raw) {
  ensure(typeof raw === 'string' && new TextEncoder().encode(raw).length <= 2 * 1024 * 1024, '文件需为不超过 2 MiB 的 JSON。')
  const value = JSON.parse(raw)
  // JSON.parse alone silently accepts duplicate keys and loses integer/float spelling.
  const tokens = raw.match(/"(?:\\[\s\S]|[^"\\])*"|[{}\[\]:,]|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g) || []
  const stack = []
  for (const token of tokens) {
    const parent = stack.at(-1)
    if (token === '{') stack.push({ keys: new Set(), key: true })
    else if (token === '[') stack.push(null)
    else if (token === '}' || token === ']') stack.pop()
    else if (token === ',' && parent) parent.key = true
    else if (token === ':' && parent) parent.key = false
    else if (token.startsWith('"') && parent?.key) {
      const key = JSON.parse(token); ensure(!parent.keys.has(key), 'JSON 含重复字段。')
      parent.keys.add(key); parent.key = false
    } else if (/^-?\d/.test(token)) ensure(!/[.eE]/.test(token), '数字字段必须为整数。')
  }
  return value
}
export function canonicalReview(value) {
  if (Array.isArray(value)) return '[' + value.map(canonicalReview).join(',') + ']'
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonicalReview(value[key])).join(',') + '}'
  return JSON.stringify(value)
}
export function reviewBase(pack, includeFingerprint = true) {
  const value = JSON.parse(JSON.stringify(pack))
  for (const query of value.queries) for (const row of query.candidates) for (const key of human) row[key] = null
  if (!includeFingerprint) delete value.dataset_sha256
  return value
}
export async function sha256(bytes) {
  const result = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(result), byte => byte.toString(16).padStart(2, '0')).join('')
}
export async function reviewFingerprint(pack) { return sha256(new TextEncoder().encode(canonicalReview(reviewBase(pack, false)))) }
function checkSourceReviewShape(pack, owner) {
  ensure(pack.split === SOURCE_REVIEW_SPLIT, '新素材核查包不能改为正式测试集。')
  reviewId(pack.owner_user_id); reviewId(String(owner))
  ensure(pack.owner_user_id === String(owner), '该标注包属于另一个账号，请使用对应账号。')
  hash(pack.dataset_sha256)
  const p = pack.provenance
  const hashes = ['source_manifest_sha256', 'import_catalog_sha256', 'decode_report_sha256', 'source_selection_sha256', 'query_fixture_sha256']
  object(p, [...hashes, 'selection', 'ordering', 'labeling_aid'])
  for (const key of hashes) hash(p[key])
  ensure(p.selection === 'targeted_source_candidates_by_metadata'
    && p.ordering === 'query_fixture_order_then_track_id_ascending'
    && p.labeling_aid === 'no_model_intervals_source_qualification')
  const queryIds = ['exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08']
  ensure(Array.isArray(pack.queries) && pack.queries.length === queryIds.length)
  const tracks = new Set(), sources = new Set(), contents = new Set()
  for (const [index, query] of pack.queries.entries()) {
    object(query, ['query_id', 'text', 'candidates']); text(query.text, 1000)
    ensure(query.query_id === queryIds[index])
    ensure(Array.isArray(query.candidates) && query.candidates.length === 4)
    let previous = 0n
    for (const row of query.candidates) {
      object(row, [...candidateFields, 'source_provider']); reviewId(row.track_id)
      ensure(BigInt(row.track_id) > previous); previous = BigInt(row.track_id)
      ensure(row.source_provider === 'incompetech' && typeof row.source_id === 'string' && /^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$/.test(row.source_id))
      text(row.title, 500); text(row.artist, 500); hash(row.content_sha256)
      int(row.content_bytes, 1, 30 * 1024 * 1024); int(row.duration_ms, 1, 600000)
      ensure(row.source_url === `https://incompetech.com/music/royalty-free/index.html?isrc=${row.source_id}`)
      ensure(row.license_url === 'https://creativecommons.org/licenses/by/4.0/')
      ensure(Array.isArray(row.model_suggested_intervals_ms) && row.model_suggested_intervals_ms.length === 0)
      checkHuman(row)
      ensure(!tracks.has(row.track_id) && !sources.has(row.source_id) && !contents.has(row.content_sha256))
      tracks.add(row.track_id); sources.add(row.source_id); contents.add(row.content_sha256)
    }
  }
  return pack
}
export function checkReviewShape(pack, owner) {
  object(pack, ['schema', 'split', 'owner_user_id', 'provenance', 'queries', 'dataset_sha256'])
  if (pack.schema === SOURCE_REVIEW_SCHEMA) return checkSourceReviewShape(pack, owner)
  const diagnostic = pack.schema === DIAGNOSTIC_SCHEMA
  ensure((pack.schema === REVIEW_SCHEMA || diagnostic) && pack.split === REVIEW_SPLIT, '只接受探索标注包，不能改为正式测试集。')
  reviewId(pack.owner_user_id); reviewId(String(owner))
  ensure(pack.owner_user_id === String(owner), '该标注包属于另一个账号，请使用对应账号。')
  hash(pack.dataset_sha256)
  const p = pack.provenance
  object(p, ['source_report_sha256', 'run_code_sha', 'input_catalog_sha256', 'checkpoint_sha256', 'pipeline_version', 'artifact_sha256', 'selection', 'ordering', 'labeling_aid',
    ...(diagnostic ? ['base_judgments_sha256', 'base_dataset_sha256', 'diagnostic_query_ids'] : [])])
  for (const key of ['source_report_sha256', 'input_catalog_sha256', 'checkpoint_sha256']) hash(p[key])
  ensure(typeof p.run_code_sha === 'string' && /^[a-f0-9]{40}$/.test(p.run_code_sha)); text(p.pipeline_version, 200)
  object(p.artifact_sha256, artifacts); for (const value of Object.values(p.artifact_sha256)) hash(value)
  ensure(p.selection === (diagnostic ? 'unjudged_complement_for_selected_queries' : 'union_whole_track_top5_and_segment_top5')
    && p.ordering === 'query_fixture_order_then_track_id_ascending'
    && p.labeling_aid === (diagnostic ? 'no_model_intervals_for_diagnostic_complement' : 'model_intervals_visible_not_blind'))
  ensure(Array.isArray(pack.queries) && pack.queries.length >= 1 && pack.queries.length <= 20)
  if (diagnostic) {
    hash(p.base_judgments_sha256); hash(p.base_dataset_sha256)
    ensure(Array.isArray(p.diagnostic_query_ids) && p.diagnostic_query_ids.length >= 1 && p.diagnostic_query_ids.length <= 20)
    for (const id of p.diagnostic_query_ids) text(id, 100)
    ensure(new Set(p.diagnostic_query_ids).size === p.diagnostic_query_ids.length)
    ensure(p.diagnostic_query_ids.length === pack.queries.length)
  }
  const queryIds = new Set(), tracks = new Map(), sources = new Map(), contents = new Map()
  for (const [index, query] of pack.queries.entries()) {
    object(query, ['query_id', 'text', 'candidates']); text(query.query_id, 100); text(query.text, 1000)
    ensure(!queryIds.has(query.query_id)); queryIds.add(query.query_id)
    if (diagnostic) ensure(query.query_id === p.diagnostic_query_ids[index])
    ensure(Array.isArray(query.candidates) && query.candidates.length >= 1 && query.candidates.length <= (diagnostic ? 100 : 10))
    let previous = 0n
    for (const row of query.candidates) {
      object(row, candidateFields); reviewId(row.track_id); reviewId(row.source_id)
      ensure(BigInt(row.track_id) > previous); previous = BigInt(row.track_id)
      text(row.title, 500); text(row.artist, 500); hash(row.content_sha256)
      int(row.content_bytes, 1, 30 * 1024 * 1024); int(row.duration_ms, 1, 600000)
      ensure(row.source_url === `https://www.jamendo.com/track/${row.source_id}`)
      ensure(typeof row.license_url === 'string' && /^https:\/\/creativecommons\.org\/licenses\/by\/(2\.0|2\.5|3\.0|4\.0)\/$/.test(row.license_url))
      ensure(Array.isArray(row.model_suggested_intervals_ms) && row.model_suggested_intervals_ms.length <= (diagnostic ? 0 : 3))
      const ranges = new Set()
      for (const range of row.model_suggested_intervals_ms) { checkRange(range, row.duration_ms); ensure(!ranges.has(String(range))); ranges.add(String(range)) }
      checkHuman(row)
      const metadata = { ...row }; for (const field of [...human, 'model_suggested_intervals_ms']) delete metadata[field]
      const identity = canonicalReview(metadata)
      ensure(!tracks.has(row.track_id) || tracks.get(row.track_id) === identity)
      ensure(!sources.has(row.source_id) || sources.get(row.source_id) === row.track_id)
      ensure(!contents.has(row.content_sha256) || contents.get(row.content_sha256) === row.track_id)
      tracks.set(row.track_id, identity); sources.set(row.source_id, row.track_id); contents.set(row.content_sha256, row.track_id)
    }
  }
  return pack
}
export async function loadReviewPack(raw, owner) {
  const pack = checkReviewShape(strictReviewJson(raw), owner)
  ensure(await reviewFingerprint(pack) === pack.dataset_sha256, '候选内容指纹不匹配，请用原运行重新生成标注包。')
  return pack
}
export async function exportReviewPack(pack, owner) {
  return JSON.stringify(await loadReviewPack(JSON.stringify(pack), owner), null, 2) + '\n'
}
export function reviewDraftKey(owner, fingerprint) { reviewId(String(owner)); hash(fingerprint); return `sonora:review:${owner}:${fingerprint}:v1` }
export async function loadReviewDraft(raw, imported, owner) {
  const draft = await loadReviewPack(raw, owner)
  ensure(canonicalReview(reviewBase(draft)) === canonicalReview(reviewBase(imported)), '本机草稿与当前候选包不一致。')
  return draft
}
export function reviewCounts(pack) {
  const rows = pack.queries.flatMap(query => query.candidates)
  const judged = rows.filter(row => row.relevance !== null).length
  return { total: rows.length, judged, unjudged: rows.length - judged }
}
