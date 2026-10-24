// Real Pinia/Vue store; only its existing user/API boundary is substituted.
import test from 'node:test'
import assert from 'node:assert/strict'
import { registerHooks } from 'node:module'
import { createPinia, setActivePinia } from 'pinia'
import { defineStore } from 'pinia'
globalThis.__sonoraUser = defineStore('test-user', { state: () => ({userId:'42',token:'jwt'}) })
let getUrl
globalThis.__sonoraUrl = (...args) => getUrl(...args)
const hook=registerHooks({resolve(specifier,context,next){
  if(specifier==='@/api/music')return{url:'data:text/javascript,export const createMusicUrl=(...args)=>globalThis.__sonoraUrl(...args)',shortCircuit:true}
  if(specifier==='@/stores/user')return{url:'data:text/javascript,export const useUserStore=()=>globalThis.__sonoraUser()',shortCircuit:true}
  return next(specifier,context)
}})
const {useSonoraPlayer}=await import('./sonoraPlayer.js')
hook.deregister()
globalThis.localStorage={getItem:()=>null,setItem:()=>{}}
const deferred=()=>{let resolve;return{promise:new Promise(r=>{resolve=r}),resolve:v=>resolve(v)}}
function setup(t){
  setActivePinia(createPinia());getUrl=async()=> 'blob:library'
  const audio={paused:true,src:'',currentTime:0,duration:20,volume:.7,pause(){this.paused=true},removeAttribute(){this.src=''},getAttribute(){return this.src},load(){},async play(){this.paused=false}}
  const p=useSonoraPlayer();p.attach(audio);const user=globalThis.__sonoraUser()
  const calls={stop:0,toggle:0,seek:[],volume:[]},controls={stop:()=>calls.stop++,toggle:()=>calls.toggle++,seek:v=>calls.seek.push(v),setVolume:v=>calls.volume.push(v)}
  t.after(()=>p.reset());return{p,user,audio,calls,controls}
}
test('review metadata/control session preserves library queue and routes seek/volume',t=>{
  const s=setup(t),song={musicid:'27',title:'Review',artist:'Artist'}
  s.p.queue=[{musicid:'9',title:'Library'}];s.p.current=s.p.queue[0];s.audio.paused=false
  const bind=s.p.registerReview(song,[5000,10000],s.controls);bind.update({phase:'playing',verified:true,positionMs:6000})
  assert.equal(s.p.reviewSession.song.title,'Review');assert.equal(s.p.current.musicid,'9');assert.equal(s.p.queue.length,1);assert.equal(s.audio.paused,true)
  s.p.seekReview(40);s.p.toggleReview();s.p.setVolume(25)
  assert.deepEqual(s.calls.seek,[7000]);assert.equal(s.calls.toggle,1);assert.deepEqual(s.calls.volume,[70,25]);assert.equal(s.audio.volume,.25)
  bind.release();assert.equal(s.p.reviewSession,null);assert.equal(s.calls.stop,1);assert.equal(s.p.queue[0].musicid,'9')
})
test('pending library response and late media/ended events cannot take over a review',async t=>{
  const s=setup(t),wait=deferred(),revoked=[],oldRevoke=URL.revokeObjectURL;URL.revokeObjectURL=v=>revoked.push(v);t.after(()=>{URL.revokeObjectURL=oldRevoke})
  getUrl=()=>wait.promise;const old=s.p.play({musicid:'9',title:'Library'})
  s.p.registerReview({musicid:'27'},[0,10000],s.controls);wait.resolve('blob:late');await old
  assert.deepEqual(revoked,['blob:late']);assert.equal(s.audio.src,'');assert.equal(s.p.reviewSession.song.musicid,'27')
  s.audio.paused=false;s.p.sync();assert.equal(s.audio.paused,true);await s.p.advance();assert.equal(s.p.reviewSession.song.musicid,'27')
})
test('old review publishers cannot update or release the newer review session',t=>{
  const s=setup(t),a=s.p.registerReview({musicid:'1'},[0,1000],s.controls),b=s.p.registerReview({musicid:'2'},[0,2000],s.controls)
  a.update({phase:'playing',positionMs:999});a.release();assert.equal(s.p.reviewSession.song.musicid,'2');assert.equal(s.p.reviewSession.positionMs,0)
  b.update({phase:'playing',verified:true});assert.equal(s.p.reviewSession.phase,'playing')
})
test('explicit library play stops review once and restores ordinary transport',async t=>{
  const s=setup(t);s.p.registerReview({musicid:'27'},[0,10000],s.controls)
  await s.p.play({musicid:'9',title:'Library'});assert.equal(s.calls.stop,1);assert.equal(s.p.reviewSession,null);assert.equal(s.audio.src,'blob:library');assert.equal(s.audio.paused,false)
})
test('token change releases review without discarding queue; account change resets both',t=>{
  const s=setup(t);s.p.queue=[{musicid:'9'}];s.p.registerReview({musicid:'27'},[0,10000],s.controls)
  s.user.token='replacement';assert.equal(s.p.reviewSession,null);assert.equal(s.calls.stop,1);assert.equal(s.p.queue.length,1)
  s.p.registerReview({musicid:'28'},[0,10000],s.controls);s.user.userId='43'
  assert.equal(s.p.reviewSession,null);assert.equal(s.calls.stop,2);assert.equal(s.p.queue.length,0)
})
test('cancelled library song switch cannot resume the old bytes under the newer title',async t=>{
  const s=setup(t);await s.p.play({musicid:'old',title:'Old'})
  const wait=deferred();getUrl=()=>wait.promise
  const pending=s.p.play({musicid:'new',title:'New'})
  const binding=s.p.registerReview({musicid:'27'},[0,10000],s.controls)
  assert.equal(s.audio.src,'');binding.release();wait.resolve('blob:cancelled');await pending
  assert.equal(s.p.current.title,'New');assert.equal(s.audio.src,'')
  getUrl=async()=> 'blob:new';await s.p.toggle();assert.equal(s.audio.src,'blob:new')
})
