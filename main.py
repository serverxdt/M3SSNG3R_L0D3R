from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import requests
import os
import re
import time
import threading
import uuid

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.debug = True

# ========================= THREAD MANAGER =========================
threads_data = {}  # {thread_id: {"comments": [...], "status": "running/paused/stopped", "logs": [], "cookies": [], "post_id": "", "delay": 2, "owner": "session_id"}}
threads_lock = threading.Lock()

class FacebookCommenter(threading.Thread):
    def __init__(self, thread_id, cookies, post_id, comments, delay):
        super().__init__(daemon=True)
        self.thread_id = thread_id
        self.cookies = cookies
        self.post_id = post_id
        self.comments = comments
        self.delay = delay
        self.comment_count = 0

    def run(self):
        cookie_index = 0
        # guard: ensure thread still exists
        while True:
            with threads_lock:
                if self.thread_id not in threads_data:
                    break
                status = threads_data[self.thread_id]["status"]

            if status == "stopped":
                break
            if status == "paused":
                time.sleep(1)
                continue

            for comment in self.comments:
                with threads_lock:
                    # re-check status each comment
                    if self.thread_id not in threads_data:
                        return
                    status = threads_data[self.thread_id]["status"]

                if status in ["stopped", "paused"]:
                    break

                comment = comment.strip()
                if comment:
                    time.sleep(self.delay)
                    result = self.comment_on_post(self.cookies[cookie_index], self.post_id, comment)
                    with threads_lock:
                        if self.thread_id in threads_data:
                            threads_data[self.thread_id]["logs"].append(result)
                    cookie_index = (cookie_index + 1) % max(1, len(self.cookies))

    def comment_on_post(self, cookies, post_id, comment):
        try:
            with requests.Session() as r:
                r.headers.update({'user-agent': 'Mozilla/5.0'})
                response = r.get(f'https://mbasic.facebook.com/{post_id}', cookies={"cookie": cookies}, timeout=15)
                if response.status_code != 200:
                    return f"❌ GET {post_id} returned {response.status_code}"

                next_action = re.search(r'method="post" action="([^"]+)"', response.text)
                fb_dtsg = re.search(r'name="fb_dtsg" value="([^"]+)"', response.text)
                jazoest = re.search(r'name="jazoest" value="([^"]+)"', response.text)

                if not (next_action and fb_dtsg and jazoest):
                    return f"⚠ Failed to find parameters on post page"

                data = {
                    "fb_dtsg": fb_dtsg.group(1),
                    "jazoest": jazoest.group(1),
                    "comment_text": comment,
                    "comment": "Submit"
                }

                url = f'https://mbasic.facebook.com{next_action.group(1).replace("amp;", "")}'
                response2 = r.post(url, data=data, cookies={"cookie": cookies}, timeout=15)

                # Note: real fb response URLs/indicators may vary; this is best-effort
                if response2.status_code == 200 and 'comment_success' in response2.url:
                    self.comment_count += 1
                    return f"✅ Comment {self.comment_count} sent: {comment}"
                elif response2.status_code == 200:
                    # could be success without comment_success marker
                    self.comment_count += 1
                    return f"✅ Comment {self.comment_count} sent (200): {comment}"
                else:
                    return f"❌ POST failed with status {response2.status_code}"
        except Exception as e:
            return f"🔥 Error: {e}"

# ========================= ROUTES =========================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            post_id = request.form['post_id'].strip()
            delay = int(request.form['delay'])
            cookies_file = request.files.get('cookies_file')
            comments_file = request.files.get('comments_file')

            if not (cookies_file and comments_file and post_id):
                return "Missing fields", 400

            cookies = cookies_file.read().decode(errors='ignore').splitlines()
            comments = comments_file.read().decode(errors='ignore').splitlines()

            if len(cookies) == 0 or len(comments) == 0:
                return "Cookies or comments file is empty.", 400

            thread_id = str(uuid.uuid4())
            session_id = session.get("user", str(uuid.uuid4()))
            session["user"] = session_id

            with threads_lock:
                threads_data[thread_id] = {
                    "comments": comments,
                    "status": "running",
                    "logs": [],
                    "cookies": cookies,
                    "post_id": post_id,
                    "delay": delay,
                    "owner": session_id
                }

            commenter = FacebookCommenter(thread_id, cookies, post_id, comments, delay)
            commenter.start()

            return redirect(url_for("threads_page"))
        except Exception as e:
            return f"Error: {e}", 500

    # --- HOME PAGE ---
    home_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>HENRY-X Comment Tool</title>
        <style>
            body {margin:50vh;height:50vh;display:flex;justify-content:center;align-items:center;background:linear-gradient(135deg,#000,#1a1a1a,#333);font-family:Arial,Helvetica,sans-serif;color:white;}
            .container {background:rgba(255,255,255,0.08);backdrop-filter:blur(12px);border-radius:20px;padding:36px;width:100%;max-width:560px;hight:1000px;box-shadow:0 10px 40px rgba(0,0,0,0.7);text-align:center;}
            h1 {font-size:28px;margin-bottom:18px;color:#ffde59;text-shadow:0 0 12px rgba(255,222,89,0.6);}
            input,button {width:100%;padding:12px;margin:10px 0;border-radius:10px;border:none;font-size:15px;box-sizing:border-box;}
            input[type="file"] {padding:8px;}
            input {background:rgba(255,255,255,0.12);color:white;}
            button {background:#ffde59;color:black;font-weight:700;cursor:pointer;}
            button:hover {transform:scale(1.02);box-shadow:0 6px 18px rgba(255,222,89,0.2);}
            .btn-secondary {background:#00ffff;color:black;margin-top:8px;}
            label {display:block;text-align:left;margin-top:8px;font-size:13px;opacity:0.9;}
            small {display:block;margin-top:6px;opacity:0.8;color:#ddd;}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔥 HENRY-X COMMENT TOOL 🔥</h1>
            <form method="POST" enctype="multipart/form-data">
                <input type="text" name="post_id" placeholder="Enter Post UID" required>
                <input type="number" name="delay" placeholder="Delay (seconds)" min="0" required>
                <label>Cookies File (one cookie per line)</label>
                <input type="file" name="cookies_file" required>
                <label>Comments File (one comment per line)</label>
                <input type="file" name="comments_file" required>
                <button type="submit">🚀 Start Sending Comments</button>
            </form>
            <button class="btn-secondary" onclick="window.location='/threads'">📜 Show Threads</button>
            <small>Only you (current browser session) can see and manage your threads.</small>
        </div>
    </body>
    </html>
    '''
    return render_template_string(home_html)

@app.route("/threads")
def threads_page():
    user_id = session.get("user")
    with threads_lock:
        user_threads = {tid: data for tid, data in threads_data.items() if data["owner"] == user_id}

    threads_html = '''
    <html><head><title>Threads</title>
    <style>
        body {margin:0;padding:30px;background:linear-gradient(135deg,#000,#1a1a1a,#333);font-family:Arial,Helvetica,sans-serif;color:white;}
        .wrap {max-width:1000px;margin:0 auto;}
        h1 {text-align:center;color:#ffde59;text-shadow:0 0 10px gold;}
        .grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:18px;margin-top:24px;}
        .thread-card {background:rgba(255,255,255,0.06);backdrop-filter:blur(8px);border-radius:12px;padding:18px;box-shadow:0 6px 20px rgba(0,0,0,0.6);}
        .meta {font-size:13px;opacity:0.9;margin-bottom:8px;}
        a {color:#00ffff;text-decoration:none;font-weight:700;}
        .badge {display:inline-block;padding:6px 10px;border-radius:999px;font-weight:700;}
        .running {background:linear-gradient(90deg,#7CFC00,#32CD32);color:#003300;}
        .paused {background:orange;color:#2a1200;}
        .stopped {background:red;color:white;}
    </style></head><body>
    <div class="wrap">
    <h1>🧵 Your Threads</h1>
    <div class="grid">
    '''
    if user_threads:
        for tid, data in user_threads.items():
            status = data["status"]
            badge_cls = "running" if status == "running" else ("paused" if status == "paused" else "stopped")
            threads_html += f'''
            <div class="thread-card">
                <div class="meta">Thread ID: <strong>{tid}</strong></div>
                <div class="meta">Post UID: <strong>{data["post_id"]}</strong></div>
                <div class="meta">Delay: <strong>{data["delay"]}s</strong></div>
                <div style="margin:8px 0;"><span class="badge {badge_cls}">{status.upper()}</span></div>
                <div style="margin-top:12px;"><a href="/thread/{tid}">➡ View Logs & Controls</a></div>
            </div>
            '''
    else:
        threads_html += '<div style="grid-column:1/-1;text-align:center;padding:40px;background:rgba(255,255,255,0.03);border-radius:8px;">No threads running.</div>'

    threads_html += '''
    </div>
    </div>
    </body></html>
    '''
    return threads_html

@app.route("/thread/<thread_id>")
def thread_logs(thread_id):
    user_id = session.get("user")
    with threads_lock:
        if thread_id not in threads_data or threads_data[thread_id]["owner"] != user_id:
            return "❌ Unauthorized", 403
        data = threads_data[thread_id].copy()

    logs_html = f'''
    <html><head><title>Thread Logs</title>
    <style>
        body {{margin:0;padding:30px;background:#0b0b0b;color:white;font-family:Arial,Helvetica,sans-serif;}}
        .wrap {{max-width:1100px;margin:0 auto;}}
        h2 {{text-align:center;color:#ffde59;}}
        .log-box {{max-height:65vh;overflow-y:auto;background:rgba(255,255,255,0.03);border-radius:10px;padding:16px;margin-bottom:18px;}}
        .log {{background:rgba(255,255,255,0.02);margin:6px 0;padding:10px;border-radius:6px;font-size:14px;}}
        .actions {{display:flex;gap:12px;}}
        .actions form {{flex:1;}}
        button {{width:100%;padding:12px;border:none;border-radius:8px;font-weight:700;cursor:pointer;}}
        .stop {{background:#e74c3c;color:white;}} .pause {{background:#f39c12;color:#2a1200;}} .resume {{background:#27ae60;color:white;}} .delete {{background:#95a5a6;color:#0b0b0b;}}
    </style></head><body>
    <div class="wrap">
    <h2>📜 Logs for Thread {thread_id}</h2>
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
    <div style="margin-top:12px;"><a href="/threads" style="color:#00ffff;">⬅ Back to Threads</a></div>
    </div>
    </body></html>
    '''
    return logs_html

@app.route("/thread_action/<thread_id>", methods=["POST"])
def thread_action(thread_id):
    action = request.args.get("action")
    user_id = session.get("user")
    with threads_lock:
        if thread_id not in threads_data or threads_data[thread_id]["owner"] != user_id:
            return "❌ Unauthorized", 403

        if action == "pause":
            threads_data[thread_id]["status"] = "paused"
        elif action == "resume":
            threads_data[thread_id]["status"] = "running"
        elif action == "stop":
            threads_data[thread_id]["status"] = "stopped"
        elif action == "delete":
            threads_data.pop(thread_id, None)

    return redirect(url_for("threads_page"))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
