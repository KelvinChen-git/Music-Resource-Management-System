import test from 'node:test'
import assert from 'node:assert/strict'
import { DIAGNOSTIC_SCHEMA, REVIEW_SCHEMA, REVIEW_SPLIT, loadReviewPack, reviewFingerprint,
  reviewCounts, reviewDraftKey, loadReviewDraft, exportReviewPack } from './reviewPack.js'

async function seal(pack) { pack.dataset_sha256 = await reviewFingerprint(pack); return pack }
async function load(pack, owner = '42') { return loadReviewPack(JSON.stringify(pack), owner) }
async function fixture(count = 12) {
  const candidates = Array.from({ length: count }, (_, index) => {
    const id = index + 1, source = 1000 + id
    return { track_id: String(id), source_id: String(source), title: `Synthetic diagnostic ${id} 🎵`,
      artist: 'Synthetic fixture only', source_url: `https://www.jamendo.com/track/${source}`,
      license_url: 'https://creativecommons.org/licenses/by/4.0/', content_sha256: id.toString(16).padStart(64, '0'),
      content_bytes: 1234, duration_ms: 12000, model_suggested_intervals_ms: [],
      relevance: null, human_intervals_ms: null, annotator: null, judged_at: null }
  })
  return seal({ schema: DIAGNOSTIC_SCHEMA, split: REVIEW_SPLIT, owner_user_id: '42',
    provenance: { source_report_sha256: 'a'.repeat(64), run_code_sha: 'b'.repeat(40),
      input_catalog_sha256: 'c'.repeat(64), checkpoint_sha256: 'd'.repeat(64), pipeline_version: 'synthetic-diagnostic-only',
      artifact_sha256: Object.fromEntries(['corpus-manifest.json', 'queries.json', 'rankings.json', 'segments.json'].map(name => [name, 'e'.repeat(64)])),
      selection: 'unjudged_complement_for_selected_queries', ordering: 'query_fixture_order_then_track_id_ascending',
      labeling_aid: 'no_model_intervals_for_diagnostic_complement', base_judgments_sha256: 'f'.repeat(64),
      base_dataset_sha256: '1'.repeat(64), diagnostic_query_ids: ['diagnostic-q1', 'diagnostic-q2'] },
    queries: ['diagnostic-q1', 'diagnostic-q2'].map(query_id => ({ query_id,
      text: `Synthetic unjudged-complement query ${query_id}.`, candidates: structuredClone(candidates) })) })
}
async function oldFixture(count) {
  const pack = await fixture(count)
  pack.schema = REVIEW_SCHEMA
  for (const field of ['base_judgments_sha256', 'base_dataset_sha256', 'diagnostic_query_ids']) delete pack.provenance[field]
  pack.provenance.selection = 'union_whole_track_top5_and_segment_top5'
  pack.provenance.labeling_aid = 'model_intervals_visible_not_blind'
  return seal(pack)
}
function mark(row, relevance) {
  Object.assign(row, { relevance, annotator: 'synthetic-diagnostic', judged_at: '2026-10-28T01:00:00Z' })
}
async function rejectResigned(changes) {
  const original = await fixture()
  for (const [description, change] of changes) {
    const next = structuredClone(original)
    change(next)
    await assert.rejects(load(await seal(next)), undefined, description)
  }
}

test('diagnostic schema imports more than ten candidates with null human fields and no suggestions', async () => {
  const pack = await fixture(), before = JSON.stringify(pack)
  const imported = await load(pack)
  assert.equal(imported.schema, DIAGNOSTIC_SCHEMA)
  assert.equal(imported.queries[0].candidates.length, 12)
  assert.deepEqual(reviewCounts(imported), { total: 24, judged: 0, unjudged: 24 })
  assert.ok(imported.queries.every(query => query.candidates.every(row => row.model_suggested_intervals_ms.length === 0)))
  assert.equal(JSON.stringify(pack), before)
  assert.equal((await load(await fixture(100))).queries[0].candidates.length, 100)
  await assert.rejects(load(await fixture(101)))
  await assert.rejects(load(await fixture(0)))
})

test('old schema keeps exact provenance and ten-candidate limit', async () => {
  assert.equal((await load(await oldFixture(10))).schema, REVIEW_SCHEMA)
  await assert.rejects(load(await oldFixture(11)))
  const old = await oldFixture(2)
  old.queries[0].candidates[0].model_suggested_intervals_ms = [[0, 10000]]
  await load(await seal(old))
  for (const field of ['base_judgments_sha256', 'base_dataset_sha256', 'diagnostic_query_ids']) {
    const next = structuredClone(old)
    next.provenance[field] = field === 'diagnostic_query_ids' ? ['diagnostic-q1', 'diagnostic-q2'] : 'f'.repeat(64)
    await assert.rejects(load(await seal(next)))
  }
  const disguised = await fixture(2)
  disguised.schema = REVIEW_SCHEMA
  await assert.rejects(load(await seal(disguised)))
})

test('diagnostic provenance requires exact fields, fixed modes and lowercase SHA256 values even after resigning', async () => {
  await rejectResigned([
    ['missing base judgments hash', pack => { delete pack.provenance.base_judgments_sha256 }],
    ['missing base dataset hash', pack => { delete pack.provenance.base_dataset_sha256 }],
    ['missing selected queries', pack => { delete pack.provenance.diagnostic_query_ids }],
    ['unknown provenance field', pack => { pack.provenance.unknown = 'self-consistent' }],
    ['uppercase base hash', pack => { pack.provenance.base_judgments_sha256 = 'A'.repeat(64) }],
    ['short base hash', pack => { pack.provenance.base_dataset_sha256 = 'a'.repeat(63) }],
    ['invalid input catalog hash', pack => { pack.provenance.input_catalog_sha256 = 'not-a-hash' }],
    ['unknown artifact', pack => { pack.provenance.artifact_sha256['other.json'] = 'a'.repeat(64) }],
    ['old selection mode', pack => { pack.provenance.selection = 'union_whole_track_top5_and_segment_top5' }],
    ['wrong ordering', pack => { pack.provenance.ordering = 'model_score_descending' }],
    ['model aid enabled', pack => { pack.provenance.labeling_aid = 'model_intervals_visible_not_blind' }],
    ['wrong split', pack => { pack.split = 'held_out' }],
    ['unknown schema', pack => { pack.schema = 'sonora-diagnostic-pack-v2' }]
  ])
})

test('diagnostic query list is one to twenty unique string IDs exactly aligned with query order', async () => {
  await rejectResigned([
    ['empty list', pack => { pack.provenance.diagnostic_query_ids = [] }],
    ['non-array list', pack => { pack.provenance.diagnostic_query_ids = 'diagnostic-q1' }],
    ['numeric ID', pack => { pack.provenance.diagnostic_query_ids[0] = 1 }],
    ['empty ID', pack => { pack.provenance.diagnostic_query_ids[0] = '' }],
    ['duplicate IDs', pack => { pack.provenance.diagnostic_query_ids[1] = 'diagnostic-q1' }],
    ['different count', pack => { pack.provenance.diagnostic_query_ids.pop() }],
    ['wrong order', pack => { pack.provenance.diagnostic_query_ids.reverse() }],
    ['unknown ID', pack => { pack.provenance.diagnostic_query_ids[0] = 'another-query' }],
    ['duplicate query', pack => { pack.queries[1].query_id = pack.queries[0].query_id }],
    ['twenty-one aligned IDs', pack => {
      pack.queries = Array.from({ length: 21 }, (_, index) => ({ ...structuredClone(pack.queries[0]), query_id: `q${index}` }))
      pack.provenance.diagnostic_query_ids = pack.queries.map(query => query.query_id)
    }]
  ])
  const single = await fixture(1)
  single.queries.pop(); single.provenance.diagnostic_query_ids.pop()
  assert.equal((await load(await seal(single))).queries.length, 1)
  const twenty = await fixture(1)
  twenty.queries = Array.from({ length: 20 }, (_, index) => ({ ...structuredClone(twenty.queries[0]), query_id: `q${index}` }))
  twenty.provenance.diagnostic_query_ids = twenty.queries.map(query => query.query_id)
  assert.equal((await load(await seal(twenty))).queries.length, 20)
})

test('diagnostic suggestions remain empty and candidate identity, URLs, bounds and metadata remain strict', async () => {
  await rejectResigned([
    ['suggested range forbidden', pack => { pack.queries[0].candidates[0].model_suggested_intervals_ms = [[0, 10000]] }],
    ['null suggestions forbidden', pack => { pack.queries[0].candidates[0].model_suggested_intervals_ms = null }],
    ['numeric track ID', pack => { pack.queries[0].candidates[0].track_id = 1 }],
    ['leading zero ID', pack => { pack.queries[0].candidates[0].track_id = '01' }],
    ['unsorted candidates', pack => { pack.queries[0].candidates.reverse() }],
    ['duplicate candidates', pack => { pack.queries[0].candidates[1] = structuredClone(pack.queries[0].candidates[0]) }],
    ['inconsistent repeated metadata', pack => { pack.queries[1].candidates[0].duration_ms++ }],
    ['duplicate source identity', pack => {
      const row = pack.queries[0].candidates[1]; row.source_id = '1001'; row.source_url = 'https://www.jamendo.com/track/1001'
    }],
    ['duplicate content identity', pack => { pack.queries[0].candidates[1].content_sha256 = pack.queries[0].candidates[0].content_sha256 }],
    ['unsafe source URL', pack => { pack.queries[0].candidates[0].source_url = 'javascript:alert(1)' }],
    ['license URL credentials', pack => { pack.queries[0].candidates[0].license_url = 'https://user@creativecommons.org/licenses/by/4.0/' }],
    ['zero content bytes', pack => { pack.queries[0].candidates[0].content_bytes = 0 }],
    ['duration exceeds limit', pack => { pack.queries[0].candidates[0].duration_ms = 600001 }],
    ['extra candidate field', pack => { pack.queries[0].candidates[0].score = 1 }],
    ['extra top-level field', pack => { pack.complete = true }]
  ])
})

test('diagnostic judgments export and restore without altering source, provenance or dataset fingerprint', async () => {
  const imported = await fixture(), before = JSON.stringify(imported), changed = structuredClone(imported)
  const zero = changed.queries[0].candidates[0], positive = changed.queries[0].candidates[1]
  mark(zero, 0); mark(positive, 3); positive.human_intervals_ms = [[1000, 5000], [5000, 12000]]
  assert.equal(await reviewFingerprint(changed), imported.dataset_sha256)
  const exported = await exportReviewPack(changed, '42'), restored = await loadReviewDraft(exported, imported, '42')
  assert.equal(restored.schema, DIAGNOSTIC_SCHEMA)
  assert.deepEqual(restored.provenance, imported.provenance)
  assert.deepEqual(restored.queries[0].candidates[1].human_intervals_ms, [[1000, 5000], [5000, 12000]])
  assert.deepEqual(reviewCounts(restored), { total: 24, judged: 2, unjudged: 22 })
  assert.equal(restored.queries[0].candidates[0].relevance, 0)
  assert.equal(restored.queries[1].candidates[0].relevance, null)
  assert.equal(JSON.stringify(imported), before)
})

test('diagnostic drafts isolate owner, base judgment file, query selection and old-schema packages', async () => {
  const pack = await fixture(), originalKey = reviewDraftKey('42', pack.dataset_sha256)
  assert.notEqual(originalKey, reviewDraftKey('43', pack.dataset_sha256))
  await assert.rejects(load(pack, '43'))
  const changedBase = structuredClone(pack)
  changedBase.provenance.base_judgments_sha256 = '2'.repeat(64)
  await seal(changedBase)
  assert.notEqual(originalKey, reviewDraftKey('42', changedBase.dataset_sha256))
  await assert.rejects(loadReviewDraft(JSON.stringify(changedBase), pack, '42'))
  const selected = structuredClone(pack)
  selected.queries.pop(); selected.provenance.diagnostic_query_ids.pop(); await seal(selected)
  assert.notEqual(originalKey, reviewDraftKey('42', selected.dataset_sha256))
  await assert.rejects(loadReviewDraft(JSON.stringify(selected), pack, '42'))
  const old = await oldFixture(10)
  assert.notEqual(originalKey, reviewDraftKey('42', old.dataset_sha256))
  await assert.rejects(loadReviewDraft(JSON.stringify(old), pack, '42'))
  const changedCandidate = structuredClone(pack)
  changedCandidate.queries.forEach(query => { query.candidates[0].title = 'Altered but internally consistent title' })
  await seal(changedCandidate)
  await load(changedCandidate) // Only the pinned-run CLI authenticates candidate origin.
  await assert.rejects(loadReviewDraft(JSON.stringify(changedCandidate), pack, '42'))
})

test('diagnostic human-field validation remains strict and import still enforces byte and fingerprint limits', async () => {
  for (const [field, value] of [['relevance', true], ['relevance', '2'], ['relevance', 4],
    ['annotator', 'Personal Name'], ['judged_at', '2026-02-30T00:00:00Z'], ['human_intervals_ms', [[0, 12001]]],
    ['human_intervals_ms', [[0, 6000], [5000, 12000]]]]) {
    const pack = await fixture(), row = pack.queries[0].candidates[0]
    mark(row, 2); row[field] = value
    await assert.rejects(load(await seal(pack)))
  }
  const unjudged = await fixture()
  unjudged.queries[0].candidates[0].annotator = 'synthetic-diagnostic'
  await assert.rejects(load(await seal(unjudged)))
  const zero = await fixture()
  mark(zero.queries[0].candidates[0], 0); zero.queries[0].candidates[0].human_intervals_ms = [[0, 1000]]
  await assert.rejects(load(await seal(zero)))
  const wrongFingerprint = await fixture()
  wrongFingerprint.provenance.base_dataset_sha256 = '3'.repeat(64)
  await assert.rejects(load(wrongFingerprint), /指纹不匹配/)
  await assert.rejects(loadReviewPack(' '.repeat(2 * 1024 * 1024 + 1), '42'), /2 MiB/)
})
