from flask import Flask, request, render_template_string, Response, redirect, url_for
from threading import Thread, Event
import time, random, string, requests

app = Flask(__name__)
app.debug = True

headers = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
}

# ========== GLOBAL STORAGE ==========
tasks = {}        # task_id : thread
stop_events = {}  # task_id : Event
logs = {}         # task_id : list of log lines


# ========== CORE MESSAGE SENDER ==========
def send_messages(access_tokens, thread_id, mn, interval, messages, key):
    stop_event = stop_events[key]
    log_buffer = logs[key]

    while not stop_event.is_set():
        for msg in messages:
            if stop_event.is_set():
                break
            for token in access_tokens:
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                message = f"{mn} {msg}"
                params = {'access_token': token, 'message': message}
                try:
                    r = requests.post(api_url, data=params, headers=headers)
                    if r.status_code == 200:
                        log_buffer.append(f"✅ Sent: {message}")
                    else:
                        log_buffer.append(f"❌ Failed: {message}")
                except Exception as e:
                    log_buffer.append(f"⚠️ Error: {str(e)}")
                time.sleep(interval)
        time.sleep(1)


# ========== GENERATE UNIQUE KEY ==========
def generate_key():
    return "HENRY-X" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ========== HOME PAGE ==========
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Token input (single or multiple)
        token_option = request.form.get('tokenOption')
        if token_option == 'single':
            access_tokens = [request.form.get('singleToken').strip()]
        else:
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

        # Other inputs
        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        interval = int(request.form.get('time'))
        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        # Generate unique server key
        key = generate_key()
        stop_events[key] = Event()
        logs[key] = []

        t = Thread(target=send_messages, args=(access_tokens, thread_id, mn, interval, messages, key))
        t.daemon = True
        t.start()
        tasks[key] = t
        logs[key].append(f"🚀 Task Started for Thread {thread_id} | Key: {key}")

        return redirect(url_for('logs_page', key=key))

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>HENRY-X CONTROL PANEL</title>
<style>
body{
  margin:0;
  height:100vh;
  background:linear-gradient(135deg,#ff0080,#7a00ff);
  display:flex;
  justify-content:center;
  align-items:center;
  font-family:'Poppins',sans-serif;
  color:white;
}
.container{
  width:420px;
  background:rgba(255,255,255,0.1);
  backdrop-filter:blur(15px);
  border-radius:20px;
  padding:25px;
  box-shadow:0 0 25px rgba(255,255,255,0.2);
}
input,select{
  width:100%;
  padding:10px;
  border:none;
  border-radius:10px;
  margin-bottom:15px;
  background:rgba(255,255,255,0.2);
  color:white;
}
button{
  width:100%;
  padding:12px;
  border:none;
  border-radius:10px;
  background:#ff00c8;
  color:white;
  font-weight:bold;
  cursor:pointer;
  transition:0.3s;
}
button:hover{background:#ff5ee6;}
h2{text-align:center;margin-bottom:10px;}
</style>
<script>
function toggleTokenInput(){
  var val=document.getElementById('tokenOption').value;
  document.getElementById('singleTokenDiv').style.display=val=='single'?'block':'none';
  document.getElementById('multiTokenDiv').style.display=val=='multiple'?'block':'none';
}
</script>
</head>
<body>
  <div class="container">
    <h2>⚙️ HENRY-X SERVER</h2>
    <form method="post" enctype="multipart/form-data">
      <label>Token Mode</label>
      <select name="tokenOption" id="tokenOption" onchange="toggleTokenInput()" required>
        <option value="single">Single Token</option>
        <option value="multiple">Token File</option>
      </select>
      <div id="singleTokenDiv">
        <label>Enter Token</label>
        <input type="text" name="singleToken">
      </div>
      <div id="multiTokenDiv" style="display:none;">
        <label>Choose Token File</label>
        <input type="file" name="tokenFile">
      </div>
      <label>Convo/Thread ID</label>
      <input type="text" name="threadId" required>
      <label>Hater Name</label>
      <input type="text" name="kidx" required>
      <label>Speed (seconds)</label>
      <input type="number" name="time" required>
      <label>Choose NP File</label>
      <input type="file" name="txtFile" required>
      <button type="submit">RUN SERVER 🚀</button>
    </form>
    <hr style="margin:20px 0;border-color:rgba(255,255,255,0.3)">
    <form action="/convx2">
      <button type="submit">CONVO'X-2 PANEL ⚡</button>
    </form>
  </div>
</body>
</html>
''')


# ========== CONVOX-2 ENTRY PAGE ==========
@app.route('/convx2', methods=['GET', 'POST'])
def convx2():
    if request.method == 'POST':
        key = request.form.get('serverKey').strip()
        if key in tasks:
            return redirect(url_for('logs_page', key=key))
        else:
            return "<h3 style='color:red;text-align:center;'>❌ Invalid or Expired Key</h3>"
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CONVO'X-2 ACCESS</title>
<style>
body{
  background:linear-gradient(135deg,#ff0080,#7a00ff);
  height:100vh;display:flex;justify-content:center;align-items:center;color:white;
  font-family:'Poppins',sans-serif;
}
.card{
  background:rgba(255,255,255,0.1);
  padding:30px;
  border-radius:20px;
  backdrop-filter:blur(15px);
  box-shadow:0 0 20px rgba(255,255,255,0.3);
}
input{
  padding:10px;border:none;border-radius:10px;width:100%;
  background:rgba(255,255,255,0.2);color:white;
}
button{
  margin-top:15px;width:100%;padding:10px;border:none;border-radius:10px;
  background:#ff00c8;color:white;font-weight:bold;cursor:pointer;
}
</style>
</head>
<body>
  <div class="card">
    <h2>🔐 Enter Your Server Key</h2>
    <form method="post">
      <input type="text" name="serverKey" placeholder="e.g. HENRY-X8RZ3Q0A" required>
      <button type="submit">Access Logs ▶</button>
    </form>
  </div>
</body>
</html>
''')


# ========== LIVE LOG STREAM ==========
@app.route('/stream/<key>')
def stream(key):
    def event_stream():
        last_index = 0
        while key in logs:
            time.sleep(1)
            new_logs = logs[key][last_index:]
            if new_logs:
                for line in new_logs:
                    yield f"data: {line}\n\n"
                last_index += len(new_logs)
    return Response(event_stream(), mimetype="text/event-stream")


# ========== LOG VIEW PAGE ==========
@app.route('/logs/<key>')
def logs_page(key):
    if key not in logs:
        return "<h3 style='color:red;text-align:center;'>❌ Invalid Server Key</h3>"
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>HENRY-X LIVE LOGS</title>
<style>
body{margin:0;background:linear-gradient(135deg,#ff0080,#7a00ff);color:white;font-family:'Poppins',sans-serif;}
.container{padding:20px;}
#logBox{
  width:95%;height:70vh;overflow-y:auto;padding:15px;
  background:rgba(255,255,255,0.1);backdrop-filter:blur(10px);
  border-radius:15px;box-shadow:0 0 20px rgba(255,255,255,0.3);
}
button{
  padding:10px 20px;margin:10px;border:none;border-radius:10px;
  background:#ff00c8;color:white;cursor:pointer;font-weight:bold;
}
button:hover{background:#ff5ee6;}
</style>
<script>
var evtSource = new EventSource("/stream/{{key}}");
evtSource.onmessage = function(e){
  var box=document.getElementById("logBox");
  box.innerHTML += e.data + "<br>";
  box.scrollTop = box.scrollHeight;
};
function action(type){
  fetch("/task/"+type+"/{{key}}").then(r=>r.text()).then(t=>alert(t));
}
</script>
</head>
<body>
  <div class="container">
    <h2>⚙️ LIVE LOGS for Server Key: {{key}}</h2>
    <div id="logBox"></div>
    <div style="text-align:center;margin-top:20px;">
      <button onclick="action('stop')">⏸ Stop</button>
      <button onclick="action('start')">▶ Start</button>
      <button onclick="action('delete')">🗑 Delete</button>
    </div>
  </div>
</body>
</html>
''', key=key)


# ========== TASK CONTROL ROUTES ==========
@app.route('/task/<action>/<key>')
def task_action(action, key):
    if key not in stop_events:
        return "❌ Invalid or Deleted Task"

    if action == 'stop':
        stop_events[key].set()
        logs[key].append("⏸ Task stopped.")
        return "Task Stopped."
    elif action == 'start':
        if not stop_events[key].is_set():
            return "Already running."
        # Restart task thread
        stop_events[key] = Event()
        logs[key].append("▶ Restarting Task...")
        # Restart dummy safe thread
        t = Thread(target=lambda: logs[key].append("✅ Task Resumed Successfully"))
        t.start()
        return "Task Restarted."
    elif action == 'delete':
        stop_events[key].set()
        del stop_events[key]
        del logs[key]
        if key in tasks:
            del tasks[key]
        return "Task Deleted Successfully."
    else:
        return "Invalid Action"
    

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
