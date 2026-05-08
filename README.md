# ReClip

A self-hosted, open-source video and audio downloader with a clean web UI. Paste links from YouTube, TikTok, Instagram, Twitter/X, and 1000+ other sites — download as MP4 or MP3.

![Python](https://img.shields.io/badge/python-3.8+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

https://github.com/user-attachments/assets/419d3e50-c933-444b-8cab-a9724986ba05

![ReClip MP3 Mode](assets/preview-mp3.png)

## Features

- Download videos from 1000+ supported sites (via [yt-dlp](https://github.com/yt-dlp/yt-dlp))
- MP4 video or MP3 audio extraction
- Quality/resolution picker
- Bulk downloads — paste multiple URLs at once
- Automatic URL deduplication
- Clean, responsive UI — no frameworks, no build step
- Single Python file backend (~150 lines)

## Quick Start

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y ffmpeg python3-venv

# 2. Clone repository
git clone https://github.com/mscalora/reclip.git
cd reclip

# 3. Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Generate the password configuration
python setup_password.py

# 5. Run the dev server
flask run --host=127.0.0.1 --port=8899
```

Open **http://localhost:8899**.

## Systemd Deployment (Ubuntu)

For a persistent deployment on Ubuntu, you can install ReClip as a `systemd` service. This will create a dedicated `reclip` system user, copy the files to `/opt/reclip`, and ensure the application starts automatically on boot.

1. Ensure you have generated your `config.json` file using `setup_password.py` first!
2. Run the included installation script with `sudo`:

```bash
chmod +x install_service.sh
sudo ./install_service.sh
```

You can then manage the service using standard `systemctl` commands:
- `sudo systemctl status reclip`
- `sudo systemctl restart reclip`
- `sudo journalctl -u reclip -f`

## Usage

1. Paste one or more video URLs into the input box
2. Choose **MP4** (video) or **MP3** (audio)
3. Click **Fetch** to load video info and thumbnails
4. Select quality/resolution if available
5. Click **Download** on individual videos, or **Download All**

## Authentication / Setup

ReClip is secured with a password login. Before starting the server, you must create a `config.json` file in the root directory containing a bcrypt hash of your chosen password. 

To easily generate this file, run the included setup script from your terminal:

```bash
source venv/bin/activate
python setup_password.py
```

Alternatively, you can manually create the `config.json` file using any bcrypt hash generator (like PHP's `password_hash()`):

```json
{
  "admin_password_hash": "$2y$10$YOUR_BCRYPT_HASH_HERE"
}
```

If you do not create this file or leave the hash empty, the app will refuse to start and will print a helpful error message. Upon successful login, your session is valid for 1 year.

## Supported Sites

Anything [yt-dlp supports](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md), including:

YouTube, TikTok, Instagram, Twitter/X, Reddit, Facebook, Vimeo, Twitch, Dailymotion, SoundCloud, Loom, Streamable, Pinterest, Tumblr, Threads, LinkedIn, and many more.

## Stack

- **Backend:** Python + Flask (~150 lines)
- **Frontend:** Vanilla HTML/CSS/JS (single file, no build step)
- **Download engine:** [yt-dlp](https://github.com/yt-dlp/yt-dlp) + [ffmpeg](https://ffmpeg.org/)
- **Dependencies:** 2 (Flask, yt-dlp)

## Disclaimer

This tool is intended for personal use only. Please respect copyright laws and the terms of service of the platforms you download from. The developers are not responsible for any misuse of this tool.

## License

[MIT](LICENSE)
