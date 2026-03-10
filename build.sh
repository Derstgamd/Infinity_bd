#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install Python dependencies from requirements.txt
pip install -r requirements.txt

# 2. Create a local folder for the FFmpeg binaries
mkdir -p ffmpeg

# 3. Download the latest static FFmpeg build for Linux 64-bit
curl -L https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | tar xJ -C ffmpeg --strip-components=1


chmod +x ffmpeg/ffmpeg
chmod +x ffmpeg/ffprobe

echo "Build complete: FFmpeg is ready at $(pwd)/ffmpeg/ffmpeg"