import os
import subprocess
import yt_dlp
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# 1. Tell the app where to find FFmpeg (installed via build.sh)
FFMPEG_PATH = os.path.join(os.getcwd(), 'ffmpeg')

@app.route('/ping', methods=['GET'])
def ping():
    """Wakes up the server from React Native"""
    return jsonify({"status": "awake", "message": "Server is ready!"}), 200

@app.route('/stream', methods=['GET'])
def stream_audio():
    video_url = request.args.get('url')
    
    # These options force yt-dlp to ignore video entirely
    ydl_opts = {
        'format': 'bestaudio/best',  # Only fetch the best audio stream
        'noplaylist': True,          # Ensure we don't accidentally grab a whole list
        'quiet': True,
        'ffmpeg_location': FFMPEG_PATH,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # download=False is the most important part for performance!
            info = ydl.extract_info(video_url, download=False)
            
            # This is the direct URL to the audio-only stream on Google's servers
            stream_url = info['url']

        # Pipe that stream through FFmpeg to give your app a clean MP3
        ffmpeg_cmd = [
            os.path.join(FFMPEG_PATH, 'ffmpeg'),
            '-i', stream_url,        # Input is the audio-only URL
            '-f', 'mp3',             # Convert to mp3
            '-ab', '128k',           # Standard mobile quality
            'pipe:1'
        ]

        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE)

        def generate_chunks(process):
            try:
                # Read 4KB at a time from the FFmpeg stdout pipe
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