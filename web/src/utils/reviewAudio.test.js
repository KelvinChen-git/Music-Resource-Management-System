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
test('verified Incompetech whole-track playback uses the shorter browser endpoint without changing input',async t=>{
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.25322
  const original=structuredClone(s.row),range=[0,153555]
  await s.control.start(s.row,range)
  assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.states.at(-1).verified,true)
  assert.equal(s.states.at(-1).rangeEndMs,153253);assert.deepEqual(range,[0,153555]);assert.deepEqual(s.row,original)
  s.audio.currentTime=153.253;s.audio.dispatchEvent(new Event('timeupdate'))
  assert.equal(s.states.at(-1).phase,'idle');assert.equal(s.states.at(-1).positionMs,153253)
  assert.equal(s.audio.paused,true);assert.equal(s.audio.src,'');assert.deepEqual(s.revoked,['blob:1'])
})
test('a longer Incompetech browser duration never extends the recorded whole-track range',async t=>{
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=154
  await s.control.start(s.row)
  assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.states.at(-1).rangeEndMs,153555)
  await s.control.seek(154000)
  assert.equal(s.states.at(-1).phase,'idle');assert.equal(s.states.at(-1).positionMs,153555)
  assert.equal(s.row.duration_ms,153555)
})
test('source fragments and legacy whole tracks retain the original duration mismatch rejection',async t=>{
  for(const [provider,range] of [[undefined,[0,153555]],['jamendo',[0,153555]],['incompetech',[1000,153555]],['incompetech',[0,153554]]]){
    const s=await setup(t);s.row.duration_ms=153555;if(provider)s.row.source_provider=provider;s.audio.duration=153.25322
    await s.control.start(s.row,range)
    assert.equal(s.states.at(-1).phase,'error');assert.match(s.states.at(-1).error,/时长/)
    assert.equal(s.audio.plays,0);assert.equal(s.revoked.length,1);assert.equal(s.states.at(-1).verified,false)
  }
})
test('source pause, paused seek, resume and endpoint seek share the verified effective range',async t=>{
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.25322
  await s.control.start(s.row);s.audio.currentTime=100;s.control.pause()
  assert.equal(s.states.at(-1).phase,'paused');assert.equal(s.states.at(-1).positionMs,100000);assert.equal(s.states.at(-1).rangeEndMs,153253)
  await s.control.seek(120000)
  assert.equal(s.calls.length,2);assert.equal(s.states.at(-1).phase,'paused');assert.equal(s.states.at(-1).positionMs,120000)
  assert.equal(s.states.at(-1).rangeEndMs,153253);assert.equal(s.audio.src,'')
  await s.control.toggle()
  assert.equal(s.calls.length,3);assert.equal(s.audio.currentTime,120);assert.equal(s.states.at(-1).phase,'playing')
  assert.equal(s.states.at(-1).rangeEndMs,153253);assert.equal(s.row.duration_ms,153555)
  await s.control.seek(153554)
  assert.equal(s.states.at(-1).phase,'idle');assert.equal(s.states.at(-1).positionMs,153253);assert.equal(s.audio.src,'')
})
test('invalid or sub-millisecond browser duration and positions beyond the effective endpoint cannot play',async t=>{
  for(const duration of [NaN,Infinity,-Infinity,0,-1,0.0005]){
    const s=await setup(t);s.row.source_provider='incompetech';s.audio.duration=duration
    await s.control.start(s.row)
    assert.equal(s.states.at(-1).phase,'error');assert.equal(s.audio.plays,0);assert.equal(s.revoked.length,1)
  }
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.25322
  await s.control.start(s.row,[0,153555],153400)
  assert.equal(s.states.at(-1).phase,'error');assert.equal(s.audio.plays,0);assert.equal(s.states.at(-1).verified,false)
})
test('source endpoint adaptation never bypasses byte/SHA validation or fresh resume duration validation',async t=>{
  const invalid=await setup(t,async()=>new Response(new Uint8Array([4,3,2,1])))
  invalid.row.source_provider='incompetech';invalid.audio.duration=11.7
  await invalid.control.start(invalid.row)
  assert.equal(invalid.created.length,0);assert.equal(invalid.audio.plays,0);assert.equal(invalid.states.at(-1).phase,'error')
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.25322
  await s.control.start(s.row);s.audio.currentTime=100;s.control.pause();s.audio.duration=153
  await s.control.toggle()
  assert.equal(s.calls.length,2);assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.states.at(-1).verified,true)
  assert.equal(s.states.at(-1).rangeEndMs,153000);assert.equal(s.audio.currentTime,100)
  assert.equal(s.audio.plays,2);assert.equal(s.created.length,2);assert.equal(s.revoked.length,1)
})
test('fresh source resume and paused seek reapply the whole-track identity even for sub-100ms shortening',async t=>{
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.25322
  await s.control.start(s.row);s.audio.currentTime=100;s.control.pause();s.audio.duration=153.2
  await s.control.toggle()
  assert.equal(s.calls.length,2);assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.states.at(-1).rangeEndMs,153200)
  s.control.pause();s.audio.duration=153.1;await s.control.seek(120000)
  assert.equal(s.calls.length,3);assert.equal(s.states.at(-1).phase,'paused');assert.equal(s.states.at(-1).rangeEndMs,153100)
  assert.equal(s.states.at(-1).positionMs,120000);assert.equal(s.audio.src,'')
  await s.control.toggle()
  assert.equal(s.calls.length,4);assert.equal(s.states.at(-1).phase,'playing');assert.equal(s.states.at(-1).rangeEndMs,153100)
  assert.equal(s.row.duration_ms,153555)
  await s.control.seek(153200)
  assert.equal(s.states.at(-1).phase,'idle');assert.equal(s.states.at(-1).positionMs,153100)
})
test('source resume or paused seek at or beyond a newly shortened endpoint rejects before playing',async t=>{
  for(const [action,position] of [['resume',153240],['resume',153200],['seek',153220],['seek',153200]]){
    const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.25322
    await s.control.start(s.row);s.audio.currentTime=action==='resume'?position/1000:100;s.control.pause();s.audio.duration=153.2
    if(action==='resume')await s.control.toggle();else await s.control.seek(position)
    assert.equal(s.calls.length,2);assert.equal(s.states.at(-1).phase,'error');assert.equal(s.states.at(-1).verified,false)
    assert.equal(s.audio.plays,1);assert.equal(s.created.length,2);assert.equal(s.revoked.length,2);assert.equal(s.audio.src,'')
  }
})
test('fresh source fragment resume keeps its original clip identity and duration rejection',async t=>{
  const s=await setup(t);Object.assign(s.row,{source_provider:'incompetech',duration_ms:153555});s.audio.duration=153.6
  await s.control.start(s.row,[0,153554]);s.audio.currentTime=100;s.control.pause();s.audio.duration=153.25322
  await s.control.toggle()
  assert.equal(s.calls.length,2);assert.equal(s.states.at(-1).phase,'error');assert.equal(s.audio.plays,1)
  assert.equal(s.created.length,2);assert.equal(s.revoked.length,2)
})

test('both pinned LOC providers clamp verified full tracks to browser EOF and preserve source duration', async t => {
  for (const provider of ['loc-citizen-dj-fma', 'loc-citizen-dj-musicbox']) {
    const s = await setup(t); s.audio.duration = 11.7; s.row.source_provider = provider
    await s.control.start(s.row)
    assert.equal(s.states.at(-1).phase, 'playing'); assert.equal(s.states.at(-1).rangeEndMs, 11700)
    assert.equal(s.row.duration_ms, 12000)
    s.control.pause(); s.audio.duration = 11.6; await s.control.toggle()
    assert.equal(s.states.at(-1).rangeEndMs, 11600); assert.equal(s.calls.length, 2)
    await s.control.start(s.row, [5000, 12000]); assert.equal(s.states.at(-1).phase, 'error')
  }
})
