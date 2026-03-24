import os
import subprocess
import yt_dlp
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_EXE = os.path.join(BASE_DIR, 'ffmpeg', 'ffmpeg')
COOKIES_FILE = os.environ.get('COOKIES_FILE', os.path.join(BASE_DIR, 'cookies.txt'))

# Fix permissions once at startup
if os.path.exists(FFMPEG_EXE):
    os.chmod(FFMPEG_EXE, 0o755)

def get_stream_url(video_url):
    opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'extractor_args': {
            'youtube': {'player_client': ['ios']}
        },
    }
    if os.path.exists(COOKIES_FILE):
        opts['cookiefile'] = COOKIES_FILE

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        return info['url'], info.get('title', 'audio')


@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "awake",
        "ffmpeg_exists": os.path.exists(FFMPEG_EXE),
        "cookies_loaded": os.path.exists(COOKIES_FILE)
    }), 200


@app.route('/stream', methods=['GET'])
def stream_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing URL parameter"}), 400

    try:
        stream_url, title = get_stream_url(video_url)

        ffmpeg_cmd = [
            FFMPEG_EXE,
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '5',
            '-i', stream_url,
            '-vn',
            '-acodec', 'libmp3lame',
            '-ab', '128k',
            '-ar', '44100',
            '-f', 'mp3',
            'pipe:1'
        ]

        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        def generate_chunks():
            try:
                while True:
                    chunk = process.stdout.read(16384)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                print(f"Streaming error: {e}")
            finally:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()

        return Response(
            generate_chunks(),
            mimetype='audio/mpeg',
            headers={
                "Content-Type": "audio/mpeg",
                "Accept-Ranges": "none",
                "X-Track-Title": title
            }
        )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)