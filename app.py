import os
import subprocess
import yt_dlp
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

FFMPEG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')

print(f"FFmpeg path: {FFMPEG_PATH}")
print(f"FFmpeg exists: {os.path.exists(os.path.join(FFMPEG_PATH, 'ffmpeg'))}")

@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "awake", "message": "Server is ready!"}), 200

@app.route('/stream', methods=['GET'])
def stream_audio():
    video_url = request.args.get('url')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'ffmpeg_location': FFMPEG_PATH,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']

        ffmpeg_cmd = [
            os.path.join(FFMPEG_PATH, 'ffmpeg'),
            '-i', stream_url,
            '-f', 'mp3',
            '-ab', '128k',
            'pipe:1'
        ]

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

        def generate_chunks(process):
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
            finally:
                process.kill()
                process.wait()

        return Response(
            generate_chunks(process),
            mimetype='audio/mpeg',
            headers={"Content-Type": "audio/mpeg"}
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)