import os
import uuid
import glob
import json
import subprocess
import shlex
import threading
from functools import wraps
from datetime import timedelta
import bcrypt
from flask import Flask, request, jsonify, send_file, render_template, session, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))
app.permanent_session_lifetime = timedelta(days=365)

import sys
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)
        ADMIN_PASSWORD_HASH = config.get("admin_password_hash", "").encode("utf-8")
        if not ADMIN_PASSWORD_HASH:
            raise ValueError("admin_password_hash is empty")
except FileNotFoundError:
    print("\n[ERROR] Configuration file missing!", file=sys.stderr)
    print("Please create a 'config.json' file in the root directory with your bcrypt password hash.", file=sys.stderr)
    print("Example:\n{\n  \"admin_password_hash\": \"$2y$10$...\"\n}\n", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] Failed to load configuration from 'config.json': {e}", file=sys.stderr)
    sys.exit(1)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

jobs = {}


def run_download(job_id, url, format_choice, format_id):
    job = jobs[job_id]
    out_template = os.path.join(DOWNLOAD_DIR, f"{job_id}.%(ext)s")

    cmd = ["yt-dlp", "--no-playlist", "-o", out_template]

    if format_choice == "audio":
        cmd += ["-x", "--audio-format", "mp3"]
    elif format_id:
        cmd += ["-S", "vcodec:h264,res,acodec:m4a", "-f", f"{format_id}+bestaudio/best", "--merge-output-format", "mp4"]
    else:
        cmd += ["-S", "vcodec:h264,res,acodec:m4a", "-f", "bestvideo+bestaudio/best", "--merge-output-format", "mp4"]

    cmd.append(url)

    try:
        print(f"Executing: {shlex.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            job["status"] = "error"
            job["error"] = result.stderr.strip().split("\n")[-1]
            return

        files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{job_id}.*"))
        if not files:
            job["status"] = "error"
            job["error"] = "Download completed but no file was found"
            return

        if format_choice == "audio":
            target = [f for f in files if f.endswith(".mp3")]
            chosen = target[0] if target else files[0]
        else:
            target = [f for f in files if f.endswith(".mp4")]
            chosen = target[0] if target else files[0]

        for f in files:
            if f != chosen:
                try:
                    os.remove(f)
                except OSError:
                    pass

        if format_choice != "audio":
            try:
                vcodec_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", chosen]
                vcodec = subprocess.run(vcodec_cmd, capture_output=True, text=True).stdout.strip().lower()
                if vcodec in ["vp9", "vp8", "av01", "vp09"]:
                    transcoded_file = os.path.join(DOWNLOAD_DIR, f"{job_id}_transcoded.mp4")
                    transcode_cmd = [
                        "ffmpeg", "-i", chosen,
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        "-movflags", "+faststart",
                        transcoded_file, "-y"
                    ]
                    print(f"Executing: {shlex.join(transcode_cmd)}")
                    subprocess.run(transcode_cmd, capture_output=True)
                    if os.path.exists(transcoded_file):
                        os.remove(chosen)
                        chosen = transcoded_file
            except Exception as e:
                print(f"Error checking codec or transcoding: {e}")

        job["file"] = chosen
        ext = os.path.splitext(chosen)[1]
        
        custom_name = job.get("custom_name", "").strip()
        if custom_name:
            safe_custom = "".join(c for c in custom_name if c not in r'\/:*?"<>|').strip()[:50].strip()
            job["filename"] = f"{safe_custom}{ext}" if safe_custom else os.path.basename(chosen)
        else:
            title = job.get("title", "").strip()
            if title:
                safe_title = "".join(c for c in title if c not in r'\/:*?"<>|').strip()[:50].strip()
                job["filename"] = f"{safe_title}{ext}" if safe_title else os.path.basename(chosen)
            else:
                job["filename"] = os.path.basename(chosen)

        # Extract posters using ffmpeg
        if format_choice != "audio":
            try:
                dur_cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", chosen]
                print(f"Executing: {shlex.join(dur_cmd)}")
                dur_output = subprocess.run(dur_cmd, capture_output=True, text=True).stdout.strip()
                if dur_output:
                    dur = float(dur_output)
                    frames = {
                        "first": 0,
                        "sec2": 2 if dur > 2 else dur/2,
                        "middle": dur / 2,
                        "end2": dur - 2 if dur > 2 else dur/2,
                        "last": dur - 0.1 if dur > 0.1 else 0
                    }
                    job["posters"] = {}
                    for key, timestamp in frames.items():
                        thumb_path = os.path.join(DOWNLOAD_DIR, f"{job_id}_{key}.jpg")
                        cmd = ["ffmpeg", "-ss", str(timestamp), "-i", chosen, "-vframes", "1", "-q:v", "2", thumb_path, "-y"]
                        print(f"Executing: {shlex.join(cmd)}")
                        subprocess.run(cmd, capture_output=True)
                        if os.path.exists(thumb_path):
                            job["posters"][key] = thumb_path
            except Exception:
                pass
                
            thumb_url = job.get("thumbnail")
            if thumb_url:
                try:
                    import urllib.request
                    orig_thumb_path = os.path.join(DOWNLOAD_DIR, f"{job_id}_original.jpg")
                    req = urllib.request.Request(thumb_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        if resp.status == 200:
                            with open(orig_thumb_path, "wb") as f:
                                f.write(resp.read())
                            if "posters" not in job: job["posters"] = {}
                            # Prepend to the dict manually by creating a new one
                            new_posters = {"original": orig_thumb_path}
                            new_posters.update(job["posters"])
                            job["posters"] = new_posters
                except Exception:
                    pass

        job["status"] = "done"
    except subprocess.TimeoutExpired:
        job["status"] = "error"
        job["error"] = "Download timed out (5 min limit)"
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH):
            session.permanent = True
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid password")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/info", methods=["POST"])
@login_required
def get_info():
    data = request.json
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    cmd = ["yt-dlp", "--no-playlist", "-S", "vcodec:h264,res,acodec:m4a", "-j", url]
    try:
        print(f"Executing: {shlex.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return jsonify({"error": result.stderr.strip().split("\n")[-1]}), 400

        info = json.loads(result.stdout)

        # Build quality options — keep best format per resolution
        best_by_height = {}
        for f in info.get("formats", []):
            height = f.get("height")
            if height and f.get("vcodec", "none") != "none":
                tbr = f.get("tbr") or 0
                if height not in best_by_height or tbr > (best_by_height[height].get("tbr") or 0):
                    best_by_height[height] = f

        formats = []
        for height, f in best_by_height.items():
            formats.append({
                "id": f["format_id"],
                "label": f"{height}p",
                "height": height,
            })
        formats.sort(key=lambda x: x["height"], reverse=True)

        return jsonify({
            "title": info.get("title", ""),
            "thumbnail": info.get("thumbnail", ""),
            "duration": info.get("duration"),
            "uploader": info.get("uploader", ""),
            "formats": formats,
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timed out fetching video info"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/download", methods=["POST"])
@login_required
def start_download():
    data = request.json
    url = data.get("url", "").strip()
    format_choice = data.get("format", "video")
    format_id = data.get("format_id")
    title = data.get("title", "")
    custom_name = data.get("custom_name", "")
    duration = data.get("duration", 0)
    thumbnail = data.get("thumbnail", "")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    job_id = uuid.uuid4().hex[:10]
    jobs[job_id] = {"status": "downloading", "url": url, "title": title, "custom_name": custom_name, "duration": duration, "thumbnail": thumbnail}

    thread = threading.Thread(target=run_download, args=(job_id, url, format_choice, format_id))
    thread.daemon = True
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
@login_required
def check_status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "status": job["status"],
        "error": job.get("error"),
        "filename": job.get("filename"),
        "posters": list(job.get("posters", {}).keys()) if "posters" in job else []
    })


@app.route("/api/file/<job_id>")
@login_required
def download_file(job_id):
    job = jobs.get(job_id)
    custom_filename = request.args.get('filename')
    download_name = custom_filename if custom_filename else job["filename"]
    
    return send_file(job["file"], as_attachment=True, download_name=download_name)


@app.route("/api/poster/<job_id>/<poster_id>")
@login_required
def download_poster(job_id, poster_id):
    job = jobs.get(job_id)
    if not job or "posters" not in job or poster_id not in job["posters"]:
        return jsonify({"error": "Poster not found"}), 404
    
    is_download = request.args.get("download") == "1"
    base_name = os.path.splitext(job.get("filename", "video"))[0]
    filename = f"{base_name}.jpg"
    
    return send_file(job["posters"][poster_id], as_attachment=is_download, download_name=filename if is_download else None)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8899))
    host = os.environ.get("HOST", "127.0.0.1")
    app.run(host=host, port=port)
