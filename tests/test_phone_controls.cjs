const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../phone.html'),'utf8');
const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
function environment(){
 const elements=new Map();const el=s=>{if(!elements.has(s))elements.set(s,{disabled:false,value:'user',getContext:()=>({})});return elements.get(s)};
 const context={URLSearchParams,location:{hash:'#token=test',hostname:'127.0.0.1',search:''},document:{querySelector:el,createElement:el,addEventListener(){}},localStorage:{getItem:()=>null},window:{addEventListener(){}},AbortSignal,setTimeout:r=>queueMicrotask(r)};
 vm.createContext(context);vm.runInContext(source,context);return context;
}
function track(ignoreManual=false){
 const settings={exposureMode:'continuous',exposureTime:100,width:1280,height:720};
 return {getCapabilities:()=>({exposureMode:['continuous','manual'],exposureTime:{min:1,max:300,step:0}}),getSettings:()=>({...settings}),getConstraints:()=>({}),applyConstraints:async c=>{if(c.width)settings.width=c.width.ideal;if(c.height)settings.height=c.height.ideal;for(const a of c.advanced||[])if(!ignoreManual||a.exposureMode!=='manual')Object.assign(settings,a)}};
}
(async()=>{
 assert.match(html,/<option value="user" selected>Front camera/);
 let c=environment();c.track={getCapabilities:()=>({})};
 assert.match(await vm.runInContext("applyLighting(track,'50 Hz')",c),/unavailable/);
 for(const [mode,value] of [['50 Hz',100],['60 Hz',250/3]]){
  c=environment();c.track=track();
  assert.match(await vm.runInContext(`applyLighting(track,'${mode}')`,c),/confirmed/);
  assert.equal(c.track.getSettings().exposureTime,value);
  assert.match(await vm.runInContext("applyLighting(track,'Auto')",c),/Automatic exposure active/);
 }
 c=environment();c.track=track(true);
 assert.match(await vm.runInContext("applyLighting(track,'50 Hz')",c),/could not be applied/);
 assert.equal(c.track.getSettings().exposureMode,'continuous');
 c=environment();c.track=track();
 await vm.runInContext("applyLighting(track,'50 Hz')",c);
 c.track.getCapabilities=()=>({exposureMode:['continuous','manual'],exposureTime:{min:100,max:300,step:0}});
 assert.match(await vm.runInContext("applyLighting(track,'60 Hz')",c),/unavailable.*Automatic exposure active/);
 assert.equal(c.track.getSettings().exposureMode,'continuous');
 c.track.getSettings=()=>({exposureMode:'manual',exposureTime:100});
 c.track.applyConstraints=async()=>{};
 assert.match(await vm.runInContext("applyLighting(track,'60 Hz')",c),/could not be confirmed.*previous exposure/);
 c.track.getCapabilities=()=>({exposureMode:['continuous','manual'],exposureTime:{min:1,max:300,step:0}});
 assert.match(await vm.runInContext("applyLighting(track,'60 Hz')",c),/could not be applied.*could not be confirmed/);
 c.track.applyConstraints=async()=>{throw Error('Unsupported constraint')};
 assert.match(await vm.runInContext("applyLighting(track,'Auto')",c),/could not be confirmed/);
 c=environment();c.track=track();let report;
 c.fetch=async (url,options)=>{if(url==='/status')return {ok:true,json:async()=>({output_size:[1920,1080],lighting:'60 Hz'})};report=JSON.parse(options.body);vm.runInContext('running=false',c);return {ok:true}};
 vm.runInContext('stream={getVideoTracks:()=>[track]};running=true;generation=1',c);
 await vm.runInContext('syncPhoneSettings(1)',c);
 assert.equal(report.width,1920);assert.equal(report.height,1080);assert.match(report.lighting_status,/confirmed/);
 console.log('PASS: front default, unsupported exposure, 50/60 Hz readback, Auto restore, ignored constraints fallback, live resolution control.');
})().catch(error=>{console.error(error);process.exitCode=1});
