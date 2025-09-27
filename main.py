from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for import requests import os import re import time import threading import uuid

app = Flask(name) app.secret_key = "super_secret_key" app.debug = True

=================== THREAD DATA ===================

threads_data = {}  # {thread_id: {"logs": [], "status": "running"}}

class FacebookCommenter(threading.Thread): def init(self, thread_id, cookies, post_id, comments, delay): super().init(daemon=True) self.thread_id = thread_id self.cookies = cookies self.post_id = post_id self.comments = comments self.delay = delay self.comment_count = 0

def run(self):
    cookie_index = 0
    while threads_data.get(self.thread_id, {}).get("status") == "running":
        for comment in self.comments:
            if threads_data.get(self.thread_id, {}).get("status") != "running":
                break
            comment = comment.strip()
            if comment:
                time.sleep(self.delay)
                log = self.comment_on_post(self.cookies[cookie_index], self.post_id, comment)
                threads_data[self.thread_id]["logs"].append(log)
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
                return "⚠ Failed to get parameters"

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
            return f"❌ Failed with status {response2.status_code}"
    except Exception as e:
        return f"🔥 Error: {e}"

@app.route("/", methods=["GET", "POST"]) def index(): if request.method == "POST": post_id = request.form['post_id'] delay = int(request.form['delay']) cookies = request.files['cookies_file'].read().decode().splitlines() comments = request.files['comments_file'].read().decode().splitlines()

thread_id = str(uuid.uuid4())
    threads_data[thread_id] = {"logs": [], "status": "running"}

    commenter = FacebookCommenter(thread_id, cookies, post_id, comments, delay)
    commenter.start()

    return redirect(url_for("threads"))

form_html = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>🔥 Henry X Samar - Comment Tool 🔥</title>
    <style>
        body {background:linear-gradient(135deg,#000,#1c1c1c,#3a3a3a);display:flex;justify-content:center;align-items:center;height:100vh;margin:0;font-family:Poppins;color:white;}
        .container {background:rgba(255,255,255,0.06);backdrop-filter:blur(15px);border-radius:20px;padding:30px;width:90%;max-width:450px;text-align:center;box-shadow:0 8px 25px rgba(0,0,0,0.6);}
        h1 {color:#ffde59;margin-bottom:10px;}
        input,button {width:100%;padding:10px;margin:8px 0;border-radius:10px;border:none;}
        input {background:rgba(255,255,255,0.1);color:white;}
        button {background:#ffde59;color:black;font-weight:bold;cursor:pointer;}
        button:hover {transform:scale(1.05);}
        .btn-secondary {background:#00ffff;color:black;}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 OFFLINE POST LOADER 🔥</h1>
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
return render_template_string(form_html)

@app.route("/threads") def threads(): threads_html = ''' <html><head><title>Threads</title> <style> body {background:#111;color:white;font-family:Poppins;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;} .card {width:700px;max-height:80vh;overflow-y:auto;background:rgba(255,255,255,0.08);backdrop-filter:blur(10px);padding:20px;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.8);} .thread {background:rgba(255,255,255,0.1);padding:10px;margin:10px 0;border-radius:10px;} a {color:#00ffff;text-decoration:none;} </style></head><body> <div class="card"> <h2>🧵 Running Threads</h2> ''' if not threads_data: threads_html += "<p>No threads running.</p>" for tid, data in threads_data.items(): threads_html += f'<div class="thread"><a href="/thread/{tid}">🔗 {tid[:8]} - <span style="color:lime;">{data["status"]}</span></a></div>' threads_html += "</div></body></html>" return threads_html

@app.route("/thread/<thread_id>") def thread_logs(thread_id): if thread_id not in threads_data: return "❌ Invalid Thread"

data = threads_data[thread_id]
logs_html = '''
<html><head><title>Logs</title>
<style>
    body {background:#111;color:white;font-family:Poppins;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
    .card {width:700px;max-height:80vh;overflow-y:auto;background:rgba(255,255,255,0.08);backdrop-filter:blur(10px);padding:20px;border-radius:20px;box-shadow:0 8px 30px rgba(0,0,0,0.8);display:flex;flex-direction:column;}
    .log {background:rgba(255,255,255,0.1);padding:8px;margin:5px 0;border-radius:8px;}
    .stop-btn {margin-top:15px;background:red;color:white;padding:10px;border:none;border-radius:10px;font-weight:bold;align-self:center;width:50%;cursor:pointer;}
</style></head><body>
<div class="card">
<h2>📜 Logs for Thread {}</h2>
'''.format(thread_id[:8])

for log in data["logs"]:
    logs_html += f'<div class="log">{log}</div>'

logs_html += f'''<form method="POST" action="/stop_thread/{thread_id}"><button class="stop-btn">⏹ STOP</button></form>'''
logs_html += "</div></body></html>"
return logs_html

@app.route("/stop_thread/<thread_id>", methods=["POST"]) def stop_thread(thread_id): if thread_id in threads_data: threads_data[thread_id]["status"] = "stopped" return redirect(url_for("threads"))

if name == 'main': port = int(os.environ.get('PORT', 5000)) app.run(host='0.0.0.0', port=port, debug=True)

