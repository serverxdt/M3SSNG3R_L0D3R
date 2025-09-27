from flask import Flask, request, render_template_string, jsonify, session, redirect, url_for
import requests, os, re, time, threading, uuid

app = Flask(__name__)
app.secret_key = "super_secret_key"
app.debug = True

# ========================= THREAD MANAGER =========================
threads_data = {}  # {thread_id: {"comments": [...], "status": "running/paused/stopped", "logs": [], "cookies": [], "post_id": "", "delay": 2, "owner": "session_id"}}

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
        while threads_data[self.thread_id]["status"] != "stopped":
            if threads_data[self.thread_id]["status"] == "paused":
                time.sleep(1)
                continue

            for comment in self.comments:
                if threads_data[self.thread_id]["status"] == "stopped":
                    break
                if threads_data[self.thread_id]["status"] == "paused":
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

# ========================= ROUTES =========================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        post_id = request.form['post_id']
        delay = int(request.form['delay'])
        cookies = request.files['cookies_file'].read().decode().splitlines()
        comments = request.files['comments_file'].read().decode().splitlines()

        thread_id = str(uuid.uuid4())
        session_id = session.get("user", str(uuid.uuid4()))
        session["user"] = session_id

        threads_data[thread_id] = {"comments": comments, "status": "running", "logs": [], "cookies": cookies,
                                   "post_id": post_id, "delay": delay, "owner": session_id}

        commenter = FacebookCommenter(thread_id, cookies, post_id, comments, delay)
        commenter.start()

        return redirect(url_for("threads_page"))

    # --- HOME PAGE ---
    home_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>HENRY-X Comment Tool</title>
        <style>
            body {background: linear-gradient(135deg,#000,#222,#333);color:white;font-family:Poppins;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}
            .container {background:rgba(255,255,255,0.08);backdrop-filter:blur(10px);border-radius:20px;padding:30px;max-width:450px;width:90%;text-align:center;}
            h1 {color:#ffde59;text-shadow:0 0 10px gold;}
            input,button {width:100%;padding:10px;margin:10px 0;border-radius:10px;border:none;}
            button {background:#ffde59;color:black;font-weight:bold;cursor:pointer;}
            button:hover {transform:scale(1.05);}
            .btn-secondary {background:#00ffff;color:black;}
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

@app.route("/threads")
def threads_page():
    user_id = session.get("user")
    user_threads = {tid:data for tid,data in threads_data.items() if data["owner"] == user_id}

    threads_html = '''
    <html><head><title>Threads</title>
    <style>
        body {background:linear-gradient(135deg,#000,#222,#333);color:white;font-family:Poppins;padding:30px;}
        .thread {background:rgba(255,255,255,0.1);margin:10px 0;padding:15px;border-radius:10px;cursor:pointer;}
        .thread:hover {background:rgba(255,255,255,0.2);}
        a {color:#00ffff;text-decoration:none;}
    </style></head>
    <body><h1>🧵 Your Threads</h1>
    '''
    for tid,data in user_threads.items():
        threads_html += f'<div class="thread"><a href="/thread/{tid}">🔗 Thread {tid[:8]} - Status: {data["status"].upper()}</a></div>'
    if not user_threads:
        threads_html += "<p>No threads running.</p>"
    threads_html += "</body></html>"
    return threads_html

@app.route("/thread/<thread_id>")
def thread_logs(thread_id):
    user_id = session.get("user")
    if thread_id not in threads_data or threads_data[thread_id]["owner"] != user_id:
        return "❌ Unauthorized"

    data = threads_data[thread_id]
    logs_html = '''
    <html><head><title>Thread Logs</title>
    <style>
        body {background:#111;color:white;font-family:Poppins;padding:20px;}
        .log {background:rgba(255,255,255,0.05);margin:5px 0;padding:8px;border-radius:5px;}
        button {margin:5px;padding:8px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;}
        .stop {background:red;color:white;} .pause{background:orange;} .resume{background:green;} .delete{background:gray;}
    </style></head><body>
    <h2>📜 Logs for Thread {}</h2>
    '''.format(thread_id[:8])

    for log in data["logs"]:
        logs_html += f'<div class="log">{log}</div>'

    logs_html += f'''
    <form method="POST" action="/thread_action/{thread_id}?action=pause"><button class="pause">⏸ Pause</button></form>
    <form method="POST" action="/thread_action/{thread_id}?action=resume"><button class="resume">▶ Resume</button></form>
    <form method="POST" action="/thread_action/{thread_id}?action=stop"><button class="stop">⏹ Stop</button></form>
    <form method="POST" action="/thread_action/{thread_id}?action=delete"><button class="delete">❌ Delete</button></form>
    </body></html>
    '''
    return logs_html

@app.route("/thread_action/<thread_id>", methods=["POST"])
def thread_action(thread_id):
    action = request.args.get("action")
    user_id = session.get("user")
    if thread_id not in threads_data or threads_data[thread_id]["owner"] != user_id:
        return "❌ Unauthorized"

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
