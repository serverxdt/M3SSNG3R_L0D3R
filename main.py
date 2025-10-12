# convox2_demo.py
# CONVO'X-2 — Safe Simulation Demo (no external posting)
# Run: python convox2_demo.py
from flask import Flask, render_template_string, request, redirect, url_for, Response, jsonify
import threading, time, uuid, queue, random, json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'convox2-demo-secret'

# In-memory job state (for demo)
jobs = {}
log_queues = {}  # job_id -> queue.Queue()

# HTML+CSS+JS template (single-file)
TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CONVO'X-2 — Demo</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
<style>
  :root{
    --bg1: #ff007f;
    --bg2: #8a2be2;
    --glass: rgba(255,255,255,0.06);
    --accent: rgba(255,255,255,0.06);
    --text: #f8f8ff;
  }
  html,body{height:100%;margin:0;font-family:Poppins, sans-serif;background:linear-gradient(135deg,var(--bg1),var(--bg2));color:var(--text);overflow:hidden}
  .wrap{display:grid;grid-template-columns:420px 1fr;gap:24px;height:100vh;padding:28px;}
  .panel{background:linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));backdrop-filter: blur(8px);border-radius:18px;padding:18px;box-shadow:0 8px 30px rgba(0,0,0,0.4);border:1px solid rgba(255,255,255,0.06);overflow:auto}
  h1{font-family:Orbitron, monospace;margin:0 0 6px 0;font-size:20px;letter-spacing:1px}
  p.lead{margin:0 0 14px 0;font-size:13px;opacity:0.9}
  label{display:block;margin:10px 0 6px;font-size:13px;opacity:0.95}
  input[type=text], input[type=number], .file-input, textarea{width:100%;padding:10px;border-radius:10px;border:1px solid rgba(255,255,255,0.06);background:transparent;color:var(--text);outline:none}
  .row{display:flex;gap:8px;align-items:center}
  .btn{padding:10px 14px;border-radius:12px;border:none;cursor:pointer;font-weight:600}
  .btn-start{background:linear-gradient(90deg,#00ff9d,#00d4ff);color:#001}
  .btn-stop{background:linear-gradient(90deg,#ff5c7c,#ff914d);color:#fff}
  .status-pill{display:inline-block;padding:6px 10px;border-radius:999px;font-weight:700;margin-left:8px}
  .console{height:58vh;background:rgba(0,0,0,0.14);border-radius:12px;padding:12px;overflow:auto;font-family:monospace;font-size:13px;line-height:1.4;border:1px solid rgba(255,255,255,0.03)}
  .small{font-size:12px;opacity:0.85}
  .topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
  .controls{display:flex;gap:8px}
  .predict{background:linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));padding:10px;border-radius:10px}
  .pulse{width:12px;height:12px;border-radius:50%;display:inline-block;box-shadow:0 0 10px rgba(255,255,255,0.06);animation:beat 1.2s infinite}
  @keyframes beat {0%{transform:scale(1)}50%{transform:scale(1.25)}100%{transform:scale(1)}}
  .footer-note{opacity:0.7;font-size:12px;margin-top:8px}
  .file-input{padding:8px}
  .switch{display:inline-flex;align-items:center;gap:6px}
  .token-list{max-height:120px;overflow:auto;padding:8px;border-radius:8px;border:1px dashed rgba(255,255,255,0.04);margin-top:8px}
  .accent-box{background:linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));padding:10px;border-radius:10px}
  .night{filter:brightness(0.9) saturate(0.7)}
  .locked{opacity:0.6}
  /* neon border */
  .neon-border{box-shadow:0 0 30px rgba(138,43,226,0.12), inset 0 0 20px rgba(255,0,127,0.04)}
  /* responsive */
  @media (max-width:900px){.wrap{grid-template-columns:1fr;padding:16px;grid-auto-rows:auto;height:auto}}
</style>
</head>
<body>
<div class="wrap">
  <!-- LEFT PANEL: Controls -->
  <div class="panel neon-border">
    <div class="topbar">
      <div>
        <h1>CONVO'X-2 — DEMO</h1>
        <p class="lead">Futuristic bot panel (simulation). All sending simulated — safe to run locally.</p>
      </div>
      <div class="small">
        <span id="botPulse" class="pulse" style="background:linear-gradient(90deg,#ff66b3,#b388ff)"></span>
      </div>
    </div>

    <form id="configForm">
      <label>CONVO / Thread ID</label>
      <input type="text" id="threadId" placeholder="e.g., t_12345" required>

      <label>Hater/Prefix name</label>
      <input type="text" id="prefix" placeholder="Enter prefix text">

      <label>Speed (seconds)</label>
      <input type="number" id="speed" min="1" value="3">

      <label>Token file (.txt) — (simulated)</label>
      <input type="file" id="tokenFile" class="file-input" accept=".txt">

      <label>Messages file (.txt)</label>
      <input type="file" id="messagesFile" class="file-input" accept=".txt">

      <div style="display:flex;gap:8px;margin-top:10px">
        <button type="button" class="btn btn-start" id="startBtn">START</button>
        <button type="button" class="btn btn-stop" id="stopBtn" disabled>STOP</button>
        <button type="button" class="btn" id="pauseBtn" disabled>PAUSE</button>
      </div>

      <div style="margin-top:10px" class="small">
        <label><input type="checkbox" id="autoResume"> Auto-resume after refresh</label>
      </div>

      <div style="margin-top:12px" class="accent-box small">
        <strong>Smart Features (simulated)</strong>
        <ul>
          <li>Predictive message preview</li>
          <li>Token health monitor + auto-rotate</li>
          <li>Auto-resume & last index persistence</li>
          <li>Visual pulse synced to speed</li>
        </ul>
      </div>

      <div class="footer-note">Developer : HENRY — CONVO'X-2 DEMO</div>
    </form>
  </div>

  <!-- RIGHT PANEL: Console & Dashboard -->
  <div class="panel">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <div>
        <h2 style="margin:0">Live Console</h2>
        <div class="small">Simulated send logs & health dashboard</div>
      </div>
      <div>
        <label class="switch small"><input type="checkbox" id="nightToggle"> Night Vision</label>
      </div>
    </div>

    <div style="display:flex;gap:12px;margin-bottom:10px">
      <div style="flex:1">
        <div class="predict small" id="predictBox">Next message preview: <em id="predictText">—</em></div>
      </div>
      <div style="width:220px">
        <div style="display:flex;justify-content:space-between;align-items:center" class="small">
          <div>Bot Status: <span id="statusLabel" class="status-pill" style="background:rgba(0,255,157,0.12);color:#00ff9d">IDLE</span></div>
          <div class="small">Sent: <strong id="sentCount">0</strong></div>
        </div>
        <div style="margin-top:8px" class="token-list" id="tokenHealth">
          <div class="small">Tokens: <span id="tokenCount">0</span></div>
          <div id="tokenDetails"></div>
        </div>
      </div>
    </div>

    <div class="console" id="console"></div>

    <div style="display:flex;gap:8px;margin-top:12px;align-items:center">
      <button class="btn" id="clearLogs">Clear Logs</button>
      <button class="btn" id="downloadLogs">Download Logs</button>
      <div style="flex:1"></div>
      <div class="small">Live time: <span id="liveTime">--:--:--</span></div>
    </div>
  </div>
</div>

<!-- audio -->
<audio id="pingAudio">
  <source src="data:audio/ogg;base64,T2dnUwACAAAAAAAAAABVD...==" type="audio/ogg">
  <!-- Base64 placeholder — browsers accept an empty src; we will play beep via oscillator in JS if needed -->
</audio>

<script>
/* ---------- Utilities ---------- */
function el(id){return document.getElementById(id)}
function logConsole(s, cls='') {
  const c = el('console')
  const p = document.createElement('div')
  p.innerText = '[' + new Date().toLocaleTimeString() + '] ' + s
  if(cls) p.className = cls
  c.appendChild(p)
  c.scrollTop = c.scrollHeight
}

/* ---------- State ---------- */
let jobId = null
let evt = null
let sentCount = 0
let running = false
let paused = false
let tokens = []
let messages = []
let currentIndex = 0
let speed = 3
let autoResume = false

/* ---------- Local persistence ---------- */
function saveState() {
  if(!jobId) return
  const st = {jobId, currentIndex, tokensCount: tokens.length, messagesCount: messages.length}
  localStorage.setItem('convox2_state', JSON.stringify(st))
}
function loadState() {
  try{
    const st = JSON.parse(localStorage.getItem('convox2_state') || 'null')
    if(st && st.jobId) {
      // allow resume
      return st
    }
  }catch(e){}
  return null
}

/* ---------- File reading ---------- */
function readFileAsLines(file, cb){
  if(!file){cb([]);return}
  const reader = new FileReader()
  reader.onload = e => {
    const txt = e.target.result.replace(/\\r/g,'').trim()
    const lines = txt.split('\\n').map(s=>s.trim()).filter(s=>s)
    cb(lines)
  }
  reader.readAsText(file)
}

/* ---------- Start/Stop controls ---------- */
el('startBtn').onclick = async () => {
  if(running) return
  // read config
  const threadId = el('threadId').value || 't_demo'
  const prefix = el('prefix').value || ''
  speed = Number(el('speed').value) || 3
  autoResume = el('autoResume').checked

  readFileAsLines(el('tokenFile').files[0], (tokLines) => {
    tokens = tokLines.length ? tokLines : ['demo-token-1','demo-token-2','demo-token-3']
    readFileAsLines(el('messagesFile').files[0], (msgLines) => {
      messages = msgLines.length ? msgLines : ['Hello world','This is a demo message','CONVO X-2 test']
      // start simulated job
      fetch('/start', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({threadId, prefix, speed, tokensCount: tokens.length, messagesCount: messages.length, resumeIndex: (autoResume? (loadState()? loadState().currentIndex:0):0)})
      }).then(r=>r.json()).then(data=>{
        jobId = data.job_id
        // register client-side state
        currentIndex = data.start_index || 0
        el('statusLabel').innerText = 'RUNNING'
        el('statusLabel').style.background = 'rgba(0,255,157,0.12)'
        el('statusLabel').style.color = '#00ff9d'
        el('startBtn').disabled = true
        el('stopBtn').disabled = false
        el('pauseBtn').disabled = false
        running = true
        el('predictText').innerText = prefix + ' ' + messages[currentIndex % messages.length]
        // open SSE stream
        startSSE(jobId)
        // animate pulse speed
        animatePulse(speed)
      })
    })
  })
}

el('stopBtn').onclick = () => {
  if(!running) return
  fetch('/stop', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({job_id:jobId})})
  cleanup()
  logConsole('User requested STOP. Job stopped locally.')
}

el('pauseBtn').onclick = () => {
  if(!running) return
  paused = !paused
  fetch('/pause', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({job_id:jobId, pause:paused})})
  el('pauseBtn').innerText = paused? 'RESUME':'PAUSE'
  logConsole(paused? 'Paused by user.' : 'Resumed by user.')
}

/* ---------- SSE for logs ---------- */
function startSSE(jid){
  if(evt) evt.close()
  evt = new EventSource('/stream?job_id=' + encodeURIComponent(jid))
  evt.onmessage = e => {
    try{
      const payload = JSON.parse(e.data)
      if(payload.type === 'log') {
        logConsole(payload.msg)
      } else if(payload.type === 'status') {
        el('sentCount').innerText = payload.sent || '0'
        el('tokenCount').innerText = payload.tokens || '0'
        // token details
        if(payload.token_details_html) el('tokenDetails').innerHTML = payload.token_details_html
      } else if(payload.type === 'predict') {
        el('predictText').innerText = payload.text
      }
      // auto-play beep for success lines
      if(payload.beep) playClick()
      // save index for auto-resume
      if(payload.current_index !== undefined) {
        currentIndex = payload.current_index
        saveState()
      }
    }catch(err){ console.error(err) }
  }
  evt.onerror = (err) => {
    console.warn('SSE error', err)
  }
}

/* ---------- Visuals ---------- */
function animatePulse(s){
  const p = el('botPulse')
  p.style.animationDuration = Math.max(0.4, s/2) + 's'
  p.style.display = 'inline-block'
}

/* ---------- Console helpers ---------- */
el('clearLogs').onclick = ()=>{el('console').innerHTML='';}
el('downloadLogs').onclick = ()=>{
  const txt = Array.from(el('console').children).map(d=>d.innerText).join('\\n')
  const blob = new Blob([txt], {type:'text/plain'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href=url; a.download='convox2_logs.txt'; a.click(); URL.revokeObjectURL(url)
}

/* ---------- Small audio using WebAudio API for short beep ---------- */
function playClick(){
  try{
    const ctx = new (window.AudioContext||window.webkitAudioContext)()
    const o = ctx.createOscillator(); const g = ctx.createGain()
    o.type = 'sine'; o.frequency.value = 1000
    g.gain.value = 0.02
    o.connect(g); g.connect(ctx.destination)
    o.start(); setTimeout(()=>{ o.stop(); ctx.close() }, 100)
  }catch(e){}
}

/* ---------- Night toggle ---------- */
el('nightToggle').onchange = (e) => {
  document.body.classList.toggle('night', e.target.checked)
}

/* ---------- Keep live time ---------- */
setInterval(()=>{ el('liveTime').innerText = new Date().toLocaleTimeString() }, 1000)

/* ---------- Cleanup ---------- */
function cleanup(){
  if(evt) { evt.close(); evt = null }
  el('startBtn').disabled = false
  el('stopBtn').disabled = true
  el('pauseBtn').disabled = true
  el('statusLabel').innerText = 'IDLE'
  el('statusLabel').style.background = 'rgba(255,255,255,0.02)'
  el('statusLabel').style.color = '#f8f8ff'
  running = false
  paused = false
  jobId = null
}

/* ---------- Load previous state if autoResume true (UI-level) ---------- */
window.addEventListener('load', ()=>{
  const st = loadState()
  if(st) {
    logConsole('Found saved session. You may choose Auto-resume before START to resume from index: ' + st.currentIndex)
  }
})
</script>
</body>
</html>
"""

# -------------------------
# Background simulated worker
# -------------------------
def worker(job_id, config):
    q = log_queues[job_id]
    tokens_count = config.get('tokens_count', 3)
    messages_count = config.get('messages_count', 3)
    speed = config.get('speed', 3)
    prefix = config.get('prefix', '')
    start_index = config.get('start_index', 0)
    running = True
    paused = False
    state = {
        'current_index': start_index,
        'sent': 0,
        'tokens': [{'token': f'demo-token-{i+1}', 'errors':0} for i in range(tokens_count)]
    }
    # store job state
    jobs[job_id]['state'] = state

    def log(msg, beep=False):
        payload = {'type':'log', 'msg':msg, 'beep':beep}
        q.put(json.dumps(payload))

    def status_update():
        token_html = ''
        for t in state['tokens']:
            token_html += f"<div class='small'>{t['token']} — errors: {t['errors']}</div>"
        payload = {'type':'status', 'sent': state['sent'], 'tokens': len(state['tokens']), 'token_details_html': token_html, 'current_index': state['current_index']}
        q.put(json.dumps(payload))

    log(f"[SYSTEM] Job started (demo). Simulating {messages_count} messages with {tokens_count} tokens. Speed: {speed}s")
    status_update()
    try:
        while jobs[job_id]['running']:
            # poll pause flag
            if jobs[job_id].get('paused'):
                if not paused:
                    paused = True
                    log("[SYSTEM] Worker paused by user.")
                time.sleep(0.5)
                continue
            else:
                if paused:
                    paused = False
                    log("[SYSTEM] Worker resumed by user.")
            # simulate send
            idx = state['current_index'] % messages_count
            token_idx = (state['current_index']) % len(state['tokens'])
            token_info = state['tokens'][token_idx]
            message_text = f"{prefix} {config.get('messages_template', f'MSG_{idx+1}')}"
            # Predictive notice
            q.put(json.dumps({'type':'predict', 'text': message_text}))
            # Simulate network and possible failure
            success = random.choices([True, False], weights=[85,15])[0]  # 85% success rate simulated
            if success:
                state['sent'] += 1
                log(f"[+] Simulated SEND OK | idx={state['current_index']} | token={token_info['token']} | msg=\"{message_text}\"", beep=True)
            else:
                token_info['errors'] += 1
                log(f"[x] Simulated SEND FAIL | idx={state['current_index']} | token={token_info['token']} | msg=\"{message_text}\"")
                # If token accumulated errors, rotate it out (demo)
                if token_info['errors'] >= 3:
                    log(f"[SYSTEM] Token {token_info['token']} flagged (errors>=3). Auto-rotating out.")
                    state['tokens'].remove(token_info)
                    if not state['tokens']:
                        log("[SYSTEM] All tokens exhausted. Stopping job.")
                        jobs[job_id]['running'] = False
                        break
            # advance index & status
            state['current_index'] += 1
            jobs[job_id]['state'] = state
            status_update()
            # heartbeat sleep, but sleep in small increments to allow responsive stop
            for i in range(int(max(1, speed*10))):
                if not jobs[job_id]['running'] or jobs[job_id].get('paused'):
                    break
                time.sleep(0.1)
    except Exception as e:
        log(f"[ERROR] Worker exception: {str(e)}")
    finally:
        log("[SYSTEM] Worker stopped.")
        status_update()
        jobs[job_id]['running'] = False

# -------------------------
# Routes
# -------------------------
@app.route('/')
def index():
    return render_template_string(TEMPLATE)

@app.route('/start', methods=['POST'])
def start_job():
    data = request.get_json() or {}
    job_id = str(uuid.uuid4())
    # store job config (sanitized)
    cfg = {
        'thread_id': data.get('threadId','t_demo'),
        'prefix': data.get('prefix',''),
        'speed': max(1, int(data.get('speed',3))),
        'tokens_count': max(1, int(data.get('tokensCount',3))),
        'messages_count': max(1, int(data.get('messagesCount',3))),
        'messages_template': 'SIM_MESSAGE'
    }
    # resume index if any
    start_index = int(data.get('resumeIndex', 0))
    cfg['start_index'] = start_index

    # initialize job state
    jobs[job_id] = {'config': cfg, 'running': True, 'paused': False}
    q = queue.Queue()
    log_queues[job_id] = q
    # spawn worker
    t = threading.Thread(target=worker, args=(job_id, cfg), daemon=True)
    t.start()
    return jsonify({'ok': True, 'job_id': job_id, 'start_index': start_index})

@app.route('/stop', methods=['POST'])
def stop_job():
    data = request.get_json() or {}
    jid = data.get('job_id')
    if jid and jid in jobs:
        jobs[jid]['running'] = False
        return jsonify({'ok':True})
    return jsonify({'ok':False,'error':'job not found'}), 404

@app.route('/pause', methods=['POST'])
def pause_job():
    data = request.get_json() or {}
    jid = data.get('job_id')
    pause_flag = data.get('pause', False)
    if jid and jid in jobs:
        jobs[jid]['paused'] = bool(pause_flag)
        return jsonify({'ok':True})
    return jsonify({'ok':False,'error':'job not found'}), 404

@app.route('/stream')
def stream():
    # SSE stream for job logs
    jid = request.args.get('job_id')
    if not jid or jid not in log_queues:
        return "No such job", 404
    q = log_queues[jid]

    def event_stream():
        # yield initial state
        yield f"data: {json.dumps({'type':'log','msg':'[SYSTEM] Connected to live demo stream.'})}\\n\\n"
        while jobs.get(jid, {}).get('running') or not q.empty():
            try:
                item = q.get(timeout=1.0)
                yield f"data: {item}\\n\\n"
            except queue.Empty:
                # send occasional status ping to keep connection alive
                yield f"data: {json.dumps({'type':'log','msg':'[SYSTEM] heartbeat'})}\\n\\n"
        yield f"data: {json.dumps({'type':'log','msg':'[SYSTEM] Stream closed.'})}\\n\\n"
    return Response(event_stream(), mimetype="text/event-stream")

# -------------------------
# Utility endpoints (demo)
# -------------------------
@app.route('/status/<job_id>')
def status(job_id):
    if job_id not in jobs:
        return jsonify({'ok':False,'error':'job not found'}), 404
    return jsonify({'ok':True, 'job': jobs[job_id]})

# -------------------------
# Run app
# -------------------------
if __name__ == '__main__':
    print("CONVO'X-2 Demo starting at http://127.0.0.1:5000 — Simulation ONLY (no external sends).")
    app.run(host='0.0.0.0', port=5000, threaded=True)
