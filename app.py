import os
import subprocess
import yt_dlp
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# Based on your build.sh, ffmpeg is in a folder named 'ffmpeg'
# Path to the actual binary: ./ffmpeg/ffmpeg
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_EXE = os.path.join(BASE_DIR, 'ffmpeg', 'ffmpeg')

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({
        "status": "awake", 
        "ffmpeg_exists": os.path.exists(FFMPEG_EXE)
    }), 200

@app.route('/stream', methods=['GET'])
def stream_audio():
    video_url = request.args.get('url')
    if not video_url:
        return jsonify({"error": "Missing URL parameter"}), 400
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']

        # The Magic Sauce: Reconnect flags + Explicit MP3 codec
        ffmpeg_cmd = [
            FFMPEG_EXE,
            '-reconnect', '1',
            '-reconnect_streamed', '1',
            '-reconnect_delay_max', '5',
            '-i', stream_url,
            '-vn',                # No video
            '-acodec', 'libmp3lame', # Force MP3 encoder (built into your static build)
            '-ab', '128k',        # Bitrate
            '-ar', '44100',       # Sample rate
            '-f', 'mp3',          # Force format
            'pipe:1'              # Output to stdout
        ]

        # Use stderr=subprocess.PIPE only if you need to debug logs
        process = subprocess.Popen(
            ffmpeg_cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.DEVNULL 
        )

        def generate_chunks():
            try:
                while True:
                    # 16KB chunks provide a good balance for streaming
                    chunk = process.stdout.read(16384)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                print(f"Streaming error: {e}")
            finally:
                # Clean up the process properly
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
                "Accept-Ranges": "none"
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)