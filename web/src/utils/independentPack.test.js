import test from 'node:test'
import assert from 'node:assert/strict'
import { INDEPENDENT_SCHEMA, INDEPENDENT_SPLIT, PRESENTATION_SEED, loadReviewPack, reviewFingerprint,
  reviewCounts, reviewDraftKey, loadReviewDraft, exportReviewPack, exportCompletionReceipt, sha256 } from './reviewPack.js'

const hashes = ['runner_freeze_sha256', 'source_dataset_sha256', 'import_catalog_sha256',
  'query_manifest_sha256', 'runtime_config_sha256', 'test_dataset_sha256']
async function sign(pack) { pack.dataset_sha256 = await reviewFingerprint(pack); return pack }
async function fixture(batch = 1) {
  const rows = Array.from({ length: 20 }, (_, i) => {
    const source_id = i < 16 ? `fma-${i + 1}` : `DR000${i}`, collection = i < 16 ? 'loc-fma' : 'loc-musicbox'
    return { track_id: String(1999000000000000100n + BigInt(i)), source_provider: i < 16 ? 'loc-citizen-dj-fma' : 'loc-citizen-dj-musicbox',
      source_id, title: `Synthetic track ${i} 🎵`, artist: 'Synthetic artist',
      source_url: `https://citizen-dj.labs.loc.gov/items/${collection}/${source_id}/`,
      license_url: `https://citizen-dj.labs.loc.gov/${collection}/use/`, content_sha256: (i + 1).toString(16).padStart(64, '0'),
      content_bytes: 1234, duration_ms: 60000, model_suggested_intervals_ms: [],
      relevance: null, human_intervals_ms: null, annotator: null, judged_at: null }
  })
  const queries = []
  for (const slot of [batch * 2 - 1, batch * 2]) {
    const query_id = `holdout-${String(slot).padStart(2, '0')}`, ordered = []
    for (const row of rows) ordered.push({ row, hash: await sha256(new TextEncoder().encode(`${PRESENTATION_SEED}\n${query_id}\n${row.source_provider}:${row.source_id}`)) })
    ordered.sort((a, b) => a.hash < b.hash ? -1 : a.hash > b.hash ? 1 : 0)
    queries.push({ query_id, text: `Synthetic request ${slot}`, gloss_zh: '只作合成检查的中文说明',
      audible_required_cues_zh: ['线索一', '线索二', '线索三'], grade_rules_zh: { 0: '未听到', 1: '少量', 2: '可辨', 3: '突出' },
      possible_no_match_probe: slot >= 7, candidates: ordered.map(({ row }) => structuredClone(row)) })
  }
  return sign({ schema: INDEPENDENT_SCHEMA, split: INDEPENDENT_SPLIT, owner_user_id: '42',
    provenance: { ...Object.fromEntries(hashes.map((key, i) => [key, String(i + 1).repeat(64)])), batch, batches: 4,
      selection: 'full20_per_query_model_blind', ordering: 'preregistered_hash_recording_order', labeling_aid: 'no_model_hints' }, queries })
}
const load = (pack, owner = '42') => loadReviewPack(JSON.stringify(pack), owner)
function mark(row, relevance = 0) { Object.assign(row, { relevance, annotator: 'synthetic-only', judged_at: '2026-10-29T01:00:00Z' }) }

test('four isolated full-grid batches retain unknowns, fixed order, probes and bilingual cues', async () => {
  const keys = new Set()
  for (let batch = 1; batch <= 4; batch++) {
    const pack = await load(await fixture(batch))
    assert.deepEqual(reviewCounts(pack), { total: 40, judged: 0, unjudged: 40 })
    keys.add(reviewDraftKey('42', pack.dataset_sha256))
    assert.equal(new Set(pack.queries.flatMap(q => q.candidates.map(r => r.track_id))).size, 20)
    assert.equal(pack.queries[0].possible_no_match_probe, batch === 4)
  }
  assert.equal(keys.size, 4)
})
test('immutable tampering, wrong owner, missing or extra fields and stale fingerprint are rejected', async () => {
  const pack = await fixture()
  await assert.rejects(load(pack, '43'))
  const bad = structuredClone(pack); bad.queries[0].gloss_zh = '修改'; await assert.rejects(load(bad))
  for (const change of [p => { p.qrels = [] }, p => { delete p.queries[0].grade_rules_zh['3'] },
    p => { p.provenance.batch = 2 }, p => { p.split = 'exploratory_only_not_held_out' },
    p => { p.queries[0].candidates.pop() }, p => { p.queries[1].candidates[0].title = '不同标题' },
    p => { p.queries[0].candidates[0].license_url = 'https://creativecommons.org/publicdomain/zero/1.0/' }]) {
    const bad = structuredClone(pack); change(bad); await assert.rejects(load(await sign(bad)))
  }
})
test('resigning a changed presentation order or adding model hints cannot bypass validation', async () => {
  const pack = await fixture()
  const swapped = structuredClone(pack); swapped.queries[0].candidates.reverse(); await assert.rejects(load(await sign(swapped)))
  const hinted = structuredClone(pack); hinted.queries[0].candidates[0].model_suggested_intervals_ms = [[0, 1000]]
  await assert.rejects(load(await sign(hinted)))
})
test('duplicate identities, contents, wrong official URLs, invalid counts and partial human data fail closed', async () => {
  for (const change of [r => { r.track_id = '0' }, r => { r.source_provider = 'unknown' },
    r => { r.duration_ms = 29999 }, r => { r.content_bytes = 0 }, r => { r.annotator = 'partial' },
    r => { r.source_url += '?other=1' }, r => { r.source_id = '../escape' },
    r => { r.relevance = true }, r => { r.source_id = 'fma-1'; r.source_provider = 'loc-citizen-dj-fma' }]) {
    const pack = await fixture(); change(pack.queries[0].candidates[0]); await assert.rejects(load(await sign(pack)))
  }
})
test('judgments and intervals round trip, draft identity unchanged, zero clears only with valid human fields', async () => {
  const pack = await fixture(), original = pack.dataset_sha256, row = pack.queries[0].candidates[0]
  mark(row, 2); row.human_intervals_ms = [[0, 1000], [2000, 4000]]
  const raw = await exportReviewPack(pack, '42'), saved = await loadReviewDraft(raw, await fixture(), '42')
  assert.equal(saved.dataset_sha256, original); assert.equal(reviewCounts(saved).judged, 1)
  row.relevance = 0; await assert.rejects(load(pack)); row.human_intervals_ms = null; await load(pack)
  row.judged_at = '2026-02-30T01:00:00Z'; await assert.rejects(load(pack))
})
test('completion receipt requires all40, hashes exact export bytes and leaks no grade or personal fields', async () => {
  const pack = await fixture(); await assert.rejects(exportCompletionReceipt(pack, '42'))
  for (const q of pack.queries) for (const r of q.candidates) mark(r, 1)
  const raw = await exportReviewPack(pack, '42'), receipt = JSON.parse(await exportCompletionReceipt(pack, '42'))
  assert.deepEqual(Object.keys(receipt).sort(), ['dataset_sha256', 'payload_sha256', 'total_completed_count', 'validation_status'])
  assert.equal(receipt.payload_sha256, await sha256(new TextEncoder().encode(raw)))
  assert.equal(receipt.total_completed_count, 40); assert.equal(receipt.validation_status, 'valid_complete_batch')
  const partial = structuredClone(pack); Object.assign(partial.queries[0].candidates[0], { relevance: null, annotator: null, judged_at: null })
  await assert.rejects(exportCompletionReceipt(partial, '42'))
})
