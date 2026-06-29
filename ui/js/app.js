function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}

function showPage(p){
    console.log('[nav] showPage:', p);
    document.querySelectorAll('.page').forEach(function(x){x.classList.remove('active')});
    document.querySelectorAll('.nav-btn').forEach(function(x){x.classList.remove('active')});
    var e=document.getElementById('page-'+p);
    var n=document.querySelector('[data-page="'+p+'"]');
    if(e){e.classList.add('active');console.log('[nav] page shown:',p)}else{console.warn('[nav] page not found:','page-'+p)}
    if(n){n.classList.add('active')}else{console.warn('[nav] nav button not found:',p)}
    if(p==='dashboard')setTimeout(loadSystemInfo,50);
    if(p==='services')setTimeout(loadServices,50);
    if(p==='startup')setTimeout(loadStartup,50);
    if(p==='disks')setTimeout(loadDisks,50);
    if(p==='gpu')setTimeout(loadGpuInfo,50);
}

function loadSystemInfo(){
    console.log('[sysinfo] fetching /api/system-info');
    fetch('/api/system-info',{signal:AbortSignal.timeout(8000)}).then(function(r){
        console.log('[sysinfo] response status:', r.status);
        return r.json()
    }).then(function(d){
        if(d.error){console.error('[sysinfo] API error:', d.error);return}
        console.log('[sysinfo] data received:', Object.keys(d).join(', '));

        var cpu=Math.round(d.cpu?d.cpu.percent:0);
        se('cpuValue',cpu+'%');sb('cpuBar',cpu);se('cpuInfo',(d.cpu?d.cpu.physical:'?')+' cores / '+(d.cpu?d.cpu.logical:'?')+' threads');
        if(!d.cpu)console.warn('[sysinfo] CPU data missing');

        var ram=Math.round(d.memory?d.memory.percent:0);
        se('ramValue',ram+'%');sb('ramBar',ram);se('ramInfo',(d.memory?d.memory.used_gb:0)+'GB / '+(d.memory?d.memory.total_gb:0)+'GB');
        if(!d.memory)console.warn('[sysinfo] RAM data missing');

        if(d.disk&&d.disk.length){var dk=d.disk[0];se('diskValue',Math.round(dk.percent)+'%');sb('diskBar',dk.percent);se('diskInfo',fb(dk.free)+' free / '+fb(dk.total))}
        else{console.warn('[sysinfo] Disk data missing');se('diskValue','N/A')}

        var up=fs(d.network?d.network.speed_up:0),dn=fs(d.network?d.network.speed_down:0);
        se('netValue','<span class="speed-up">\u2191'+up+'</span> <span class="speed-down">\u2193'+dn+'</span>',true);
        se('netInfo','Sent: '+fb(d.network?d.network.bytes_sent:0)+' | Recv: '+fb(d.network?d.network.bytes_recv:0));
        var nb=document.getElementById('netBar');if(nb)nb.style.width=Math.min(100,Math.max(d.network?d.network.speed_up:0,d.network?d.network.speed_down:0,1)/1048576*100)+'%';
        if(d.gpu){se('gpuValue',(d.gpu.usage||0)+'%');sb('gpuBar',d.gpu.usage||0);var gt=d.gpu.name||'N/A';if(d.gpu.temperature)gt+=' | '+d.gpu.temperature+'\u00b0C';if(d.gpu.memory_total)gt+=' | '+fb((d.gpu.memory_used||0)*1048576)+'/'+fb(d.gpu.memory_total);se('gpuName',gt)}
        else{console.warn('[sysinfo] GPU data missing');se('gpuName','N/A')}

        if(d.system){se('uptimeValue',d.system.uptime);se('sysInfo',d.system.os+' | '+d.system.processor)}
        else{console.warn('[sysinfo] System data missing')}

        if(d.cpu&&d.cpu.temperature){se('tempValue',d.cpu.temperature+'\u00b0C')}
        else{se('tempValue','N/A')}

        if(d.os){var b=document.getElementById('osBadge');if(b)b.textContent=d.os.os_name||'Unknown'}
        console.log('[sysinfo] dashboard updated successfully');
    }).catch(function(err){
        console.error('[sysinfo] fetch failed:', err.message || err);
        se('cpuValue','ERR');se('ramValue','ERR');se('diskValue','ERR');
        se('gpuName','Error: '+err.message);
        se('uptimeValue','Retrying...');
        setTimeout(loadSystemInfo,5000);
    });
}

function se(id,v,html){var e=document.getElementById(id);if(e){if(html)e.innerHTML=v;else e.textContent=v}}
function sb(id,pct){var e=document.getElementById(id);if(e)e.style.width=pct+'%'}
function fb(b){if(!b)return'--';var k=1024,s=['B','KB','MB','GB','TB'];var i=Math.floor(Math.log(b)/Math.log(k));return parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]}
function fs(bps){if(!bps||bps<1)return'0 B/s';var k=1024,s=['B/s','KB/s','MB/s','GB/s'];var i=Math.floor(Math.log(bps)/Math.log(k));return parseFloat((bps/Math.pow(k,i)).toFixed(1))+s[i]}

function runOptimizer(c){console.log('[optimizer] running:',c);showLoader(c+'...');fetch('/api/optimize/'+c,{method:'POST'}).then(function(r){return r.json()}).then(function(d){hideLoader();showResults(c,d.results||d)}).catch(function(e){hideLoader();console.error('[optimizer] failed:',c,e);showResults(c,[{success:false,message:e.message}])})}
function runAllOptimizations(){showLoader('Running all...');fetch('/api/optimize/all',{method:'POST'}).then(function(r){return r.json()}).then(function(d){hideLoader();var a=[];Object.keys(d).forEach(function(c){if(Array.isArray(d[c]))d[c].forEach(function(x){x.category=c;a.push(x)})});var el=document.getElementById('dashResultsList');var s=document.getElementById('dashResults');if(el&&s){s.style.display='block';el.innerHTML=a.map(function(r){return '<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' <strong>['+r.category.toUpperCase()+']</strong> '+r.message+'</div>'}).join('')}}).catch(function(e){hideLoader();console.error('[optimizer] all failed:',e)})}
function runExtremeTuning(){showLoader('Extreme mode...');fetch('/api/tuning/extreme',{method:'POST'}).then(function(r){return r.json()}).then(function(d){hideLoader();showResults('extreme',d.results||[])}).catch(function(e){hideLoader();console.error('[extreme] failed:',e);showResults('extreme',[{success:false,message:e.message}])})}

function loadServices(){console.log('[services] loading');var l=document.getElementById('servicesList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/services').then(function(r){return r.json()}).then(function(d){l.innerHTML=(d.services||[]).map(function(s){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(s.name)+'</span><span class="svc-desc">'+esc(s.desc)+'</span>'+(s.safe?'<span class="svc-badge safe">Safe</span>':'<span class="svc-badge warn">Critical</span>')+'</div><label class="toggle"><input type="checkbox" '+(s.running?'checked':'')+' '+(s.safe?'':'disabled')+' onchange="toggleService(\''+esc(s.name).replace(/'/g,"\\'")+'\',this.checked)"><span class="slider"></span></label></div>'}).join('')}).catch(function(e){console.error('[services] failed:',e);l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}
function toggleService(n,e){fetch('/api/services/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,enable:e})}).catch(function(e){console.error('[services] toggle failed:',e)})}

function loadStartup(){console.log('[startup] loading');var l=document.getElementById('startupList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/startup').then(function(r){return r.json()}).then(function(d){l.innerHTML=(d.apps||[]).map(function(a){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(a.name)+'</span><span class="svc-desc">'+esc(a.desc)+'</span></div><label class="toggle"><input type="checkbox" checked onchange="toggleStartup(\''+esc(a.name).replace(/'/g,"\\'")+'\',this.checked)"><span class="slider"></span></label></div>'}).join('')}).catch(function(e){console.error('[startup] failed:',e);l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}
function toggleStartup(n,e){fetch('/api/startup/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,enable:e})}).catch(function(e){console.error('[startup] toggle failed:',e)})}

function loadDisks(){console.log('[disks] loading');var l=document.getElementById('diskList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/external-disk').then(function(r){return r.json()}).then(function(d){l.innerHTML=(d.disks||[]).map(function(dk){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(dk.device)+' <span class="svc-desc">'+esc(dk.mountpoint)+'</span></span><span class="svc-desc">'+esc(dk.fstype)+' | '+fb(dk.used)+'/'+fb(dk.total)+' ('+dk.percent+'%) '+(dk.is_external?'<span class="svc-badge safe">External</span>':'')+'</span><div class="disk-bar"><div class="disk-fill" style="width:'+dk.percent+'%"></div></div></div><button class="btn sm" onclick="optimizeDisk(\''+esc(dk.device).replace(/'/g,"\\'")+'\')">Optimize</button></div>'}).join('')}).catch(function(e){console.error('[disks] failed:',e);l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}
function optimizeDisk(d){showLoader('Optimizing...');fetch('/api/external-disk/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:d})}).then(function(r){return r.json()}).then(function(x){hideLoader();showResults('disk',Array.isArray(x)?x:x.results||[])}).catch(function(e){hideLoader();console.error('[disks] opt failed:',e);showResults('disk',[{success:false,message:e.message}])})}

function loadDrivers(){console.log('[drivers] loading');var l=document.getElementById('driversList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/drivers/scan').then(function(r){return r.json()}).then(function(d){var dr=d.drivers||[];var h='<div class="svc-header"><h3 style="color:var(--t)">Installed ('+dr.length+')</h3></div>';h+=dr.slice(0,20).map(function(x){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(x.name)+'</span><span class="svc-desc">'+esc(x.manufacturer||'')+' | v'+esc(x.version||'N/A')+'</span></div>'+(x.download_url?'<a class="btn sm" href="'+esc(x.download_url)+'" target="_blank">Download</a>':'')+'</div>'}).join('');l.innerHTML=h}).catch(function(e){console.error('[drivers] failed:',e);l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}

function setDNS(p){showLoader('DNS...');fetch('/api/toolbox/dns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:p})}).then(function(r){return r.json()}).then(function(d){hideLoader();showToolResult(d)}).catch(function(e){hideLoader();showToolResult({success:false,message:e.message})})}
function toolboxAction(a){showLoader(a+'...');fetch('/api/toolbox/'+a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})}).then(function(r){return r.json()}).then(function(d){hideLoader();showToolResult(d)}).catch(function(e){hideLoader();showToolResult({success:false,message:e.message})})}
function toolboxPost(a,d){showLoader(a+'...');fetch('/api/toolbox/'+a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(x){hideLoader();showToolResult(x)}).catch(function(e){hideLoader();showToolResult({success:false,message:e.message})})}
function toolboxPing(){showLoader('Pinging...');fetch('/api/toolbox/ping',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:'8.8.8.8'})}).then(function(r){return r.json()}).then(function(d){hideLoader();var e=document.getElementById('pingResult');if(e){e.style.display='block';e.textContent=d.output||d.message||'No result'}}).catch(function(e){hideLoader();console.error('[ping] failed:',e)})}
function loadHardwareInfo(){fetch('/api/toolbox/hardware').then(function(r){return r.json()}).then(function(d){var e=document.getElementById('hwInfo');if(e&&d.info){e.style.display='block';e.innerHTML=Object.keys(d.info).map(function(k){return '<div class="hw-row"><span class="hw-key">'+esc(k)+'</span><span class="hw-val">'+esc(String(d.info[k]))+'</span></div>'}).join('')}}).catch(function(e){console.error('[hardware] failed:',e)})}

function loadGpuInfo(){
    console.log('[gpu] fetching GPU info');
    fetch('/api/system-info',{signal:AbortSignal.timeout(8000)}).then(function(r){return r.json()}).then(function(d){
        var e=document.getElementById('gpuDetails');
        if(!e)return;
        var g=d.gpu||{};
        e.innerHTML='<div class="hw-row"><span class="hw-key">Name</span><span class="hw-val">'+esc(g.name||'N/A')+'</span></div>'+
            '<div class="hw-row"><span class="hw-key">Usage</span><span class="hw-val">'+(g.usage||0)+'%</span></div>'+
            '<div class="hw-row"><span class="hw-key">Memory</span><span class="hw-val">'+(g.memory_total?Math.round(g.memory_used/1024)+'MB / '+Math.round(g.memory_total/1024)+'MB':'N/A')+'</span></div>'+
            '<div class="hw-row"><span class="hw-key">Temperature</span><span class="hw-val">'+(g.temperature?g.temperature+'°C':'N/A')+'</span></div>'+
            '<div class="hw-row"><span class="hw-key">Driver</span><span class="hw-val">'+esc(g.driver||'N/A')+'</span></div>';
        console.log('[gpu] GPU info updated');
    }).catch(function(err){
        console.error('[gpu] failed:', err.message);
        var e=document.getElementById('gpuDetails');
        if(e)e.innerHTML='<div class="result-item result-fail">GPU info unavailable</div>';
    });
}

function smartDetect(){console.log('[smart] fetching recommendations');fetch('/api/smart-detect').then(function(r){return r.json()}).then(function(d){var e=document.getElementById('recsList');if(!e||!d.recommendations)return;if(d.recommendations.length===0){e.innerHTML='<div class="result-item result-ok">No recommendations needed</div>';return}e.innerHTML=d.recommendations.map(function(r){return '<div class="result-item result-ok" style="animation-delay:0s">'+esc(r.message)+'</div>'}).join('')}).catch(function(err){console.error('[smart] failed:',err);var e=document.getElementById('recsList');if(e)e.innerHTML='<div class="result-item result-fail">Smart detection unavailable</div>'})}
setTimeout(smartDetect,2000)

function showToolResult(r){var c=document.getElementById('toolboxResultsList');var s=document.getElementById('toolboxResults');if(!c||!s)return;s.style.display='block';c.innerHTML='<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' '+(r.message||'Done')+'</div>'}

function showResults(cat,r){var c=document.getElementById(cat+'ResultsList');var s=document.getElementById(cat+'Results');if(!c||!s)return;s.style.display='block';if(Array.isArray(r))c.innerHTML=r.map(function(x,i){return '<div class="result-item '+(x.success?'result-ok':'result-fail')+'" style="animation-delay:'+i*0.03+'s">'+(x.success?'&#10003;':'&#10007;')+' '+x.message+'</div>'}).join('')}
function showLoader(t){var o=document.getElementById('loader');var l=document.getElementById('loaderText');if(o)o.style.display='flex';if(l)l.textContent=t||'Working...'}
function hideLoader(){var o=document.getElementById('loader');if(o)o.style.display='none'}

function setTheme(t){console.log('[theme] setting:',t);document.body.className='';if(t!=='dark')document.body.classList.add('theme-'+t);document.querySelectorAll('.theme-btn').forEach(function(b){b.classList.remove('active')});var btn=document.querySelector('[data-theme="'+t+'"]');if(btn)btn.classList.add('active');localStorage.setItem('optinix-theme',t)}
function setAccent(c){document.documentElement.style.setProperty('--c',c);localStorage.setItem('optinix-accent',c)}
function setBg(b){document.body.classList.remove('bg-gradient','bg-mesh','bg-particles');if(b!=='none')document.body.classList.add('bg-'+b);var canvas=document.getElementById('bgCanvas');if(b==='particles'&&canvas){canvas.style.display='block';startParticles(canvas)}else if(canvas){canvas.style.display='none';stopParticles()}localStorage.setItem('optinix-bg',b)}
function toggleSidebar(mode){var s=document.querySelector('.sidebar');if(mode==='compact'){s.style.width='52px';s.style.minWidth='52px';s.querySelectorAll('.nav-btn span,.brand-name,.sidebar-footer').forEach(function(e){e.style.display='none'})}else if(mode==='hidden'){s.style.display='none'}else{s.style.width='';s.style.minWidth='';s.querySelectorAll('.nav-btn span,.brand-name,.sidebar-footer').forEach(function(e){e.style.display=''})}}
var particleAnim=null;
function startParticles(c){var ctx=c.getContext('2d');c.width=window.innerWidth;c.height=window.innerHeight;var ps=[];for(var i=0;i<30;i++)ps.push({x:Math.random()*c.width,y:Math.random()*c.height,vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,r:Math.random()*2+1});function draw(){ctx.clearRect(0,0,c.width,c.height);ps.forEach(function(p){p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>c.width)p.vx*=-1;if(p.y<0||p.y>c.height)p.vy*=-1;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle='rgba(124,58,237,0.3)';ctx.fill()});particleAnim=requestAnimationFrame(draw)}draw()}
function stopParticles(){if(particleAnim)cancelAnimationFrame(particleAnim)}

document.addEventListener('DOMContentLoaded',function(){
    console.log('[app] DOMContentLoaded - initializing Optinix');
    var saved=localStorage.getItem('optinix-theme');if(saved)setTheme(saved);
    var accent=localStorage.getItem('optinix-accent');if(accent)setAccent(accent);
    var bg=localStorage.getItem('optinix-bg');if(bg)setBg(bg);
    console.log('[app] loading initial system info');
    loadSystemInfo();
    setInterval(loadSystemInfo,3000);
    console.log('[app] initialization complete');
});
