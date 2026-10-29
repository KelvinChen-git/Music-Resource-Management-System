import test from 'node:test'
import assert from 'node:assert/strict'
import { SOURCE_REVIEW_SCHEMA, SOURCE_REVIEW_SPLIT, REVIEW_SCHEMA, DIAGNOSTIC_SCHEMA, REVIEW_SPLIT,
  loadReviewPack, reviewFingerprint, reviewCounts, reviewDraftKey, loadReviewDraft, exportReviewPack } from './reviewPack.js'

const queryIds = ['exp-02', 'exp-03', 'exp-04', 'exp-07', 'exp-08']
const provenanceHashes = ['source_manifest_sha256', 'import_catalog_sha256', 'decode_report_sha256', 'source_selection_sha256', 'query_fixture_sha256']
async function seal(pack) { pack.dataset_sha256 = await reviewFingerprint(pack); return pack }
async function load(pack, owner = '42') { return loadReviewPack(JSON.stringify(pack), owner) }
async function fixture() {
  return seal({ schema: SOURCE_REVIEW_SCHEMA, split: SOURCE_REVIEW_SPLIT, owner_user_id: '42',
    provenance: { ...Object.fromEntries(provenanceHashes.map((key, index) => [key, (index + 1).toString(16).repeat(64)])),
      selection: 'targeted_source_candidates_by_metadata', ordering: 'query_fixture_order_then_track_id_ascending',
      labeling_aid: 'no_model_intervals_source_qualification' },
    queries: queryIds.map((query_id, queryIndex) => ({ query_id, text: `Synthetic source qualification ${query_id} 🎵`,
      candidates: Array.from({ length: 4 }, (_, index) => {
        const id = queryIndex * 4 + index + 1, source_id = `USXYZ${String(id).padStart(7, '0')}`
        return { track_id: String(1999000000000000000n + BigInt(id)), source_provider: 'incompetech', source_id,
          title: `Synthetic source ${id}`, artist: 'Synthetic fixture only',
          source_url: `https://incompetech.com/music/royalty-free/index.html?isrc=${source_id}`,
          license_url: 'https://creativecommons.org/licenses/by/4.0/', content_sha256: id.toString(16).padStart(64, '0'),
          content_bytes: 1234, duration_ms: 60000, model_suggested_intervals_ms: [],
          relevance: null, human_intervals_ms: null, annotator: null, judged_at: null }
      }) })) })
}
function mark(row, relevance) { Object.assign(row, { relevance, annotator: 'synthetic-source', judged_at: '2026-10-28T01:00:00Z' }) }
async function rejectResigned(changes) {
  const original = await fixture()
  for (const [description, change] of changes) {
    const next = structuredClone(original)
    change(next)
    await assert.rejects(load(await seal(next)), undefined, description)
  }
}
async function oldFixture(schema = REVIEW_SCHEMA, count = 2) {
  const source = await fixture(), candidates = source.queries.flatMap(query => query.candidates).slice(0, count)
  candidates.forEach((row, index) => {
    delete row.source_provider; row.track_id = String(index + 1); row.source_id = String(index + 101)
    row.source_url = `https://www.jamendo.com/track/${row.source_id}`
  })
  return seal({ schema, split: REVIEW_SPLIT, owner_user_id: '42',
    provenance: { source_report_sha256: 'a'.repeat(64), run_code_sha: 'b'.repeat(40), input_catalog_sha256: 'c'.repeat(64),
      checkpoint_sha256: 'd'.repeat(64), pipeline_version: 'synthetic-regression-only',
      artifact_sha256: Object.fromEntries(['corpus-manifest.json', 'queries.json', 'rankings.json', 'segments.json'].map(name => [name, 'e'.repeat(64)])),
      selection: schema === DIAGNOSTIC_SCHEMA ? 'unjudged_complement_for_selected_queries' : 'union_whole_track_top5_and_segment_top5',
      ordering: 'query_fixture_order_then_track_id_ascending',
      labeling_aid: schema === DIAGNOSTIC_SCHEMA ? 'no_model_intervals_for_diagnostic_complement' : 'model_intervals_visible_not_blind',
      ...(schema === DIAGNOSTIC_SCHEMA ? { base_judgments_sha256: 'f'.repeat(64), base_dataset_sha256: '1'.repeat(64), diagnostic_query_ids: ['old-synthetic'] } : {}) },
    queries: [{ query_id: 'old-synthetic', text: 'Synthetic regression query.', candidates }] })
}

test('source review imports exactly twenty independent null judgments with string Java Long IDs', async () => {
  const pack = await fixture(), before = JSON.stringify(pack), imported = await load(pack)
  assert.equal(imported.schema, SOURCE_REVIEW_SCHEMA)
  assert.equal(imported.split, SOURCE_REVIEW_SPLIT)
  assert.deepEqual(imported.queries.map(query => query.query_id), queryIds)
  assert.deepEqual(reviewCounts(imported), { total: 20, judged: 0, unjudged: 20 })
  assert.ok(imported.queries.every(query => query.candidates.length === 4))
  assert.ok(imported.queries.flatMap(query => query.candidates).every(row => BigInt(row.track_id) > BigInt(Number.MAX_SAFE_INTEGER)))
  assert.equal(JSON.stringify(pack), before)
})

test('source provenance has only five pinned SHA256 inputs and exact source qualification modes', async () => {
  const changes = provenanceHashes.flatMap(key => [
    [`missing ${key}`, pack => { delete pack.provenance[key] }],
    [`uppercase ${key}`, pack => { pack.provenance[key] = 'A'.repeat(64) }],
    [`short ${key}`, pack => { pack.provenance[key] = 'a'.repeat(63) }]
  ])
  await rejectResigned([...changes,
    ['invented checkpoint', pack => { pack.provenance.checkpoint_sha256 = 'a'.repeat(64) }],
    ['invented source report', pack => { pack.provenance.source_report_sha256 = 'a'.repeat(64) }],
    ['invented run SHA', pack => { pack.provenance.run_code_sha = 'b'.repeat(40) }],
    ['model selection', pack => { pack.provenance.selection = 'union_whole_track_top5_and_segment_top5' }],
    ['model ordering', pack => { pack.provenance.ordering = 'model_score_descending' }],
    ['model labeling aid', pack => { pack.provenance.labeling_aid = 'model_intervals_visible_not_blind' }]
  ])
})

test('source schema and development split cannot be disguised as an old package or formal test set', async () => {
  await rejectResigned([
    ['old E1 schema', pack => { pack.schema = REVIEW_SCHEMA }],
    ['old diagnostic schema', pack => { pack.schema = DIAGNOSTIC_SCHEMA }],
    ['unknown schema', pack => { pack.schema = 'sonora-source-review-pack-v2' }],
    ['old split', pack => { pack.split = REVIEW_SPLIT }],
    ['test split', pack => { pack.split = 'held_out' }],
    ['extra top-level field', pack => { pack.complete = true }]
  ])
})

test('source queries require the five fixed IDs in fixture order with four candidates each', async () => {
  await rejectResigned([
    ['four queries', pack => { pack.queries.pop() }],
    ['six queries', pack => { pack.queries.push(structuredClone(pack.queries[0])) }],
    ['reversed queries', pack => { pack.queries.reverse() }],
    ['unknown query', pack => { pack.queries[0].query_id = 'exp-01' }],
    ['duplicate query', pack => { pack.queries[1].query_id = 'exp-02' }],
    ['three candidates', pack => { pack.queries[0].candidates.pop() }],
    ['five candidates', pack => { pack.queries[0].candidates.push(structuredClone(pack.queries[1].candidates[0])) }],
    ['empty description', pack => { pack.queries[0].text = '' }],
    ['extra query field', pack => { pack.queries[0].model_score = 0 }],
    ['reverse candidates', pack => { pack.queries[0].candidates.reverse() }]
  ])
})

test('source track, ISRC and content identities are globally unique even across different queries', async () => {
  await rejectResigned([
    ['same complete track in another query', pack => { pack.queries[1].candidates[0] = structuredClone(pack.queries[0].candidates[0]) }],
    ['same Java track with different metadata', pack => { pack.queries[1].candidates[0].track_id = pack.queries[0].candidates[0].track_id }],
    ['same ISRC with different Java track', pack => {
      const row = pack.queries[1].candidates[0], original = pack.queries[0].candidates[0]
      row.source_id = original.source_id; row.source_url = original.source_url
    }],
    ['same content with different IDs', pack => { pack.queries[1].candidates[0].content_sha256 = pack.queries[0].candidates[0].content_sha256 }],
    ['same candidate inside a query', pack => { pack.queries[0].candidates[1] = structuredClone(pack.queries[0].candidates[0]) }]
  ])
})

test('source provider, uppercase ISRC, exact same-source URL and CC BY 4.0 are mandatory', async () => {
  await rejectResigned([
    ['missing provider', pack => { delete pack.queries[0].candidates[0].source_provider }],
    ['wrong provider', pack => { pack.queries[0].candidates[0].source_provider = 'jamendo' }],
    ['numeric source', pack => { pack.queries[0].candidates[0].source_id = '101' }],
    ['lowercase source', pack => { pack.queries[0].candidates[0].source_id = 'usxyz0000001' }],
    ['malformed country', pack => { pack.queries[0].candidates[0].source_id = 'U1XYZ0000001' }],
    ['malformed registrant', pack => { pack.queries[0].candidates[0].source_id = 'USX_Z0000001' }],
    ['malformed numeric suffix', pack => { pack.queries[0].candidates[0].source_id = 'USXYZ000000X' }],
    ['wrong ISRC link', pack => { pack.queries[0].candidates[0].source_url = pack.queries[0].candidates[1].source_url }],
    ['extra source URL argument', pack => { pack.queries[0].candidates[0].source_url += '&extra=1' }],
    ['different source host', pack => { pack.queries[0].candidates[0].source_url = pack.queries[0].candidates[0].source_url.replace('https://', 'https://www.') }],
    ['old CC license', pack => { pack.queries[0].candidates[0].license_url = 'https://creativecommons.org/licenses/by/3.0/' }],
    ['license credentials', pack => { pack.queries[0].candidates[0].license_url = 'https://user@creativecommons.org/licenses/by/4.0/' }],
    ['extra model score', pack => { pack.queries[0].candidates[0].score = 1 }]
  ])
  const mixedRegistrant = await fixture(), row = mixedRegistrant.queries[0].candidates[0]
  row.source_id = 'GB1A90000001'; row.source_url = `https://incompetech.com/music/royalty-free/index.html?isrc=${row.source_id}`
  await load(await seal(mixedRegistrant))
})

test('source Java Long spelling, ordering, byte and duration bounds remain strict', async () => {
  const maximum = await fixture()
  maximum.queries.flatMap(query => query.candidates).forEach((row, index) => { row.track_id = String(9223372036854775788n + BigInt(index)) })
  await load(await seal(maximum))
  await rejectResigned([
    ['numeric track ID', pack => { pack.queries[0].candidates[0].track_id = 1 }],
    ['zero track ID', pack => { pack.queries[0].candidates[0].track_id = '0' }],
    ['leading-zero track ID', pack => { pack.queries[0].candidates[0].track_id = '01' }],
    ['overflow Java Long', pack => { pack.queries[0].candidates[3].track_id = '9223372036854775808' }],
    ['boolean bytes', pack => { pack.queries[0].candidates[0].content_bytes = true }],
    ['zero bytes', pack => { pack.queries[0].candidates[0].content_bytes = 0 }],
    ['oversized audio', pack => { pack.queries[0].candidates[0].content_bytes = 30 * 1024 * 1024 + 1 }],
    ['zero duration', pack => { pack.queries[0].candidates[0].duration_ms = 0 }],
    ['under-thirty-second duration', pack => { pack.queries[0].candidates[0].duration_ms = 29999 }],
    ['overlong duration', pack => { pack.queries[0].candidates[0].duration_ms = 600001 }],
    ['uppercase content hash', pack => { pack.queries[0].candidates[0].content_sha256 = 'A'.repeat(64) }]
  ])
  const bounds = await fixture()
  Object.assign(bounds.queries[0].candidates[0], { content_bytes: 30 * 1024 * 1024, duration_ms: 600000 })
  Object.assign(bounds.queries[0].candidates[1], { content_bytes: 1, duration_ms: 30000 })
  await load(await seal(bounds))
})

test('source packages always have an empty suggestions array, including after human scoring', async () => {
  await rejectResigned([
    ['suggested interval', pack => { pack.queries[0].candidates[0].model_suggested_intervals_ms = [[0, 10000]] }],
    ['null suggestions', pack => { pack.queries[0].candidates[0].model_suggested_intervals_ms = null }],
    ['missing suggestions', pack => { delete pack.queries[0].candidates[0].model_suggested_intervals_ms }]
  ])
})

test('source human judgments export and restore without changing the fingerprint or other null fields', async () => {
  const imported = await fixture(), before = JSON.stringify(imported), changed = structuredClone(imported)
  mark(changed.queries[0].candidates[0], 0)
  mark(changed.queries[0].candidates[1], 3)
  changed.queries[0].candidates[1].human_intervals_ms = [[0, 5000], [5000, 12000]]
  assert.equal(await reviewFingerprint(changed), imported.dataset_sha256)
  const exported = await exportReviewPack(changed, '42'), restored = await loadReviewDraft(exported, imported, '42')
  assert.deepEqual(reviewCounts(restored), { total: 20, judged: 2, unjudged: 18 })
  assert.equal(restored.queries[0].candidates[0].relevance, 0)
  assert.deepEqual(restored.queries[0].candidates[1].human_intervals_ms, [[0, 5000], [5000, 12000]])
  assert.deepEqual(restored.provenance, imported.provenance)
  assert.ok(restored.queries.every(query => query.candidates.every(row => row.model_suggested_intervals_ms.length === 0)))
  assert.equal(JSON.stringify(imported), before)
})

test('source human fields retain strict score, alias, timestamp and interval checks', async () => {
  for (const [key, value] of [['relevance', true], ['relevance', '2'], ['relevance', 4], ['annotator', 'Real Name'],
    ['judged_at', '2026-02-30T00:00:00Z'], ['human_intervals_ms', []], ['human_intervals_ms', [[0, 60001]]],
    ['human_intervals_ms', [[0, 6000], [5000, 12000]]]]) {
    const pack = await fixture(), row = pack.queries[0].candidates[0]
    mark(row, 2); row[key] = value
    await assert.rejects(load(await seal(pack)))
  }
  await rejectResigned([
    ['alias on unjudged candidate', pack => { pack.queries[0].candidates[0].annotator = 'synthetic-source' }],
    ['interval on zero relevance', pack => { const row = pack.queries[0].candidates[0]; mark(row, 0); row.human_intervals_ms = [[0, 1000]] }]
  ])
})

test('source drafts isolate owner, fixed inputs and candidate content, and reject fingerprint changes', async () => {
  const imported = await fixture(), key = reviewDraftKey('42', imported.dataset_sha256)
  await assert.rejects(load(imported, '43'))
  assert.notEqual(key, reviewDraftKey('43', imported.dataset_sha256))
  const changedInput = structuredClone(imported)
  changedInput.provenance.source_manifest_sha256 = 'a'.repeat(64)
  await assert.rejects(load(changedInput), /指纹不匹配/)
  await seal(changedInput)
  assert.notEqual(key, reviewDraftKey('42', changedInput.dataset_sha256))
  await assert.rejects(loadReviewDraft(JSON.stringify(changedInput), imported, '42'))
  const changedCandidate = structuredClone(imported)
  changedCandidate.queries[0].candidates[0].title = 'Changed synthetic title'
  await seal(changedCandidate)
  await load(changedCandidate) // Only the pinned-input CLI verifies source authenticity.
  await assert.rejects(loadReviewDraft(JSON.stringify(changedCandidate), imported, '42'))
  const old = await oldFixture()
  assert.notEqual(key, reviewDraftKey('42', old.dataset_sha256))
  await assert.rejects(loadReviewDraft(JSON.stringify(old), imported, '42'))
})

test('old E1 and diagnostic schemas retain numeric sources, exact provenance, limits and repeat semantics', async () => {
  await load(await oldFixture(REVIEW_SCHEMA, 10))
  await assert.rejects(load(await oldFixture(REVIEW_SCHEMA, 11)))
  const diagnostic = await oldFixture(DIAGNOSTIC_SCHEMA, 11)
  await load(diagnostic)
  for (const schema of [REVIEW_SCHEMA, DIAGNOSTIC_SCHEMA]) {
    const pack = await oldFixture(schema), row = pack.queries[0].candidates[0]
    row.source_id = 'USXYZ0000001'; row.source_url = `https://www.jamendo.com/track/${row.source_id}`
    await assert.rejects(load(await seal(pack)))
    const provider = await oldFixture(schema)
    provider.queries[0].candidates[0].source_provider = 'jamendo'
    await assert.rejects(load(await seal(provider)))
    const extraProvenance = await oldFixture(schema)
    extraProvenance.provenance.source_manifest_sha256 = 'a'.repeat(64)
    await assert.rejects(load(await seal(extraProvenance)))
  }
  const repeated = await oldFixture()
  repeated.queries.push({ ...structuredClone(repeated.queries[0]), query_id: 'another-old-query' })
  repeated.queries[0].candidates[0].model_suggested_intervals_ms = [[0, 10000]]
  await load(await seal(repeated))
})
