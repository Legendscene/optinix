// ═══════════════════════════════════════════════════
// OPTINIX — Premium PC Optimizer JS
// ═══════════════════════════════════════════════════

function esc(s){if(!s)return'';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}

// ─── TOAST NOTIFICATION SYSTEM ───
var toastContainer=null;
function initToastContainer(){
    if(toastContainer)return;
    toastContainer=document.createElement('div');
    toastContainer.style.cssText='position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none';
    document.body.appendChild(toastContainer);
}
function showToast(msg,type){
    initToastContainer();
    var t=document.createElement('div');
    var bg=type==='success'?'rgba(0,255,136,.12)':type==='error'?'rgba(255,51,102,.12)':'rgba(0,212,255,.12)';
    var border=type==='success'?'rgba(0,255,136,.2)':type==='error'?'rgba(255,51,102,.2)':'rgba(0,212,255,.2)';
    var icon=type==='success'?'&#10003;':type==='error'?'&#10007;':'&#9432;';
    t.innerHTML='<span style="margin-right:8px">'+icon+'</span>'+esc(msg);
    t.style.cssText='background:'+bg+';backdrop-filter:blur(16px);border:1px solid '+border+';color:#f0f0f8;padding:12px 18px;border-radius:12px;font-size:.78rem;font-weight:500;pointer-events:auto;animation:slideInToast .3s ease;box-shadow:0 8px 32px rgba(0,0,0,.4);max-width:360px';
    toastContainer.appendChild(t);
    setTimeout(function(){t.style.opacity='0';t.style.transform='translateX(20px)';t.style.transition='all .3s ease';setTimeout(function(){if(t.parentNode)t.parentNode.removeChild(t)},300)},3000);
}
// Inject toast animation
var toastStyle=document.createElement('style');
toastStyle.textContent='@keyframes slideInToast{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:none}}';
document.head.appendChild(toastStyle);

// ─── SMOOTH PAGE TRANSITIONS ───
var currentPage='dashboard';
function showPage(p){
    if(p===currentPage){
        var e=document.getElementById('page-'+p);
        if(e){e.classList.add('active')}
        return;
    }
    // Fade out current
    var cur=document.getElementById('page-'+currentPage);
    if(cur){cur.style.opacity='0';cur.style.transform='translateY(-8px)';cur.style.transition='all .2s ease'}
    document.querySelectorAll('.nav-btn').forEach(function(x){x.classList.remove('active')});
    var n=document.querySelector('[data-page="'+p+'"]');
    if(n)n.classList.add('active');
    setTimeout(function(){
        if(cur){cur.classList.remove('active');cur.style.opacity='';cur.style.transform='';cur.style.transition=''}
        var e=document.getElementById('page-'+p);
        if(e){e.classList.add('active')}
        currentPage=p;
        if(p==='dashboard')setTimeout(loadSystemInfo,50);
        if(p==='services')setTimeout(loadServices,50);
        if(p==='startup')setTimeout(loadStartup,50);
        if(p==='disks')setTimeout(loadDisks,50);
        if(p==='gpu')setTimeout(loadGpuInfo,50);
        if(p==='game-profiles')setTimeout(loadGameProfiles,50);
    },200);
}

// ─── ANIMATED NUMBER COUNTERS ───
var animatedValues={};
function animateValue(id,target,suffix){
    suffix=suffix||'';
    var el=document.getElementById(id);
    if(!el)return;
    var current=animatedValues[id]||0;
    var diff=target-current;
    if(Math.abs(diff)<0.5){el.textContent=Math.round(target)+suffix;animatedValues[id]=target;return}
    var steps=20;
    var step=diff/steps;
    var i=0;
    function tick(){
        i++;
        current+=step;
        if(i>=steps){current=target}
        el.textContent=Math.round(current)+suffix;
        animatedValues[id]=current;
        if(i<steps)requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ─── SYSTEM INFO ───
function loadSystemInfo(){
    fetch('/api/system-info',{signal:AbortSignal.timeout(8000)}).then(function(r){return r.json()}).then(function(d){
        if(d.error)return;
        var cpu=Math.round(d.cpu?d.cpu.percent:0);
        animateValue('cpuValue',cpu,'%');sb('cpuBar',cpu);se('cpuInfo',(d.cpu?d.cpu.physical:'?')+' cores / '+(d.cpu?d.cpu.logical:'?')+' threads');

        var ram=Math.round(d.memory?d.memory.percent:0);
        animateValue('ramValue',ram,'%');sb('ramBar',ram);se('ramInfo',(d.memory?d.memory.used_gb:0)+'GB / '+(d.memory?d.memory.total_gb:0)+'GB');

        if(d.disk&&d.disk.length){var dk=d.disk[0];animateValue('diskValue',Math.round(dk.percent),'%');sb('diskBar',dk.percent);se('diskInfo',fb(dk.free)+' free / '+fb(dk.total))}

        var up=fs(d.network?d.network.speed_up:0),dn=fs(d.network?d.network.speed_down:0);
        se('netValue','<span class="speed-up">\u2191'+up+'</span> <span class="speed-down">\u2193'+dn+'</span>',true);
        se('netInfo','Sent: '+fb(d.network?d.network.bytes_sent:0)+' | Recv: '+fb(d.network?d.network.bytes_recv:0));
        var nb=document.getElementById('netBar');if(nb)nb.style.width=Math.min(100,Math.max(d.network?d.network.speed_up:0,d.network?d.network.speed_down:0,1)/1048576*100)+'%';

        if(d.gpu){se('gpuValue',(d.gpu.usage||0)+'%');sb('gpuBar',d.gpu.usage||0);var gt=d.gpu.name||'N/A';if(d.gpu.temperature)gt+=' | '+d.gpu.temperature+'\u00b0C';if(d.gpu.memory_total)gt+=' | '+fb((d.gpu.memory_used||0)*1048576)+'/'+fb(d.gpu.memory_total);se('gpuName',gt)}
        if(d.system){se('uptimeValue',d.system.uptime);se('sysInfo',d.system.os+' | '+d.system.processor)}
        if(d.cpu&&d.cpu.temperature){se('tempValue',d.cpu.temperature+'\u00b0C')}else{se('tempValue','N/A')}
        if(d.os){var b=document.getElementById('osBadge');if(b)b.textContent=d.os.os_name||'Unknown'}
    }).catch(function(err){
        se('cpuValue','ERR');se('ramValue','ERR');se('diskValue','ERR');
        se('gpuName','Error: '+err.message);se('uptimeValue','Retrying...');
        setTimeout(loadSystemInfo,5000);
    });
}

function se(id,v,html){var e=document.getElementById(id);if(e){if(html)e.innerHTML=v;else e.textContent=v}}
function sb(id,pct){var e=document.getElementById(id);if(e)e.style.width=pct+'%'}
function fb(b){if(!b)return'--';var k=1024,s=['B','KB','MB','GB','TB'];var i=Math.floor(Math.log(b)/Math.log(k));return parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]}
function fs(bps){if(!bps||bps<1)return'0 B/s';var k=1024,s=['B/s','KB/s','MB/s','GB/s'];var i=Math.floor(Math.log(bps)/Math.log(k));return parseFloat((bps/Math.pow(k,i)).toFixed(1))+s[i]}

// ─── OPTIMIZERS ───
function runOptimizer(c){showLoader(c+'...');fetch('/api/optimize/'+c,{method:'POST'}).then(function(r){return r.json()}).then(function(d){hideLoader();showResults(c,d.results||d);showToast(c+' optimization complete','success')}).catch(function(e){hideLoader();showResults(c,[{success:false,message:e.message}]);showToast(c+' failed','error')})}
function runAllOptimizations(){showLoader('Running all...');fetch('/api/optimize/all',{method:'POST'}).then(function(r){return r.json()}).then(function(d){hideLoader();var a=[];Object.keys(d).forEach(function(c){if(Array.isArray(d[c]))d[c].forEach(function(x){x.category=c;a.push(x)})});var el=document.getElementById('dashResultsList');var s=document.getElementById('dashResults');if(el&&s){s.style.display='block';el.innerHTML=a.map(function(r){return '<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' <strong>['+r.category.toUpperCase()+']</strong> '+r.message+'</div>'}).join('')}showToast('All optimizations complete','success')}).catch(function(e){hideLoader();showToast('Optimization failed','error')})}
function runExtremeTuning(){showLoader('Extreme mode...');fetch('/api/tuning/extreme',{method:'POST'}).then(function(r){return r.json()}).then(function(d){hideLoader();showResults('extreme',d.results||[]);showToast('Extreme mode activated','success')}).catch(function(e){hideLoader();showResults('extreme',[{success:false,message:e.message}]);showToast('Extreme mode failed','error')})}

// ─── SERVICES ───
function loadServices(){var l=document.getElementById('servicesList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/services').then(function(r){return r.json()}).then(function(d){l.innerHTML=(d.services||[]).map(function(s){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(s.name)+'</span><span class="svc-desc">'+esc(s.desc)+'</span>'+(s.safe?'<span class="svc-badge safe">Safe</span>':'<span class="svc-badge warn">Critical</span>')+'</div><label class="toggle"><input type="checkbox" '+(s.running?'checked':'')+' '+(s.safe?'':'disabled')+' onchange="toggleService(\''+esc(s.name).replace(/'/g,"\\'")+'\',this.checked)"><span class="slider"></span></label></div>'}).join('')}).catch(function(e){l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}
function toggleService(n,e){fetch('/api/services/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,enable:e})}).then(function(){showToast('Service toggled','success')}).catch(function(){showToast('Failed to toggle service','error')})}

// ─── STARTUP ───
function loadStartup(){var l=document.getElementById('startupList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/startup').then(function(r){return r.json()}).then(function(d){l.innerHTML=(d.apps||[]).map(function(a){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(a.name)+'</span><span class="svc-desc">'+esc(a.desc)+'</span></div><label class="toggle"><input type="checkbox" checked onchange="toggleStartup(\''+esc(a.name).replace(/'/g,"\\'")+'\',this.checked)"><span class="slider"></span></label></div>'}).join('')}).catch(function(e){l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}
function toggleStartup(n,e){fetch('/api/startup/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:n,enable:e})}).catch(function(){})}

// ─── DISKS ───
function loadDisks(){var l=document.getElementById('diskList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/external-disk').then(function(r){return r.json()}).then(function(d){l.innerHTML=(d.disks||[]).map(function(dk){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(dk.device)+' <span class="svc-desc">'+esc(dk.mountpoint)+'</span></span><span class="svc-desc">'+esc(dk.fstype)+' | '+fb(dk.used)+'/'+fb(dk.total)+' ('+dk.percent+'%) '+(dk.is_external?'<span class="svc-badge safe">External</span>':'')+'</span><div class="disk-bar"><div class="disk-fill" style="width:'+dk.percent+'%"></div></div></div><button class="btn sm" onclick="optimizeDisk(\''+esc(dk.device).replace(/'/g,"\\'")+'\')">Optimize</button></div>'}).join('')}).catch(function(e){l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}
function optimizeDisk(d){showLoader('Optimizing...');fetch('/api/external-disk/optimize',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device:d})}).then(function(r){return r.json()}).then(function(x){hideLoader();showResults('disk',Array.isArray(x)?x:x.results||[]);showToast('Disk optimized','success')}).catch(function(e){hideLoader();showResults('disk',[{success:false,message:e.message}]);showToast('Disk optimization failed','error')})}

// ─── DRIVERS ───
function loadDrivers(){var l=document.getElementById('driversList');if(!l)return;l.innerHTML='<div class="loader-mini"></div>';fetch('/api/drivers/scan').then(function(r){return r.json()}).then(function(d){var dr=d.drivers||[];var h='<div class="svc-header"><h3 style="color:var(--c)">Installed ('+dr.length+')</h3></div>';h+=dr.slice(0,20).map(function(x){return '<div class="svc-row"><div class="svc-info"><span class="svc-name">'+esc(x.name)+'</span><span class="svc-desc">'+esc(x.manufacturer||'')+' | v'+esc(x.version||'N/A')+'</span></div>'+(x.download_url?'<a class="btn sm" href="'+esc(x.download_url)+'" target="_blank">Download</a>':'')+'</div>'}).join('');l.innerHTML=h}).catch(function(e){l.innerHTML='<p class="err">Failed: '+esc(e.message)+'</p>'})}

// ─── TOOLBOX ───
function setDNS(p){showLoader('DNS...');fetch('/api/toolbox/dns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({provider:p})}).then(function(r){return r.json()}).then(function(d){hideLoader();showToolResult(d);showToast('DNS set to '+p,'success')}).catch(function(e){hideLoader();showToolResult({success:false,message:e.message});showToast('DNS change failed','error')})}
function toolboxAction(a){showLoader(a+'...');fetch('/api/toolbox/'+a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})}).then(function(r){return r.json()}).then(function(d){hideLoader();showToolResult(d);showToast(a+' complete','success')}).catch(function(e){hideLoader();showToolResult({success:false,message:e.message});showToast(a+' failed','error')})}
function toolboxPost(a,d){showLoader(a+'...');fetch('/api/toolbox/'+a,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(function(r){return r.json()}).then(function(x){hideLoader();showToolResult(x);showToast(a+' applied','success')}).catch(function(e){hideLoader();showToolResult({success:false,message:e.message});showToast(a+' failed','error')})}
function toolboxPing(){showLoader('Pinging...');fetch('/api/toolbox/ping',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({host:'8.8.8.8'})}).then(function(r){return r.json()}).then(function(d){hideLoader();var e=document.getElementById('pingResult');if(e){e.style.display='block';e.textContent=d.output||d.message||'No result'}}).catch(function(e){hideLoader()})}
function loadHardwareInfo(){fetch('/api/toolbox/hardware').then(function(r){return r.json()}).then(function(d){var e=document.getElementById('hwInfo');if(e&&d.info){e.style.display='block';e.innerHTML=Object.keys(d.info).map(function(k){return '<div class="hw-row"><span class="hw-key">'+esc(k)+'</span><span class="hw-val">'+esc(String(d.info[k]))+'</span></div>'}).join('')}}).catch(function(){})}

// ─── GPU INFO ───
function loadGpuInfo(){
    fetch('/api/system-info',{signal:AbortSignal.timeout(8000)}).then(function(r){return r.json()}).then(function(d){
        var e=document.getElementById('gpuDetails');if(!e)return;
        var g=d.gpu||{};
        e.innerHTML='<div class="hw-row"><span class="hw-key">Name</span><span class="hw-val">'+esc(g.name||'N/A')+'</span></div>'+
            '<div class="hw-row"><span class="hw-key">Usage</span><span class="hw-val">'+(g.usage||0)+'%</span></div>'+
            '<div class="hw-row"><span class="hw-key">Memory</span><span class="hw-val">'+(g.memory_total?Math.round(g.memory_used/1024)+'MB / '+Math.round(g.memory_total/1024)+'MB':'N/A')+'</span></div>'+
            '<div class="hw-row"><span class="hw-key">Temperature</span><span class="hw-val">'+(g.temperature?g.temperature+'°C':'N/A')+'</span></div>'+
            '<div class="hw-row"><span class="hw-key">Driver</span><span class="hw-val">'+esc(g.driver||'N/A')+'</span></div>';
    }).catch(function(){var e=document.getElementById('gpuDetails');if(e)e.innerHTML='<div class="result-item result-fail">GPU info unavailable</div>'});
}

// ─── SMART DETECT ───
function smartDetect(){fetch('/api/smart-detect').then(function(r){return r.json()}).then(function(d){var e=document.getElementById('recsList');if(!e||!d.recommendations)return;if(d.recommendations.length===0){e.innerHTML='<div class="result-item result-ok">System is optimized - no recommendations</div>';return}e.innerHTML=d.recommendations.map(function(r){return '<div class="result-item result-ok">'+esc(r.message)+'</div>'}).join('')}).catch(function(){var e=document.getElementById('recsList');if(e)e.innerHTML='<div class="result-item result-fail">Smart detection unavailable</div>'})}
setTimeout(smartDetect,2000);

// ─── RESULTS DISPLAY ───
function showToolResult(r){var c=document.getElementById('toolboxResultsList');var s=document.getElementById('toolboxResults');if(!c||!s)return;s.style.display='block';c.innerHTML='<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' '+(r.message||'Done')+'</div>'}
function showResults(cat,r){
    var c=document.getElementById(cat+'ResultsList');var s=document.getElementById(cat+'Results');
    if(!c||!s)return;s.style.display='block';
    if(Array.isArray(r))c.innerHTML=r.map(function(x,i){return '<div class="result-item '+(x.success?'result-ok':'result-fail')+'" style="animation-delay:'+i*0.03+'s">'+(x.success?'&#10003;':'&#10007;')+' '+x.message+'</div>'}).join('');
}
function showLoader(t){var o=document.getElementById('loader');var l=document.getElementById('loaderText');if(o)o.style.display='flex';if(l)l.textContent=t||'Working...'}
function hideLoader(){var o=document.getElementById('loader');if(o)o.style.display='none'}

// ─── THEME SYSTEM ───
function setTheme(t){document.body.className='';if(t!=='dark')document.body.classList.add('theme-'+t);document.querySelectorAll('.theme-btn').forEach(function(b){b.classList.remove('active')});var btn=document.querySelector('[data-theme="'+t+'"]');if(btn)btn.classList.add('active');localStorage.setItem('optinix-theme',t);showToast('Theme: '+t,'info')}
function setAccent(c){document.documentElement.style.setProperty('--c',c);localStorage.setItem('optinix-accent',c)}
function setBg(b){document.body.classList.remove('bg-gradient','bg-mesh','bg-particles');if(b!=='none')document.body.classList.add('bg-'+b);var canvas=document.getElementById('bgCanvas');if(b==='particles'&&canvas){canvas.style.display='block';startParticles(canvas)}else if(canvas){canvas.style.display='none';stopParticles()}localStorage.setItem('optinix-bg',b)}
function toggleSidebar(mode){var s=document.querySelector('.sidebar');if(mode==='compact'){s.style.width='54px';s.style.minWidth='54px';s.querySelectorAll('.nav-btn span,.brand-name,.sidebar-footer,.nav-group-label').forEach(function(e){e.style.display='none'})}else if(mode==='hidden'){s.style.display='none'}else{s.style.width='';s.style.minWidth='';s.querySelectorAll('.nav-btn span,.brand-name,.sidebar-footer,.nav-group-label').forEach(function(e){e.style.display=''})}}

// ─── PARTICLE BACKGROUND ───
var particleAnim=null;
function startParticles(c){var ctx=c.getContext('2d');c.width=window.innerWidth;c.height=window.innerHeight;var ps=[];for(var i=0;i<35;i++)ps.push({x:Math.random()*c.width,y:Math.random()*c.height,vx:(Math.random()-.5)*.25,vy:(Math.random()-.5)*.25,r:Math.random()*1.5+.5,a:Math.random()*.3+.1});function draw(){ctx.clearRect(0,0,c.width,c.height);ps.forEach(function(p){p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>c.width)p.vx*=-1;if(p.y<0||p.y>c.height)p.vy*=-1;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fillStyle='rgba(0,212,255,'+p.a+')';ctx.fill()});particleAnim=requestAnimationFrame(draw)}draw()}
function stopParticles(){if(particleAnim)cancelAnimationFrame(particleAnim)}

// ─── GAME PROFILES ───
function loadGameProfiles(){
    var grid=document.getElementById('gameProfilesGrid');
    if(!grid)return;
    grid.innerHTML='<div class="loader-mini"></div>';
    fetch('/api/game-profiles').then(function(r){return r.json()}).then(function(d){
        var profiles=d.profiles||[];
        if(!profiles.length){grid.innerHTML='<p style="color:var(--tx-3);padding:20px">No profiles available</p>';return}
        grid.innerHTML=profiles.map(function(p){
            return '<div class="panel card-hover" onclick="applyGameProfile(\''+esc(p.id)+'\')">'+
                '<div class="card-icon" style="background:rgba(168,85,247,.08);border-color:rgba(168,85,247,.15)">'+
                '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--pk)" stroke-width="1.5"><path d="M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258A4 4 0 0 0 17.32 5z"/></svg></div>'+
                '<h3>'+esc(p.name)+'</h3>'+
                '<p>'+esc(p.description)+'</p>'+
                (p.builtin?'<div class="tag-row"><span class="tag">Built-in</span></div>':'<div class="tag-row"><span class="tag">Custom</span></div>')+
                '<button class="btn sm primary">Apply Profile</button></div>';
        }).join('');
    }).catch(function(e){grid.innerHTML='<p class="err">Failed to load profiles: '+esc(e.message)+'</p>'});
}
function applyGameProfile(id){
    showLoader('Applying '+id+' profile...');
    fetch('/api/game-profiles/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({profile_id:id})}).then(function(r){return r.json()}).then(function(d){
        hideLoader();
        var results=d.results||[];
        var s=document.getElementById('gameProfilesResults');var l=document.getElementById('gameProfilesResultsList');
        if(s&&l){s.style.display='block';l.innerHTML=results.map(function(r){return '<div class="result-item '+(r.success?'result-ok':'result-fail')+'">'+(r.success?'&#10003;':'&#10007;')+' '+r.message+'</div>'}).join('')}
        showToast(id+' profile applied','success');
    }).catch(function(e){hideLoader();showToast('Profile apply failed','error')});
}
function detectGame(){
    var el=document.getElementById('detectedGame');
    if(el)el.innerHTML='<div class="loader-mini"></div>';
    fetch('/api/game-profiles/detect').then(function(r){return r.json()}).then(function(d){
        if(d.detected){
            if(el)el.innerHTML='<span style="color:var(--gn);font-weight:600">&#9679; Detected: '+esc(d.game_name)+'</span> <button class="btn sm primary" onclick="applyGameProfile(\''+esc(d.game_id)+'\')" style="margin-left:8px">Apply Profile</button>';
            showToast('Game detected: '+d.game_name,'success');
        }else{
            if(el)el.innerHTML='<span style="color:var(--tx-3)">No known game running</span>';
        }
    }).catch(function(e){if(el)el.innerHTML='<span style="color:var(--rd)">Detection failed</span>'});
}

// ─── INIT ───
document.addEventListener('DOMContentLoaded',function(){
    var saved=localStorage.getItem('optinix-theme');if(saved)setTheme(saved);
    var accent=localStorage.getItem('optinix-accent');if(accent)setAccent(accent);
    var bg=localStorage.getItem('optinix-bg');if(bg)setBg(bg);
    loadSystemInfo();
    setInterval(loadSystemInfo,3000);
});
