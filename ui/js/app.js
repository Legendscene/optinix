function showPage(p){document.querySelectorAll('.page').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.nav-btn').forEach(x=>x.classList.remove('active'));const e=document.getElementById('page-'+p);const n=document.querySelector('[data-page="'+p+'"]');if(e)e.classList.add('active');if(n)n.classList.add('active');if(p==='dashboard')loadSystemInfo();if(p==='services')loadServices();if(p==='startup')loadStartup();if(p==='disks')loadDisks()}

async function loadSystemInfo(){try{const r=await fetch('/api/system-info');const d=await r.json();
// CPU
const cpuPct=Math.round(d.cpu.percent||0);setEl('cpuValue',cpuPct+'%');setBar('cpuBar',cpuPct);setEl('cpuInfo',(d.cpu.physical||'?')+' cores / '+(d.cpu.logical||'?')+' threads');
// RAM
const ramPct=Math.round(d.memory.percent||0);setEl('ramValue',ramPct+'%');setBar('ramBar',ramPct);setEl('ramInfo',(d.memory.used_gb||0)+'GB / '+(d.memory.total_gb||0)+'GB');
// Disk
if(d.disk&&d.disk.length){const dk=d.disk[0];setEl('diskValue',Math.round(dk.percent)+'%');setBar('diskBar',dk.percent);setEl('diskInfo',fmtBytes(dk.free)+' free / '+fmtBytes(dk.total))}
// Net
const up=fmtSpeed(d.network.speed_up),dn=fmtSpeed(d.network.speed_down);setEl('netValue','<span class="speed-up">\u2191'+up+'</span> <span class="speed-down">\u2193'+dn+'</span>',true);setEl('netInfo','Sent: '+fmtBytes(d.network.bytes_sent)+' | Recv: '+fmtBytes(d.network.bytes_recv));const netBar=document.getElementById('netBar');if(netBar)netBar.style.width=Math.min(100,Math.max(d.network.speed_up,d.network.speed_down,1)/1048576*100)+'%';
// GPU
if(d.gpu){setEl('gpuValue',d.gpu.usage+'%');setBar('gpuBar',d.gpu.usage);let gt=d.gpu.name||'N/A';if(d.gpu.temperature)gt+=' | '+d.gpu.temperature+'\u00b0C';if(d.gpu.memory_total)gt+=' | '+fmtBytes(d.gpu.memory_used*1048576)+'/'+fmtBytes(d.gpu.memory_total);setEl('gpuName',gt)}
// System
if(d.system){setEl('uptimeValue',d.system.uptime);setEl('sysInfo',d.system.os+' | '+d.system.processor)}
// Temp
if(d.cpu&&d.cpu.temperature)setEl('tempValue',d.cpu.temperature+'\u00b0C');
// OS badge
if(d.os){const b=document.getElementById('osBadge');if(b)b.textContent=d.os.os_name}
}catch(e){console.error(e)}}

function setEl(id,v,html){const e=document.getElementById(id);if(e){if(html)e.innerHTML=v;else e.textContent=v}}
function setBar(id,pct){const e=document.getElementById(id);if(e)e.style.width=pct+'%'}
function fmtBytes(b){if(!b)return'--';const k=1024,s=['B','KB','MB','GB','TB'];const i=Math.floor(Math.log(b)/Math.log(k));return parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]}
function fmtSpeed(bps){if(!bps||bps<1)return'0 B/s';const k=1024,s=['B/s','KB/s','MB/s','GB/s'];const i=Math.floor(Math.log(bps)/Math.log(k));return parseFloat((bps/Math.pow(k,i)).toFixed(1))+s[i]}

async function runOptimizer(c){showLoader(c+'...');try{const r=await fetch('/api/optimize/'+c,{method:'POST'});const d=await r.json();hideLoader();showResults(c,d.results||d)}catch(e){hideLoader();showResults(c,[{success:false,message:e.message}]})}

async function runAllOptimizations(){showLoader('Running all...');try{const r=await fetch('/api/optimize/all',{method:'POST'});const d=await r.json();hideLoader();let a=[];Object.entries(d).forEach(([c,r])=>{if(Array.isArray(r))r.forEach(x=>a.push({...x,category:c}))});const el=document.getElementById('dashResultsList');const s=document.getElementById('dashResults');if(el&&s){s.style.display='block';el.innerHTML=a.map(r=>'<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' <strong>['+r.category.toUpperCase()+']</strong> '+r.message+'</div>').join('')}}catch(e){hideLoader()}}

async function runExtremeTuning(){showLoader('Extreme mode...');try{const r=await fetch('/api/tuning/extreme',{method:'POST'});const d=await r.json();hideLoader();showResults('extreme',d.results||[])}catch(e){hideLoader();showResults('extreme',[{success:false,message:e.message}])}}

// SERVICES
async function loadServices(){const l=document.getElementById('servicesList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';try{const r=await fetch('/api/services');const d=await r.json();l.innerHTML=(d.services||[]).map(s=>'<div class="svc-row"><div class="svc-info"><span class="svc-name">'+s.name+'</span><span class="svc-desc">'+s.desc+'</span>'+(s.safe?'<span class="svc-badge safe">Safe</span>':'<span class="svc-badge warn">Critical</span>')+'</div><label class="toggle"><input type="checkbox" '+(s.running?'checked':'')+' '+(s.safe?'':'disabled')+' onchange="toggleService(\''+s.name+'\',this.checked)"><span class="slider"></span></label></div>').join('')}catch(e){l.innerHTML='<p class="err">Failed to load</p>'}}
async function toggleService(n,e){try{await fetch('/api/services/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,enable:e})})}catch(x){}}

// STARTUP
async function loadStartup(){const l=document.getElementById('startupList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';try{const r=await fetch('/api/startup');const d=await r.json();l.innerHTML=(d.apps||[]).map(a=>'<div class="svc-row"><div class="svc-info"><span class="svc-name">'+a.name+'</span><span class="svc-desc">'+a.desc+'</span></div><label class="toggle"><input type="checkbox" checked onchange="toggleStartup(\''+a.name+'\',this.checked)"><span class="slider"></span></label></div>').join('')}catch(e){l.innerHTML='<p class="err">Failed to load</p>'}}
async function toggleStartup(n,e){try{await fetch('/api/startup/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,enable:e})})}catch(x){}}

// DISKS
async function loadDisks(){const l=document.getElementById('diskList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';try{const r=await fetch('/api/external-disk');const d=await r.json();l.innerHTML=(d.disks||[]).map(dk=>'<div class="svc-row"><div class="svc-info"><span class="svc-name">'+dk.device+' <span class="svc-desc">'+dk.mountpoint+'</span></span><span class="svc-desc">'+dk.fstype+' | '+fmtBytes(dk.used)+'/'+fmtBytes(dk.total)+' ('+dk.percent+'%) '+(dk.is_external?'<span class="svc-badge safe">External</span>':'')+'</span><div class="disk-bar"><div class="disk-fill" style="width:'+dk.percent+'%"></div></div></div><button class="btn sm" onclick="optimizeDisk(\''+dk.device+'\')">Optimize</button></div>').join('')}catch(e){l.innerHTML='<p class="err">Failed to load</p>'}}
async function optimizeDisk(d){showLoader('Optimizing '+d+'...');try{const r=await fetch('/api/external-disk/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:d})});const x=await r.json();hideLoader();showResults('disk',Array.isArray(x)?x:x.results||[])}catch(e){hideLoader();showResults('disk',[{success:false,message:e.message}])}}

// DRIVERS
async function loadDrivers(){const l=document.getElementById('driversList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';try{const r=await fetch('/api/drivers/scan');const d=await r.json();const m=await fetch('/api/drivers/missing');const md=await m.json();const ml=md.missing||[];let h='';if(ml.length){h+='<div class="svc-header"><h3 style="color:var(--rd)">Missing ('+ml.length+')</h3></div>';h+=ml.map(x=>'<div class="svc-row" style="border-left:2px solid var(--rd)"><div class="svc-info"><span class="svc-name">'+x.name+'</span><span class="svc-desc">'+x.class+' | '+x.status+'</span></div></div>').join('');h+='<div class="tool-row" style="margin:8px 0"><a class="btn sm" href="https://www.nvidia.com/Download/index.aspx" target="_blank">NVIDIA</a><a class="btn sm" href="https://www.amd.com/en/support" target="_blank">AMD</a><a class="btn sm" href="https://www.intel.com/content/www/us/en/download-center/home.html" target="_blank">Intel</a></div>'}const dr=d.drivers||[];h+='<div class="svc-header"><h3 style="color:var(--t)">Installed ('+dr.length+')</h3></div>';h+=dr.slice(0,25).map(x=>'<div class="svc-row"><div class="svc-info"><span class="svc-name">'+x.name+'</span><span class="svc-desc">'+(x.manufacturer||'')+' | v'+(x.version||'N/A')+'</span></div>'+(x.download_url?'<a class="btn sm" href="'+x.download_url+'" target="_blank">Download</a>':'')+'</div>').join('');l.innerHTML=h}catch(e){l.innerHTML='<p class="err">Failed to load</p>'}}

// TOOLBOX
async function setDNS(p){showLoader('DNS to '+p+'...');try{const r=await fetch('/api/toolbox/dns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:p})});const d=await r.json();hideLoader();showToolResult(d)}catch(e){hideLoader();showToolResult({success:false,message:e.message})}}
async function toolboxAction(a){showLoader(a+'...');try{const r=await fetch('/api/toolbox/'+a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})});const d=await r.json();hideLoader();showToolResult(d)}catch(e){hideLoader();showToolResult({success:false,message:e.message})}}
async function toolboxPost(a,d){showLoader(a+'...');try{const r=await fetch('/api/toolbox/'+a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});const x=await r.json();hideLoader();showToolResult(x)}catch(e){hideLoader();showToolResult({success:false,message:e.message})}}
async function toolboxPing(){showLoader('Pinging...');try{const r=await fetch('/api/toolbox/ping',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:'8.8.8.8'})});const d=await r.json();hideLoader();const e=document.getElementById('pingResult');if(e){e.style.display='block';e.textContent=d.output||d.message||'No result'}}catch(e){hideLoader()}}
async function loadHardwareInfo(){try{const r=await fetch('/api/toolbox/hardware');const d=await r.json();const e=document.getElementById('hwInfo');if(e&&d.info){e.style.display='block';e.innerHTML=Object.entries(d.info).map(([k,v])=>'<div class="hw-row"><span class="hw-key">'+k+'</span><span class="hw-val">'+v+'</span></div>').join('')}}catch(e){}}
function showToolResult(r){const c=document.getElementById('toolboxResultsList');const s=document.getElementById('toolboxResults');if(!c||!s)return;s.style.display='block';c.innerHTML='<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' '+(r.message||'Done')+'</div>'}

function showResults(cat,r){const c=document.getElementById(cat+'ResultsList');const s=document.getElementById(cat+'Results');if(!c||!s)return;s.style.display='block';if(Array.isArray(r))c.innerHTML=r.map((x,i)=>'<div class="result-item '+(x.success?'result-ok':'result-fail')+'" style="animation-delay:'+i*0.03+'s">'+(x.success?'&#10003;':'&#10007;')+' '+x.message+'</div>').join('')}
function showLoader(t){const o=document.getElementById('loader');const l=document.getElementById('loaderText');if(o)o.style.display='flex';if(l)l.textContent=t||'Optimizing...'}
function hideLoader(){const o=document.getElementById('loader');if(o)o.style.display='none'}

// THEMES
function setTheme(t){document.body.className='';if(t!=='dark')document.body.classList.add('theme-'+t);document.querySelectorAll('.theme-btn').forEach(b=>b.classList.remove('active'));const btn=document.querySelector('[data-theme="'+t+'"]');if(btn)btn.classList.add('active');localStorage.setItem('optinix-theme',t)}
function setAccent(c){document.documentElement.style.setProperty('--c',c);localStorage.setItem('optinix-accent',c)}
function setBg(b){document.body.classList.remove('bg-gradient','bg-mesh','bg-particles');if(b!=='none')document.body.classList.add('bg-'+b);const canvas=document.getElementById('bgCanvas');if(b==='particles'&&canvas){canvas.style.display='block';startParticles(canvas)}else if(canvas){canvas.style.display='none';stopParticles();document.body.classList.remove('bg-particles')}localStorage.setItem('optinix-bg',b)}
function toggleSidebar(mode){const s=document.querySelector('.sidebar');if(mode==='compact'){s.style.width='52px';s.style.minWidth='52px';s.querySelectorAll('.nav-btn span,.brand-name,.sidebar-footer').forEach(e=>e.style.display='none')}else if(mode==='hidden'){s.style.display='none'}else{s.style.width='';s.style.minWidth='';s.querySelectorAll('.nav-btn span,.brand-name,.sidebar-footer').forEach(e=>e.style.display='')}}

let particleAnim=null;
function startParticles(canvas){const ctx=canvas.getContext('2d');canvas.width=window.innerWidth;canvas.height=window.innerHeight;const particles=[];for(let i=0;i<50;i++)particles.push({x:Math.random()*canvas.width,y:Math.random()*canvas.height,vx:(Math.random()-.5)*.5,vy:(Math.random()-.5)*.5,r:Math.random()*2+1});function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);particles.forEach(p=>{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>canvas.width)p.vx*=-1;if(p.y<0||p.y>canvas.height)p.vy*=-1;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle='rgba(124,58,237,0.3)';ctx.fill()});particles.forEach((a,i)=>{particles.slice(i+1).forEach(b=>{const d=Math.hypot(a.x-b.x,a.y-b.y);if(d<120){ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle='rgba(124,58,237,'+(1-d/120)*0.15+')';ctx.stroke()}})});particleAnim=requestAnimationFrame(draw)}draw()}
function stopParticles(){if(particleAnim)cancelAnimationFrame(particleAnim)}

// Load saved theme
document.addEventListener('DOMContentLoaded',()=>{
    const saved=localStorage.getItem('optinix-theme');if(saved)setTheme(saved);
    const accent=localStorage.getItem('optinix-accent');if(accent)setAccent(accent);
    const bg=localStorage.getItem('optinix-bg');if(bg)setBg(bg);
    loadSystemInfo();setInterval(loadSystemInfo,2000);fetch('/api/system-info').then(()=>setTimeout(()=>fetch('/api/system-info'),500))
});
