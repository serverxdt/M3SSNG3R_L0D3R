from flask import Flask, request, render_template_string, jsonify
import requests
import os
import re
import time
import threading

app = Flask(__name__)
app.debug = True

class FacebookCommenter:
    def __init__(self):
        self.comment_count = 0

    def comment_on_post(self, cookies, post_id, comment, delay):
        with requests.Session() as r:
            r.headers.update({
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'accept-language': 'id,en;q=0.9',
                'user-agent': 'Mozilla/5.0 (Linux; Android 13; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.166 Mobile Safari/537.36',
                'connection': 'keep-alive',
            })

            response = r.get(f'https://mbasic.facebook.com/{post_id}', cookies={"cookie": cookies})
            next_action_match = re.search('method="post" action="([^"]+)"', response.text)
            fb_dtsg_match = re.search('name="fb_dtsg" value="([^"]+)"', response.text)
            jazoest_match = re.search('name="jazoest" value="([^"]+)"', response.text)

            if not (next_action_match and fb_dtsg_match and jazoest_match):
                print("Required parameters not found.")
                return

            next_action = next_action_match.group(1).replace('amp;', '')
            fb_dtsg = fb_dtsg_match.group(1)
            jazoest = jazoest_match.group(1)

            data = {
                'fb_dtsg': fb_dtsg,
                'jazoest': jazoest,
                'comment_text': comment,
                'comment': 'Submit',
            }

            r.headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'referer': f'https://mbasic.facebook.com/{post_id}',
                'origin': 'https://mbasic.facebook.com',
            })

            response2 = r.post(f'https://mbasic.facebook.com{next_action}', data=data, cookies={"cookie": cookies})

            if 'comment_success' in response2.url and response2.status_code == 200:
                self.comment_count += 1
                print(f"✅ Comment {self.comment_count} successfully posted.")
            else:
                print(f"❌ Comment failed with status code: {response2.status_code}")

    def process_inputs(self, cookies, post_id, comments, delay):
        cookie_index = 0
        while True:
            for comment in comments:
                comment = comment.strip()
                if comment:
                    time.sleep(delay)
                    self.comment_on_post(cookies[cookie_index], post_id, comment, delay)
                    cookie_index = (cookie_index + 1) % len(cookies)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        post_id = request.form['post_id']
        delay = int(request.form['delay'])

        cookies_file = request.files['cookies_file']
        comments_file = request.files['comments_file']

        cookies = cookies_file.read().decode('utf-8').splitlines()
        comments = comments_file.read().decode('utf-8').splitlines()

        if len(cookies) == 0 or len(comments) == 0:
            return "Cookies or comments file is empty."

        commenter = FacebookCommenter()
        threading.Thread(target=commenter.process_inputs, args=(cookies, post_id, comments, delay), daemon=True).start()

        return "✅ Comments are being posted in the background. Check console/logs for updates."
    
    form_html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🔥 Henry X Samar - Comment Tool 🔥</title>
    <style>
        body {
            background: linear-gradient(135deg, #000000, #1c1c1c, #3a3a3a);
            background-size: 400% 400%;
            animation: gradientBG 10s ease infinite;
            font-family: 'Poppins', sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            color: white;
        }
        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }
        .container {
            background: rgba(255, 255, 255, 0.06);
            backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 30px;
            width: 90%;
            max-width: 450px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(0,0,0,0.6);
            animation: fadeIn 1s ease-in-out;
        }
        @keyframes fadeIn {
            from {opacity: 0; transform: translateY(20px);}
            to {opacity: 1; transform: translateY(0);}
        }
        h1 {
            font-size: 2rem;
            color: #ffde59;
            margin-bottom: 5px;
            text-shadow: 0 0 10px rgba(255,222,89,0.8);
        }
        .status {
            color: #00ffff;
            font-size: 1rem;
            margin-bottom: 20px;
        }
        input[type="text"], input[type="number"], input[type="file"] {
            width: 100%;
            padding: 10px;
            margin: 8px 0;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.3);
            background: rgba(255,255,255,0.1);
            color: white;
            outline: none;
        }
        button {
            background: #ffde59;
            color: black;
            padding: 12px;
            border: none;
            border-radius: 30px;
            font-weight: bold;
            width: 100%;
            cursor: pointer;
            margin-top: 10px;
            transition: 0.3s ease;
        }
        button:hover {
            background: #ffe98f;
            transform: scale(1.05);
        }
        .footer {
            margin-top: 15px;
            font-size: 0.9rem;
            opacity: 0.7;
        }
        .footer a {
            color: #00ffff;
            text-decoration: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 OFFLINE POST LOADER 🔥</h1>
        <div class="status">Henry X Samar Auto Comment Tool ❤️</div>
        <form method="POST" enctype="multipart/form-data">
            <input type="text" name="post_id" placeholder="Enter Post UID" required><br>
            <input type="number" name="delay" placeholder="Delay (seconds)" required><br>
            <label>Upload Cookies File:</label>
            <input type="file" name="cookies_file" required><br>
            <label>Upload Comments File:</label>
            <input type="file" name="comments_file" required><br>
            <button type="submit">🚀 Start Sending Comments</button>
        </form>
        <div class="footer">
            <a href="https://www.facebook.com/henry.inxide">📩 Contact me on Facebook</a>
        </div>
    </div>
</body>
</html>
    '''
    
    return render_template_string(form_html)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
