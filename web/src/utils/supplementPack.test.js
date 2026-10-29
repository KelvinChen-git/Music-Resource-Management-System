import test from 'node:test'
import assert from 'node:assert/strict'
import { RETRIEVAL_SUPPLEMENT_SCHEMA, RETRIEVAL_SUPPLEMENT_SPLIT, REVIEW_SCHEMA, DIAGNOSTIC_SCHEMA,
  SOURCE_REVIEW_SCHEMA, REVIEW_SPLIT, SOURCE_REVIEW_SPLIT, loadReviewPack, reviewFingerprint,
  reviewCounts, reviewDraftKey, loadReviewDraft, exportReviewPack, sha256 } from './reviewPack.js'
import { createReviewAudio } from './reviewAudio.js'

const targets = ['exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08']
const provenanceHashes = ['source_report_sha256', 'input_catalog_sha256', 'checkpoint_sha256', 'evaluation_sha256']
const artifacts = ['corpus-manifest.json', 'queries.json', 'rankings.json', 'segments.json', 'vectors.npz']
async function seal(pack) { pack.dataset_sha256 = await reviewFingerprint(pack); return pack }
async function load(pack, owner = '42') { return loadReviewPack(JSON.stringify(pack), owner) }
function candidate(id, provider = 'incompetech') {
  const source_id = provider === 'jamendo' ? String(1000 + id) : `USXYZ${String(id).padStart(7, '0')}`
  return { track_id: String(id), source_provider: provider, source_id,
    title: `Synthetic supplement ${id} 🎵`, artist: 'Synthetic fixture only',
    source_url: provider === 'jamendo' ? `https://www.jamendo.com/track/${source_id}` : `https://incompetech.com/music/royalty-free/index.html?isrc=${source_id}`,
    license_url: 'https://creativecommons.org/licenses/by/4.0/', content_sha256: id.toString(16).padStart(64, '0'),
    content_bytes: 1234, duration_ms: 153253, model_suggested_intervals_ms: [],
    relevance: null, human_intervals_ms: null, annotator: null, judged_at: null }
}
async function fixture() {
  return seal({ schema: RETRIEVAL_SUPPLEMENT_SCHEMA, split: RETRIEVAL_SUPPLEMENT_SPLIT, owner_user_id: '42',
    provenance: { ...Object.fromEntries(provenanceHashes.map((key, index) => [key, String(index + 1).repeat(64)])),
      run_code_sha: 'b'.repeat(40), pipeline_version: 'candidate-soundfile-soxr-mono-zero-10s-hop5s-v1',
      source_decoder_version: 'soundfile-read-out-65536-actual-eof-v1',
      artifact_sha256: Object.fromEntries(artifacts.map(name => [name, 'e'.repeat(64)])),
      known_judgments_sha256: { base: 'a'.repeat(64), diagnostic: 'c'.repeat(64), source: 'd'.repeat(64) },
      supplement_query_ids: ['exp-04', 'exp-07'], selection: 'unjudged_union_whole_track_top5_and_segment_top5',
      ordering: 'query_fixture_order_then_track_id_ascending', labeling_aid: 'no_model_intervals_retrieval_supplement' },
    queries: [{ query_id: 'exp-04', text: 'Synthetic piano query.', candidates: [candidate(201)] },
      { query_id: 'exp-07', text: 'Synthetic jazz query.', candidates: [candidate(202, 'jamendo'), candidate(203)] }] })
}
function mark(row, relevance) { Object.assign(row, { relevance, annotator: 'synthetic-supplement', judged_at: '2026-10-29T01:00:00Z' }) }
async function rejectResigned(changes) {
  const original = await fixture()
  for (const [description, change] of changes) {
    const next = structuredClone(original)
    change(next)
    await assert.rejects(load(await seal(next)), undefined, description)
  }
}

test('supplement imports the independent development schema with two providers and three null judgments', async () => {
  const pack = await fixture(), before = JSON.stringify(pack), imported = await load(pack)
  assert.equal(imported.schema, RETRIEVAL_SUPPLEMENT_SCHEMA)
  assert.equal(imported.split, 'development_not_held_out')
  assert.deepEqual(reviewCounts(imported), { total: 3, judged: 0, unjudged: 3 })
  assert.ok(imported.queries.every(query => query.candidates.every(row => row.model_suggested_intervals_ms.length === 0)))
  assert.equal(JSON.stringify(pack), before)
})

test('supplement provenance enforces all exact hashes, five artifacts and three completed judgment inputs', async () => {
  await rejectResigned([
    ...provenanceHashes.flatMap(key => [
      [`missing ${key}`, pack => { delete pack.provenance[key] }],
      [`uppercase ${key}`, pack => { pack.provenance[key] = 'A'.repeat(64) }]
    ]),
    ['short source run commit', pack => { pack.provenance.run_code_sha = 'b'.repeat(39) }],
    ['unknown pipeline', pack => { pack.provenance.pipeline_version = 'another-pipeline' }],
    ['historical decoder', pack => { pack.provenance.source_decoder_version = 'soundfile-blocks-header-v1' }],
    ['missing vectors', pack => { delete pack.provenance.artifact_sha256['vectors.npz'] }],
    ['unknown artifact', pack => { pack.provenance.artifact_sha256['extra.json'] = 'a'.repeat(64) }],
    ['invalid vectors hash', pack => { pack.provenance.artifact_sha256['vectors.npz'] = 'e'.repeat(63) }],
    ['missing known source judgments', pack => { delete pack.provenance.known_judgments_sha256.source }],
    ['unknown judgment input', pack => { pack.provenance.known_judgments_sha256.other = 'a'.repeat(64) }],
    ['invalid known base hash', pack => { pack.provenance.known_judgments_sha256.base = null }],
    ['unknown provenance field', pack => { pack.provenance.base_dataset_sha256 = 'a'.repeat(64) }],
    ['old selection', pack => { pack.provenance.selection = 'union_whole_track_top5_and_segment_top5' }],
    ['model ordering', pack => { pack.provenance.ordering = 'model_score_descending' }],
    ['model suggestions enabled', pack => { pack.provenance.labeling_aid = 'model_intervals_visible_not_blind' }]
  ])
})

test('supplement query IDs form a nonempty target-ordered subset and match the package exactly', async () => {
  await rejectResigned([
    ['empty subset', pack => { pack.provenance.supplement_query_ids = []; pack.queries = [] }],
    ['non-array subset', pack => { pack.provenance.supplement_query_ids = 'exp-04' }],
    ['numeric ID', pack => { pack.provenance.supplement_query_ids[0] = 4 }],
    ['unknown query', pack => { pack.provenance.supplement_query_ids[0] = 'exp-01'; pack.queries[0].query_id = 'exp-01' }],
    ['duplicate queries', pack => { pack.provenance.supplement_query_ids[1] = 'exp-04'; pack.queries[1].query_id = 'exp-04' }],
    ['reversed subset', pack => { pack.provenance.supplement_query_ids.reverse(); pack.queries.reverse() }],
    ['query order mismatch', pack => { pack.queries.reverse() }],
    ['query count mismatch', pack => { pack.queries.pop() }],
    ['empty query text', pack => { pack.queries[0].text = '' }],
    ['extra query field', pack => { pack.queries[0].rank = 1 }],
    ['empty candidates', pack => { pack.queries[0].candidates = [] }],
    ['eleven candidates', pack => { pack.queries[0].candidates = Array.from({ length: 11 }, (_, index) => candidate(index + 1)) }],
    ['numeric ordering reversed', pack => { pack.queries[1].candidates.reverse() }]
  ])
  const maximum = await fixture()
  maximum.provenance.supplement_query_ids = targets
  maximum.queries = targets.map(query_id => ({ query_id, text: `Synthetic ${query_id}.`, candidates: Array.from({ length: 10 }, (_, index) => candidate(index + 1)) }))
  assert.deepEqual(reviewCounts(await load(await seal(maximum))), { total: 50, judged: 0, unjudged: 50 })
  const single = await fixture()
  single.provenance.supplement_query_ids.pop(); single.queries.pop()
  assert.equal((await load(await seal(single))).queries.length, 1)
})

test('supplement preserves strict provider identities, source URLs, byte bounds and actual duration bounds', async () => {
  await rejectResigned([
    ['missing provider', pack => { delete pack.queries[0].candidates[0].source_provider }],
    ['unknown provider', pack => { pack.queries[0].candidates[0].source_provider = 'other' }],
    ['lowercase ISRC', pack => { pack.queries[0].candidates[0].source_id = 'usxyz0000201' }],
    ['wrong ISRC country', pack => { pack.queries[0].candidates[0].source_id = 'U1XYZ0000201' }],
    ['wrong ISRC link', pack => { pack.queries[0].candidates[0].source_url += '&extra=1' }],
    ['old Incompetech license', pack => { pack.queries[0].candidates[0].license_url = 'https://creativecommons.org/licenses/by/3.0/' }],
    ['numeric Jamendo source', pack => { pack.queries[1].candidates[0].source_id = 1202 }],
    ['leading-zero Jamendo source', pack => { pack.queries[1].candidates[0].source_id = '01202' }],
    ['unsafe Jamendo URL', pack => { pack.queries[1].candidates[0].source_url = 'javascript:alert(1)' }],
    ['license URL credentials', pack => { pack.queries[1].candidates[0].license_url = 'https://user@creativecommons.org/licenses/by/4.0/' }],
    ['numeric track ID', pack => { pack.queries[0].candidates[0].track_id = 201 }],
    ['Java Long overflow', pack => { pack.queries[0].candidates[0].track_id = '9223372036854775808' }],
    ['zero bytes', pack => { pack.queries[0].candidates[0].content_bytes = 0 }],
    ['oversize bytes', pack => { pack.queries[0].candidates[0].content_bytes = 30 * 1024 * 1024 + 1 }],
    ['Incompetech below thirty seconds', pack => { pack.queries[0].candidates[0].duration_ms = 29999 }],
    ['Jamendo zero duration', pack => { pack.queries[1].candidates[0].duration_ms = 0 }],
    ['overlong duration', pack => { pack.queries[0].candidates[0].duration_ms = 600001 }],
    ['uppercase content hash', pack => { pack.queries[0].candidates[0].content_sha256 = 'A'.repeat(64) }],
    ['nonempty suggestions', pack => { pack.queries[0].candidates[0].model_suggested_intervals_ms = [[0, 10000]] }],
    ['null suggestions', pack => { pack.queries[0].candidates[0].model_suggested_intervals_ms = null }],
    ['extra candidate field', pack => { pack.queries[0].candidates[0].score = 1 }]
  ])
  const bounds = await fixture()
  Object.assign(bounds.queries[0].candidates[0], { content_bytes: 30 * 1024 * 1024, duration_ms: 30000 })
  Object.assign(bounds.queries[1].candidates[0], { content_bytes: 1, duration_ms: 1, license_url: 'https://creativecommons.org/licenses/by/2.5/' })
  bounds.queries[1].candidates[1].duration_ms = 600000
  await load(await seal(bounds))
})

test('same track may recur across queries with consistent metadata but never share source or content across tracks', async () => {
  const repeated = await fixture()
  repeated.queries[1].candidates.unshift(structuredClone(repeated.queries[0].candidates[0]))
  mark(repeated.queries[1].candidates[0], 2)
  assert.equal(reviewCounts(await load(await seal(repeated))).judged, 1)
  const changed = structuredClone(repeated)
  changed.queries[1].candidates[0].duration_ms++
  await assert.rejects(load(await seal(changed)))
  await rejectResigned([
    ['duplicate row in query', pack => { pack.queries[1].candidates[1] = structuredClone(pack.queries[1].candidates[0]) }],
    ['source shared across tracks', pack => { const source = pack.queries[0].candidates[0], row = pack.queries[1].candidates[1]; row.source_id = source.source_id; row.source_url = source.source_url }],
    ['content shared across tracks', pack => { pack.queries[1].candidates[0].content_sha256 = pack.queries[0].candidates[0].content_sha256 }]
  ])
})

test('supplement scoring, optional human ranges and export preserve all immutable data and null labels', async () => {
  const imported = await fixture(), before = JSON.stringify(imported), changed = structuredClone(imported)
  mark(changed.queries[0].candidates[0], 0); mark(changed.queries[1].candidates[0], 3)
  changed.queries[1].candidates[0].human_intervals_ms = [[1000, 5000], [5000, 153253]]
  assert.equal(await reviewFingerprint(changed), imported.dataset_sha256)
  const exported = await exportReviewPack(changed, '42'), restored = await loadReviewDraft(exported, imported, '42')
  assert.deepEqual(reviewCounts(restored), { total: 3, judged: 2, unjudged: 1 })
  assert.deepEqual(restored.provenance, imported.provenance)
  assert.equal(restored.queries[0].candidates[0].relevance, 0)
  assert.equal(restored.queries[1].candidates[1].relevance, null)
  assert.deepEqual(restored.queries[1].candidates[0].human_intervals_ms, [[1000, 5000], [5000, 153253]])
  assert.equal(JSON.stringify(imported), before)
  for (const [key, value] of [['relevance', true], ['relevance', '2'], ['relevance', 4], ['annotator', 'Real Name'],
    ['judged_at', '2026-02-30T00:00:00Z'], ['human_intervals_ms', []], ['human_intervals_ms', [[0, 153254]]],
    ['human_intervals_ms', [[0, 6000], [5000, 12000]]]]) {
    const pack = await fixture(), row = pack.queries[0].candidates[0]
    mark(row, 2); row[key] = value; await assert.rejects(load(await seal(pack)))
  }
  await rejectResigned([
    ['alias on null judgment', pack => { pack.queries[0].candidates[0].annotator = 'synthetic-supplement' }],
    ['range on zero relevance', pack => { const row = pack.queries[0].candidates[0]; mark(row, 0); row.human_intervals_ms = [[0, 1000]] }]
  ])
})

test('supplement drafts isolate owner, evaluation and actual duration while retaining strict size and fingerprint checks', async () => {
  const imported = await fixture(), key = reviewDraftKey('42', imported.dataset_sha256)
  await assert.rejects(load(imported, '43'))
  assert.notEqual(key, reviewDraftKey('43', imported.dataset_sha256))
  for (const change of [pack => { pack.provenance.evaluation_sha256 = 'f'.repeat(64) },
    pack => { pack.queries[0].candidates[0].duration_ms = 153555 }]) {
    const next = structuredClone(imported); change(next)
    await assert.rejects(load(next), /指纹不匹配/)
    await seal(next); await load(next) // Only the fixed-input CLI authenticates evaluation and actual duration.
    assert.notEqual(key, reviewDraftKey('42', next.dataset_sha256))
    await assert.rejects(loadReviewDraft(JSON.stringify(next), imported, '42'))
  }
  await assert.rejects(loadReviewPack(' '.repeat(2 * 1024 * 1024 + 1), '42'), /2 MiB/)
  const duplicate = JSON.stringify(imported).replace('"schema":', '"schema":"other","schema":')
  await assert.rejects(loadReviewPack(duplicate, '42'), /重复字段/)
})

test('supplement cannot disguise itself as any legacy schema or split', async () => {
  await rejectResigned([
    ...[REVIEW_SCHEMA, DIAGNOSTIC_SCHEMA, SOURCE_REVIEW_SCHEMA, 'sonora-retrieval-supplement-pack-v2'].map(schema => [schema, pack => { pack.schema = schema }]),
    ...[REVIEW_SPLIT, SOURCE_REVIEW_SPLIT, 'held_out'].map(split => [split, pack => { pack.split = split }]),
    ['extra top-level field', pack => { pack.complete = true }]
  ])
})

test('actual-duration supplement rows reuse the existing shorter-browser endpoint through fresh pause, seek and resume', async t => {
  const bytes = new Uint8Array([1, 2, 3, 4]), pack = await fixture(), row = pack.queries[0].candidates[0]
  Object.assign(row, { content_bytes: bytes.length, content_sha256: await sha256(bytes) }); await seal(pack)
  const before = JSON.stringify(pack), states = [], calls = [], revoked = []
  class Audio extends EventTarget {
    src = ''; duration = 153.2; paused = true; position = 0
    load() { if (this.src) queueMicrotask(() => this.dispatchEvent(new Event('loadedmetadata'))) }
    removeAttribute() { this.src = '' }
    pause() { this.paused = true }
    get currentTime() { return this.position }
    set currentTime(value) { this.position = value; queueMicrotask(() => this.dispatchEvent(new Event('seeked'))) }
    async play() { this.paused = false }
  }
  const audio = new Audio(), control = createReviewAudio({ audio,
    fetchMedia: async url => { calls.push(url); return new Response(bytes) }, onState: state => states.push(state),
    urls: { createObjectURL: () => `blob:synthetic-${calls.length}`, revokeObjectURL: url => revoked.push(url) } })
  t.after(() => control.stop())
  await control.start(row)
  assert.equal(states.at(-1).phase, 'playing'); assert.equal(states.at(-1).rangeEndMs, 153200)
  audio.currentTime = 100; control.pause(); assert.equal(audio.src, '')
  audio.duration = 153.15; await control.seek(120000)
  assert.equal(states.at(-1).phase, 'paused'); assert.equal(states.at(-1).rangeEndMs, 153150); assert.equal(audio.src, '')
  audio.duration = 153.1; await control.toggle()
  assert.equal(states.at(-1).phase, 'playing'); assert.equal(states.at(-1).rangeEndMs, 153100); assert.equal(audio.currentTime, 120)
  assert.deepEqual(calls, Array(3).fill('/api/music-resources/201/file'))
  await control.seek(153253)
  assert.equal(states.at(-1).positionMs, 153100); assert.equal(audio.src, ''); assert.equal(audio.paused, true)
  assert.equal(revoked.length, 3); assert.equal(JSON.stringify(pack), before)
})
