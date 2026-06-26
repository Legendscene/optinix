function showPage(page){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(n=>n.classList.remove('active'));
    const el=document.getElementById('page-'+page);
    const nav=document.querySelector('[data-page="'+page+'"]');
    if(el)el.classList.add('active');
    if(nav)nav.classList.add('active');
    if(page==='dashboard')loadSystemInfo();
}

async function loadSystemInfo(){
    try{
        const r=await fetch('/api/system-info');
        const d=await r.json();
        animate('cpuValue',d.cpu.percent,'%');
        animate('ramValue',d.memory.percent,'%');
        if(d.disk&&d.disk.length){animate('diskValue',d.disk[0].percent,'%');bar('diskBar',d.disk[0].percent)}
        bar('cpuBar',d.cpu.percent);
        bar('ramBar',d.memory.percent);
        document.getElementById('netValue').textContent=fmt(d.network.bytes_recv);
        if(d.os){const b=document.getElementById('osBadge');if(b)b.textContent=d.os.os_name}
    }catch(e){console.error(e)}
}

function animate(id,target,suffix){
    const el=document.getElementById(id);if(!el)return;
    let cur=0;const step=Math.max(1,Math.floor(target/25));
    const iv=setInterval(()=>{cur+=step;if(cur>=target){cur=target;clearInterval(iv)}el.textContent=cur+suffix},25);
}
function bar(id,pct){const el=document.getElementById(id);if(!el)return;setTimeout(()=>{el.style.width=pct+'%'},80)}
function fmt(b){if(!b)return'--';const k=1024,s=['B','KB','MB','GB','TB'];const i=Math.floor(Math.log(b)/Math.log(k));return parseFloat((b/Math.pow(k,i)).toFixed(1))+' '+s[i]}

async function runOptimizer(cat){
    showLoader(cat+'...');
    try{
        const r=await fetch('/api/optimize/'+cat,{method:'POST'});
        const d=await r.json();
        hideLoader();
        showResults(cat,d.results||d);
    }catch(e){
        hideLoader();
        showResults(cat,[{success:false,message:'Error: '+e.message}]);
    }
}

async function runAllOptimizations(){
    showLoader('Running all optimizers...');
    try{
        const r=await fetch('/api/optimize/all',{method:'POST'});
        const d=await r.json();
        hideLoader();
        let all=[];
        Object.entries(d).forEach(([cat,res])=>{
            if(Array.isArray(res))res.forEach(r=>all.push({...r,category:cat}));
        });
        const c=document.getElementById('dashResultsList');
        const s=document.getElementById('dashResults');
        if(c&&s){s.style.display='block';c.innerHTML=all.map(r=>{
            const cls=r.success?'result-ok':'result-fail';
            const icon=r.success?'&#10003;':'&#10007;';
            const pre=r.category?'<strong>['+r.category.toUpperCase()+']</strong> ':'';
            return'<div class="result-item '+cls+'">'+icon+' '+pre+r.message+'</div>';
        }).join('')}
    }catch(e){hideLoader();showResults('dashboard',[{success:false,message:'Error: '+e.message}])}
}

function showResults(cat,results){
    const c=document.getElementById(cat+'ResultsList');
    const s=document.getElementById(cat+'Results');
    if(!c||!s)return;
    s.style.display='block';
    if(Array.isArray(results)){
        c.innerHTML=results.map((r,i)=>{
            const cls=r.success?'result-ok':'result-fail';
            const icon=r.success?'&#10003;':'&#10007;';
            return'<div class="result-item '+cls+'" style="animation-delay:'+i*0.04+'s">'+icon+' '+r.message+'</div>';
        }).join('');
    }
}

function showLoader(text){
    const o=document.getElementById('loader');
    const t=document.getElementById('loaderText');
    if(o)o.style.display='flex';
    if(t)t.textContent=text||'Optimizing...';
}
function hideLoader(){const o=document.getElementById('loader');if(o)o.style.display='none'}

document.addEventListener('DOMContentLoaded',()=>{loadSystemInfo();setInterval(loadSystemInfo,5000)});
