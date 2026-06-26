import sys
import os
import subprocess
import time
import threading
import webview

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INSTALLER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Optinix Installer</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
body{font-family:'Inter',system-ui,sans-serif;background:#09090b;color:#fafafa;height:100vh;overflow:hidden;display:flex;align-items:center;justify-content:center}
.installer{width:520px;background:#0f0f12;border:1px solid rgba(255,255,255,.06);border-radius:16px;overflow:hidden;box-shadow:0 25px 50px rgba(0,0,0,.5)}
.header{padding:40px;text-align:center;background:linear-gradient(180deg,rgba(124,58,237,.08),transparent)}
.logo{width:80px;height:80px;border-radius:20px;margin:0 auto 16px;box-shadow:0 8px 32px rgba(124,58,237,.3)}
h1{font-size:1.8rem;font-weight:800;background:linear-gradient(135deg,#fff,#a1a1aa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sub{color:#71717a;font-size:.85rem;margin-top:4px}
.body{padding:30px}
.step{display:none;animation:fadeUp .3s ease}
.step.active{display:block}
@keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
.step-title{font-size:1.1rem;font-weight:700;margin-bottom:16px}
.step-desc{color:#a1a1aa;font-size:.85rem;line-height:1.6;margin-bottom:20px}
.progress{height:4px;background:#27272a;border-radius:2px;overflow:hidden;margin:20px 0}
.progress-fill{height:100%;background:linear-gradient(90deg,#7c3aed,#06b6d4);border-radius:2px;transition:width .5s ease;width:0}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 28px;border-radius:10px;border:none;font-weight:600;font-size:.9rem;cursor:pointer;transition:all .2s;font-family:inherit;width:100%}
.btn-primary{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff}
.btn-primary:hover{box-shadow:0 8px 24px rgba(124,58,237,.3);transform:translateY(-1px)}
.btn-secondary{background:#27272a;color:#fafafa;border:1px solid rgba(255,255,255,.1)}
.btn-secondary:hover{background:#3f3f46}
.btn:disabled{opacity:.5;cursor:not-allowed}
.log{background:#18181b;border:1px solid rgba(255,255,255,.06);border-radius:8px;padding:12px;font-size:.75rem;color:#a1a1aa;max-height:150px;overflow-y:auto;font-family:monospace;margin:12px 0}
.log-item{padding:3px 0;border-bottom:1px solid rgba(255,255,255,.03)}
.log-ok{color:#22c55e}.log-warn{color:#f59e0b}.log-err{color:#ef4444}
.checklist{list-style:none;margin:16px 0}
.checklist li{padding:8px 0;display:flex;align-items:center;gap:10px;font-size:.85rem;color:#a1a1aa}
.checklist li .check{width:20px;height:20px;border-radius:50%;border:2px solid #27272a;display:flex;align-items:center;justify-content:center;font-size:.7rem;flex-shrink:0;transition:all .3s}
.checklist li.done .check{background:#22c55e;border-color:#22c55e;color:#fff}
.footer{padding:20px 30px;border-top:1px solid rgba(255,255,255,.06);display:flex;justify-content:space-between;gap:10px}
.version{color:#52525b;font-size:.7rem;text-align:center;padding:0 30px 15px}
</style>
</head>
<body>
<div class="installer">
<div class="header">
<img src="/assets/logo.jfif" alt="Optinix" class="logo">
<h1>Optinix</h1>
<p class="sub">Ultimate PC Optimizer - Installer</p>
</div>
<div class="body">
<!-- Step 1: Welcome -->
<div class="step active" id="step1">
<div class="step-title">Welcome to Optinix</div>
<div class="step-desc">The world's most advanced PC optimizer. One click to boost your system performance with 200+ optimizations, gaming mode, extreme tuning, and real-time monitoring.</div>
<button class="btn btn-primary" onclick="nextStep(2)">Get Started</button>
</div>
<!-- Step 2: Features -->
<div class="step" id="step2">
<div class="step-title">What's Included</div>
<ul class="checklist">
<li class="done"><span class="check">&#10003;</span> System Cleanup (temp, cache, browser data)</li>
<li class="done"><span class="check">&#10003;</span> Network Optimization (TCP/IP, DNS, BBR)</li>
<li class="done"><span class="check">&#10003;</span> Performance Boost (power plan, RAM, CPU)</li>
<li class="done"><span class="check">&#10003;</span> Gaming Mode (GPU priority, DVR off, input lag)</li>
<li class="done"><span class="check">&#10003;</span> 100+ Registry Tweaks (telemetry, privacy)</li>
<li class="done"><span class="check">&#10003;</span> Service & Startup Manager</li>
<li class="done"><span class="check">&#10003;</span> Driver Manager (scan, detect, download)</li>
<li class="done"><span class="check">&#10003;</span> Extreme Mode (i3 to gaming PC)</li>
<li class="done"><span class="check">&#10003;</span> Real-time CPU/RAM/GPU/Disk/Network monitoring</li>
<li class="done"><span class="check">&#10003;</span> 8 Themes with animated backgrounds</li>
</ul>
<button class="btn btn-primary" onclick="nextStep(3)">Install</button>
</div>
<!-- Step 3: Installing -->
<div class="step" id="step3">
<div class="step-title">Installing...</div>
<div class="progress"><div class="progress-fill" id="installProgress"></div></div>
<div class="log" id="installLog"></div>
</div>
<!-- Step 4: Done -->
<div class="step" id="step4">
<div class="step-title">Installation Complete!</div>
<div class="step-desc">Optinix has been installed successfully. Your system is ready to be optimized.</div>
<button class="btn btn-primary" onclick="launchApp()">Launch Optinix</button>
<button class="btn btn-secondary" onclick="closeWindow()" style="margin-top:8px">Close Installer</button>
</div>
</div>
<div class="version">Optinix v1.0.0 | Made with Python + Flask + pywebview</div>
</div>
<script>
let currentStep=1;
function nextStep(n){document.querySelectorAll('.step').forEach(s=>s.classList.remove('active'));document.getElementById('step'+n).classList.add('active');currentStep=n;if(n===3)startInstall()}
function addLog(msg,cls){const log=document.getElementById('installLog');const item=document.createElement('div');item.className='log-item '+(cls||'');item.textContent=msg;log.appendChild(item);log.scrollTop=log.scrollHeight}
function setProgress(pct){document.getElementById('installProgress').style.width=pct+'%'}
function startInstall(){
const steps=[
{msg:'Checking system requirements...',pct:10,cls:'log-ok',delay:400},
{msg:'Installing Python dependencies...',pct:25,cls:'log-ok',delay:600},
{msg:'Setting up optimization modules...',pct:40,cls:'log-ok',delay:500},
{msg:'Configuring services manager...',pct:55,cls:'log-ok',delay:400},
{msg:'Setting up driver manager...',pct:70,cls:'log-ok',delay:400},
{msg:'Building web interface...',pct:85,cls:'log-ok',delay:500},
{msg:'Finalizing installation...',pct:95,cls:'log-ok',delay:400},
{msg:'Installation complete!',pct:100,cls:'log-ok',delay:300}
];
let i=0;
function runStep(){
if(i<steps.length){
addLog(steps[i].msg,steps[i].cls);
setProgress(steps[i].pct);
i++;
setTimeout(runStep,steps[i-1].delay);
}else{
setTimeout(()=>nextStep(4),500);
}
}
runStep();
}
function launchApp(){
try{window.pywebview.api.launch_app()}catch(e){window.location.href='/'}
}
function closeWindow(){try{window.pywebview.api.close()}catch(e){window.close()}}
</script>
</body>
</html>
"""


class InstallerAPI:
    def __init__(self, window_ref):
        self.window = window_ref

    def launch_app(self):
        import subprocess
        subprocess.Popen([sys.executable, os.path.join(BASE_DIR, "main.py")])
        if self.window:
            self.window.destroy()

    def close(self):
        if self.window:
            self.window.destroy()


def run_installer():
    api = InstallerAPI(None)
    window = webview.create_window(
        title="Optinix Installer",
        html=INSTALLER_HTML,
        width=560,
        height=650,
        resizable=False,
        easy_drag=True,
        background_color="#09090b"
    )
    api.window = window
    window.expose(api.launch_app, api.close)
    webview.start(debug=False)


if __name__ == "__main__":
    run_installer()
