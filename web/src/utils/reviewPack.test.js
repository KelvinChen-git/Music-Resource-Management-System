import test from 'node:test'
import assert from 'node:assert/strict'
import { REVIEW_SCHEMA, REVIEW_SPLIT, loadReviewPack, reviewFingerprint, reviewCounts,
  reviewDraftKey, loadReviewDraft, exportReviewPack, strictReviewJson } from './reviewPack.js'

export async function fixture(owner = '42') {
  const pack = { schema: REVIEW_SCHEMA, split: REVIEW_SPLIT, owner_user_id: owner,
    provenance: { source_report_sha256: 'a'.repeat(64), run_code_sha: 'b'.repeat(40), input_catalog_sha256: 'c'.repeat(64), checkpoint_sha256: 'd'.repeat(64), pipeline_version: 'synthetic-only',
      artifact_sha256: Object.fromEntries(['corpus-manifest.json','queries.json','rankings.json','segments.json'].map(name => [name, 'e'.repeat(64)])), selection: 'union_whole_track_top5_and_segment_top5', ordering: 'query_fixture_order_then_track_id_ascending', labeling_aid: 'model_intervals_visible_not_blind' },
    queries: [{ query_id: 'synthetic-q', text: 'Synthetic test query — no listening judgments.', candidates: [1, 2].map(i => ({ track_id: String(i), source_id: String(100+i), title: `Synthetic ${i} 🎵`, artist: 'Test only', source_url: `https://www.jamendo.com/track/${100+i}`, license_url: 'https://creativecommons.org/licenses/by/4.0/', content_sha256: String(i).repeat(64), content_bytes: 1234, duration_ms: 12000, model_suggested_intervals_ms: [[0, 10000], [5000, 12000]], relevance: null, human_intervals_ms: null, annotator: null, judged_at: null })) }] }
  pack.dataset_sha256 = await reviewFingerprint(pack)
  return pack
}
async function load(pack, owner = '42') { return loadReviewPack(JSON.stringify(pack), owner) }
function mark(row, rating) { Object.assign(row, { relevance: rating, annotator: 'synthetic-test', judged_at: '2026-10-22T01:00:00Z' }) }

test('null labels stay null; unicode, canonical fingerprint and export round trip', async () => {
  const pack = await fixture(), before = JSON.stringify(pack)
  const read = await load(pack), result = reviewCounts(read)
  assert.deepEqual(result, {total:2,judged:0,unjudged:2})
  assert.deepEqual(await loadReviewPack(await exportReviewPack(read,'42'),'42'), pack)
  assert.equal(JSON.stringify(pack),before)
})
test('integer0 differs from null; labels and intervals do not change dataset fingerprint', async () => {
  const pack = await fixture(), row = pack.queries[0].candidates[0]
  mark(row,0)
  assert.deepEqual(reviewCounts(await load(pack)),{total:2,judged:1,unjudged:1})
  mark(row,3);row.human_intervals_ms=[[0,5000],[5000,12000]]
  assert.equal(await reviewFingerprint(pack),pack.dataset_sha256)
  assert.equal((await load(pack)).queries[0].candidates[0].human_intervals_ms.length,2)
})
test('owner, split, candidate integrity, ID spelling and unknown fields rejected', async () => {
  const p=await fixture()
  await assert.rejects(load(p,'43'))
  const changes=[v=>v.split='test',v=>v.owner_user_id='43',v=>v.dataset_sha256='f'.repeat(64),v=>v.queries[0].text='Changed',v=>v.extra=1,
    v=>v.queries[0].candidates.reverse(),v=>v.queries[0].candidates[0].track_id='01',v=>v.queries[0].candidates[0].track_id='9223372036854775808',v=>v.queries[0].candidates[0].content_bytes=true,
    v=>v.queries[0].candidates[0].source_url+='?canary=1',v=>v.queries[0].candidates[0].license_url='https://user@creativecommons.org/licenses/by/4.0/',v=>v.provenance.selection='untrusted']
  for(const change of changes){const next=structuredClone(p);change(next);await assert.rejects(load(next))}
})
test('duplicate JSON keys including escaped keys, float spelling and nonfinite rejected', async () => {
  assert.throws(()=>strictReviewJson('{"a":1,"\\u0061":2}'))
  for(const raw of ['{"a":1.0}','{"a":1e0}','{"a":NaN}','{"a":Infinity}',' '.repeat(2*1024*1024+1)]) assert.throws(()=>strictReviewJson(raw))
  assert.deepEqual(strictReviewJson('{"a":[{"b":1}, {"b":2}],"text":"{\\\"a\\\":1.0}"}'),{a:[{b:1},{b:2}],text:'{"a":1.0}'})
})
test('human labels require valid alias/time and valid integer score', async () => {
  for(const [key,value] of [['relevance',true],['relevance','2'],['relevance',4],['annotator',null],['annotator','Personal Name'],['judged_at','2026-02-30T00:00:00Z'],['judged_at','0000-01-01T00:00:00Z'],['judged_at',null]]){
    const p=await fixture(),r=p.queries[0].candidates[0];mark(r,2);r[key]=value;await assert.rejects(load(p))
  }
  const p=await fixture();p.queries[0].candidates[0].annotator='synthetic-test';await assert.rejects(load(p))
})
test('human ranges reject bounds, overlap, order, empty list and zero relevance', async () => {
  for(const ranges of [[],[[0,0]],[[-1,100]],[[0,12001]],[[false,10]],[[0,1.5]],[[0,6000],[5000,7000]],[[5000,6000],[0,1000]],Array(21).fill([0,10])]){
    const p=await fixture(),r=p.queries[0].candidates[0];mark(r,2);r.human_intervals_ms=ranges;await assert.rejects(load(p))
  }
  const p=await fixture(),r=p.queries[0].candidates[0];mark(r,0);r.human_intervals_ms=[[0,10]];await assert.rejects(load(p))
})
test('drafts isolate owner and dataset; recomputed changed candidate cannot replace import', async () => {
  const p=await fixture(),changed=structuredClone(p);mark(changed.queries[0].candidates[0],0)
  assert.equal(reviewCounts(await loadReviewDraft(JSON.stringify(changed),p,'42')).judged,1)
  assert.notEqual(reviewDraftKey('42',p.dataset_sha256),reviewDraftKey('43',p.dataset_sha256))
  const other=structuredClone(p);other.queries[0].text='Different data';other.dataset_sha256=await reviewFingerprint(other)
  assert.notEqual(reviewDraftKey('42',p.dataset_sha256),reviewDraftKey('42',other.dataset_sha256))
  await assert.rejects(loadReviewDraft(JSON.stringify(other),p,'42'))
  await assert.rejects(loadReviewDraft(JSON.stringify(changed),p,'43'))
})
test('repeated track metadata must be consistent; model suggestions never prefill human fields', async () => {
  const p=await fixture();p.queries.push({...structuredClone(p.queries[0]),query_id:'q2'})
  p.dataset_sha256=await reviewFingerprint(p);assert.equal(reviewCounts(await load(p)).judged,0)
  p.queries[1].candidates[0].content_bytes++
  p.dataset_sha256=await reviewFingerprint(p);await assert.rejects(load(p))
})
