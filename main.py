from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for import requests, os, re, time, threading, uuid

app = Flask(name) app.secret_key = "super_secret_key" app.debug = True

========================= THREAD MANAGER =========================

threads_data = {}

class FacebookCommenter(threading.Thread): def init(self, thread_id, cookies, post_id, comments, delay): super().init(daemon=True) self.thread_id = thread_id self.cookies = cookies self.post_id = post_id self.comments = comments self.delay = delay self.comment_count = 0

def run(self):
    cookie_index = 0
    while threads_data[self.thread_id]["status"] != "stopped":
        if threads_data[self.thread_id]["status"] == "paused":
            time.sleep(1)
            continue

        for comment in self.comments:
            if threads_data[self.thread_id]["status"] in ["stopped", "paused"]:
                break
            comment = comment.strip()
            if comment:
                time.sleep(self.delay)
                result = self.comment_on_post(self.cookies[cookie_index], self.post_id, comment)
                threads_data[self.thread_id]["logs"].append(result)
                cookie_index = (cookie_index + 1) % len(self.cookies)

def comment_on_post(self, cookies, post_id, comment):
    try:
        with requests.Session() as r:
            r.headers.update({'user-agent': 'Mozilla/5.0'})
            response = r.get(f'https://mbasic.facebook.com/{post_id}', cookies={"cookie": cookies})
            next_action = re.search('method="post" action="([^"]+)"', response.text)
            fb_dtsg = re.search('name="fb_dtsg" value="([^"]+)"', response.text)
            jazoest = re.search('name="jazoest" value="([^"]+)"', response.text)

            if not (next_action and fb_dtsg and jazoest):
                return f"⚠ Failed to find parameters"

            data = {
                "fb_dtsg": fb_dtsg.group(1),
                "jazoest": jazoest.group(1),
                "comment_text": comment,
                "comment": "Submit"
            }

            response2 = r.post(f'https://mbasic.facebook.com{next_action.group(1).replace("amp;", "")}', data=data, cookies={"cookie": cookies})
            if 'comment_success' in response2.url and response2.status_code == 200:
                self.comment_count += 1
                return f"✅ Comment {self.comment_count} sent: {comment}"
            else:
                return f"❌ Failed with status {response2.status_code}"
    except Exception as e:
        return f"🔥 Error: {e}"

@app.route("/", methods=["GET", "POST"]) def index(): if request.method == "POST": post_id = request.form['post_id'] delay = int(request.form['delay']) cookies = request.files['cookies_file'].read().decode().splitlines() comments = request.files['comments_file'].read().decode().splitlines()

thread_id = str(uuid.uuid4())
    session_id = session.get("user", str(uuid.uuid4()))
    session["user"] = session_id

    threads_data[thread_id] = {"comments": comments, "status": "running", "logs": [], "cookies": cookies,
                               "post_id": post_id, "delay": delay, "owner": session_id}

    commenter = FacebookCommenter(thread_id, cookies, post_id, comments, delay)
    commenter.start()

    return redirect(url_for("threads_page"))

home_html = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>HENRY-X Comment Tool</title>
    <style>
        body {margin:0;height:100vh;display:flex;justify-content:center;align-items:center;background:linear-gradient(135deg,#000,#1a1a1a,#333);font-family:Poppins;color:white;}
        .container {background:rgba(255,255,255,0.08);backdrop-filter:blur(15px);border-radius:25px;padding:40px;width:90%;max-width:500px;box-shadow:0 8px 30px rgba(0,0,0,0.8);text-align:center;}
        h1 {font-size:28px;margin-bottom:20px;color:#ffde59;text-shadow:0 0 15px gold;}
        input,button {width:100%;padding:12px;margin:12px 0;border-radius:12px;border:none;font-size:16px;}
        input {background:rgba(255,255,255,0.15);color:white;}
        button {background:#ffde59;color:black;font-weight:bold;cursor:pointer;transition:0.3s;}
        button:hover {transform:scale(1.05);box-shadow:0 0 15px #ffde59;}
        .btn-secondary {background:#00ffff;}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 HENRY-X COMMENT TOOL 🔥</h1>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="post_id" placeholder="Enter Post UID" required>
            <input type="number" name="delay" placeholder="Delay (seconds)" required>
            <input type="file" name="cookies_file" required>
            <input type="file" name="comments_file" required>
            <button type="submit">🚀 Start Sending Comments</button>
        </form>
        <button class="btn-secondary" onclick="window.location='/threads'">📜 Show Threads</button>
    </div>
</body>
</html>
'''
return render_template_string(home_html)

@app.route("/threads") def threads_page(): user_id = session.get("user") user_threads = {tid:data for tid,data in threads_data.items() if data["owner"] == user_id}

threads_html = '''
<html><head><title>Threads</title>
<style>
    body {margin:0;padding:30px;background:linear-gradient(135deg,#000,#1a1a1a,#333);font-family:Poppins;color:white;}
    .thread-card {background:rgba(255,255,255,0.08);backdrop-filter:blur(10px);border-radius:15px;padding:20px;margin:15px 0;box-shadow:0 4px 15px rgba(0,0,0,0.6);}
    a {color:#00ffff;text-decoration:none;font-weight:bold;}
</style></head><body>
<h1 style="text-align:center;color:#ffde59;text-shadow:0 0 10px gold;">🧵 Your Threads</h1>
'''
for tid,data in user_threads.items():
    threads_html += f'<div class="thread-card"><a href="/thread/{tid}">🔗 Thread {tid[:8]} - <span style="color:lime;">{data["status"].upper()}</span></a></div>'
if not user_threads:
    threads_html += "<p style='text-align:center;'>No threads running.</p>"
threads_html += "</body></html>"
return threads_html

@app.route("/thread/<thread_id>") def thread_logs(thread_id): user_id = session.get("user") if thread_id not in threads_data or threads_data[thread_id]["owner"] != user_id: return "❌ Unauthorized"

data = threads_data[thread_id]
logs_html = f'''
<html><head><title>Thread Logs</title>
<style>
    body {{margin:0;padding:30px;background:#111;color:white;font-family:Poppins;}}
    .log-box {{max-height:60vh;overflow-y:auto;background:rgba(255,255,255,0.08);border-radius:10px;padding:15px;margin-bottom:20px;}}
    .log {{background:rgba(255,255,255,0.05);margin:5px 0;padding:8px;border-radius:5px;}}
    .actions {{display:flex;gap:10px;}}
    button {{flex:1;padding:12px;border:none;border-radius:10px;font-weight:bold;cursor:pointer;}}
    .stop {{background:red;color:white;}}
    .pause {{background:orange;}}
    .resume {{background:green;color:white;}}
    .delete {{background:gray;color:white;}}
</style></head><body>
<h2 style="text-align:center;color:#ffde59;">📜 Logs for Thread {thread_id[:8]}</h2>
<div class="log-box">
'''
for log in data["logs"]:
    logs_html += f'<div class="log">{log}</div>'
logs_html += f'''
</div>
<div class="actions">
    <form method="POST" action="/thread_action/{thread_id}?action=pause"><button class="pause">⏸ Pause</button></form>
    <form method="POST" action="/thread_action/{thread_id}?action=resume"><button class="resume">▶ Resume</button></form>
    <form method="POST" action="/thread_action/{thread_id}?action=stop"><button class="stop">⏹ Stop</button></form>
    <form method="POST" action="/thread_action/{thread_id}?action=delete"><button class="delete">❌ Delete</button></form>
</div>
</body></html>
'''
return logs_html

@app.route("/thread_action/<thread_id>", methods=["POST"]) def thread_action(thread_id): action = request.args.get("action") user_id = session.get("user") if thread_id not in threads_data or threads_data[thread_id]["owner"] != user_id: return "❌ Unauthorized"

if action == "pause":
    threads_data[thread_id]["status"] = "paused"
elif action == "resume":
    threads_data[thread_id]["status"] = "running"
elif action == "stop":
    threads_data[thread_id]["status"] = "stopped"
elif action == "delete":
    threads_data.pop(thread_id, None)

return redirect(url_for("threads_page"))

if name == 'main': port = int(os.environ.get("PORT", 5000)) app.run(host='0.0.0.0', port=port, debug=True)

