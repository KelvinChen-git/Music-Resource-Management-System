import test from 'node:test'
import assert from 'node:assert/strict'
import { createReviewAudio } from './reviewAudio.js'
import { sha256 } from './reviewPack.js'
const bytes = new Uint8Array([1,2,3,4])
const later=()=>{let resolve;const promise=new Promise(r=>{resolve=r});return{promise,resolve}}
class Audio extends EventTarget {
  src='';duration=12;paused=true;position=0;plays=0
  load(){if(this.src)queueMicrotask(()=>this.dispatchEvent(new Event('loadedmetadata')))}
  removeAttribute(){this.src=''}
  pause(){this.paused=true}
  get currentTime(){return this.position}
  set currentTime(value){this.position=value;queueMicrotask(()=>this.dispatchEvent(new Event('seeked')))}
  async play(){this.paused=false;this.plays++}
}
async function setup(t,fetcher=async()=>new Response(bytes)){
  const audio=new Audio(),states=[],created=[],revoked=[],calls=[],signals=[]
  const row={track_id:'27',duration_ms:12000,content_bytes:4,content_sha256:await sha256(bytes)}
  let globalPauses=0
  const control=createReviewAudio({audio,fetchMedia:(url,options)=>{calls.push(url);signals.push(options.signal);return fetcher(url,options)},beforePlay:()=>globalPauses++,onState:s=>states.push(s),urls:{createObjectURL:blob=>{created.push(blob);return 'blob:'+created.length},revokeObjectURL:url=>revoked.push(url)}})
  t.after(()=>control.stop())
  return{audio,states,created,revoked,calls,signals,row,control,get globalPauses(){return globalPauses}}
}
test('fresh authorized request each play, verified blob, seek, end stop and URL release',async t=>{
  const s=await setup(t);await s.control.start(s.row,[5000,10000])
  assert.equal(s.audio.currentTime,5);assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.created.length,1);assert.equal(s.states.at(-1).verified,true)
  assert.deepEqual(s.calls,['/api/music-resources/27/file']);assert.equal(s.globalPauses,1)
  s.audio.currentTime=10;s.audio.dispatchEvent(new Event('timeupdate'))
  assert.equal(s.audio.paused,true);assert.equal(s.states.at(-1).positionMs,10000);assert.deepEqual(s.revoked,['blob:1'])
  await s.control.start(s.row,[0,10000]);assert.equal(s.calls.length,2);assert.equal(s.created.length,2)
  s.control.stop();assert.equal(s.audio.src,'');assert.equal(s.signals[1].aborted,true);assert.equal(s.revoked.length,2)
})
test('hash mismatch, incomplete/oversize bodies and declared length mismatch never create URL',async t=>{
  for(const [body,headers] of [[new Uint8Array([4,3,2,1]),{}],[bytes.slice(0,3),{}],[new Uint8Array([1,2,3,4,5]),{}],[bytes,{'content-length':'5'}]]){
    const s=await setup(t,async()=>new Response(body,{headers}));await s.control.start(s.row)
    assert.equal(s.created.length,0);assert.equal(s.audio.plays,0);assert.equal(s.states.at(-1).phase,'error');assert.equal(s.states.at(-1).verified,false);assert.equal(s.states.at(-1).trackId,'')
  }
})
test('permission/network rejection never plays, and is retryable via fresh fetch',async t=>{
  for(const message of ['Please log in again','Media access denied','Media is unavailable','network']){
    const s=await setup(t,async()=>{throw new Error(message)});await s.control.start(s.row)
    assert.equal(s.states.at(-1).error,message);assert.equal(s.created.length,0)
  }
})
test('stopped or replaced pending request cannot attach audio',async t=>{
  const first=later();let n=0;const s=await setup(t,()=>++n===1?first.promise:Promise.resolve(new Response(bytes)))
  const old=s.control.start(s.row);await s.control.start(s.row,[5000,10000]);first.resolve(new Response(bytes));await old
  assert.equal(s.created.length,1);assert.equal(s.audio.paused,false);assert.equal(s.signals[0].aborted,true)
  const pending=later();const q=await setup(t,()=>pending.promise);const p=q.control.start(q.row);q.control.stop();pending.resolve(new Response(bytes));await p
  assert.equal(q.created.length,0);assert.equal(q.audio.plays,0)
})
test('late old play promise does not pause new playback',async t=>{
  const s=await setup(t),started=later(),oldPlay=later();let n=0
  s.audio.play=async()=>{s.audio.paused=false;if(++n===1){started.resolve();await oldPlay.promise}}
  const old=s.control.start(s.row);await started.promise;await s.control.start(s.row);oldPlay.resolve();await old
  assert.equal(s.audio.paused,false);assert.equal(s.states.at(-1).phase,'playing')
})
test('duration mismatch and autoplay errors release created URL',async t=>{
  const s=await setup(t);s.audio.duration=3;await s.control.start(s.row,[5000,10000]);assert.equal(s.states.at(-1).phase,'error');assert.equal(s.revoked.length,1)
  const q=await setup(t);q.audio.play=async()=>{throw new Error('autoplay blocked')};await q.control.start(q.row);assert.equal(q.states.at(-1).phase,'error');assert.equal(q.revoked.length,1)
})
test('wall time during stalled playback does not pretend a clip was played',async t=>{
  const s=await setup(t);await s.control.start(s.row,[0,30]);await new Promise(r=>setTimeout(r,45))
  assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.audio.paused,false)
  s.audio.currentTime=0.03;s.audio.dispatchEvent(new Event('timeupdate'));assert.equal(s.states.at(-1).phase,'idle')
})
test('live seek changes the actual audio, clamps to clip bounds and ends at the selected endpoint',async t=>{
  const s=await setup(t);await s.control.start(s.row,[5000,10000])
  await s.control.seek(8000);assert.equal(s.audio.currentTime,8);assert.equal(s.states.at(-1).positionMs,8000)
  await s.control.seek(6000);assert.equal(s.audio.currentTime,6)
  await s.control.seek(-100);assert.equal(s.audio.currentTime,5)
  assert.equal(s.calls.length,1)
  await s.control.seek(99000);assert.equal(s.states.at(-1).positionMs,10000);assert.equal(s.audio.src,'');assert.equal(s.audio.paused,true)
})
test('pause saves position and releases bytes; paused seek stays paused and resume fetches afresh',async t=>{
  const s=await setup(t);await s.control.start(s.row,[5000,10000]);s.audio.currentTime=6.5;s.control.pause()
  assert.equal(s.states.at(-1).phase,'paused');assert.equal(s.states.at(-1).positionMs,6500);assert.equal(s.audio.src,'')
  await s.control.seek(7000);assert.equal(s.calls.length,2);assert.equal(s.audio.paused,true);assert.equal(s.audio.src,'');assert.equal(s.states.at(-1).positionMs,7000)
  await s.control.toggle();assert.equal(s.calls.length,3);assert.equal(s.audio.currentTime,7);assert.equal(s.audio.paused,false)
  s.control.stop();await s.control.toggle();assert.equal(s.calls.length,3)
})
test('a resume permission failure clears verified state and never reuses the old blob',async t=>{
  let n=0;const s=await setup(t,async()=>{if(++n===2)throw new Error('Media access denied');return new Response(bytes)})
  await s.control.start(s.row);s.control.pause();await s.control.toggle()
  assert.equal(s.created.length,1);assert.equal(s.states.at(-1).verified,false);assert.equal(s.states.at(-1).phase,'error');assert.equal(s.audio.src,'')
  await s.control.toggle();assert.equal(s.calls.length,3);assert.equal(s.created.length,2)
})
test('seeking a pending load cancels its generation and late bytes cannot move the new playhead',async t=>{
  const first=later();let n=0;const s=await setup(t,()=>++n===1?first.promise:Promise.resolve(new Response(bytes)))
  const pending=s.control.start(s.row);await s.control.seek(7000);first.resolve(new Response(bytes));await pending
  assert.equal(s.audio.currentTime,7);assert.equal(s.created.length,1);assert.equal(s.signals[0].aborted,true)
})
