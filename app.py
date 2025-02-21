from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import yt_dlp
import os
import subprocess
import re
import requests
import time

app = Flask(__name__)
CORS(app)  

DOWNLOAD_FOLDER = 'downloads'
THUMBNAIL_FOLDER = 'thumbnails'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

@app.route('/video-info', methods=['POST'])
def video_info():
    data = request.get_json()  
    url = data.get('url') 
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
  
        if not url.startswith(('http://', 'https://')):
            return jsonify({"error": "Invalid URL"}), 400

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        
    
        video_details = {
            'title': info.get('title', 'Unknown Title'),
            'description': info.get('description', 'No description available'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'url': url,
        }

        return jsonify(video_details)

    except yt_dlp.DownloadError as e:
        return jsonify({"error": f"Download error: {str(e)}"}), 400
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred. Please try again later."}), 500

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()  # Parse JSON data
    url = data.get('url')
    title = data.get('title')
    thumbnail_url = data.get('thumbnail')

    if not url or not title:
        return jsonify({"error": "No URL or title provided"}), 400

    try:
        sanitized_title = sanitize_filename(title)
        video_path = os.path.join(DOWNLOAD_FOLDER, f'{sanitized_title}_video.mp4')
        audio_path = os.path.join(DOWNLOAD_FOLDER, f'{sanitized_title}_audio.mp4')
        final_path = os.path.join(DOWNLOAD_FOLDER, f'{sanitized_title}.mp4')
        thumbnail_path = os.path.join(THUMBNAIL_FOLDER, f'{sanitized_title}.jpg')

        # Ensure files are not in use or locked
        def ensure_file_unlocked(file_path, retries=3, delay=2):
            for i in range(retries):
                try:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    break
                except PermissionError:
                    if i < retries - 1:
                        print(f"File is in use, retrying in {delay} seconds...")
                        time.sleep(delay)
                    else:
                        raise Exception(f"Unable to access file: {file_path}")

  
        ensure_file_unlocked(video_path)
        ensure_file_unlocked(audio_path)
        ensure_file_unlocked(final_path)

   
        ydl_opts_video = {
            'format': 'bestvideo',
            'outtmpl': video_path,
            'noplaylist': True,
            'overwrites': True,
            'nooverwrites': False
        }

        ydl_opts_audio = {
            'format': 'bestaudio',
            'outtmpl': audio_path,
            'noplaylist': True,
            'overwrites': True,
            'nooverwrites': False
        }

        with yt_dlp.YoutubeDL(ydl_opts_video) as ydl:
            ydl.download([url])

        with yt_dlp.YoutubeDL(ydl_opts_audio) as ydl:
            ydl.download([url])


        subprocess.run([
            'ffmpeg', '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental', final_path
        ], check=True)

        if not os.path.exists(final_path):
            return jsonify({"error": "File not found"}), 404


        if thumbnail_url:
            try:
                thumbnail_response = requests.get(thumbnail_url, stream=True)
                if thumbnail_response.status_code == 200:
                    with open(thumbnail_path, 'wb') as f:
                        for chunk in thumbnail_response.iter_content(1024):
                            f.write(chunk)
            except Exception as e:
                print(f"Failed to download thumbnail: {str(e)}")


        file_size = os.path.getsize(final_path)

 
        response = send_file(
            final_path,
            as_attachment=True,
            download_name=f'{sanitized_title}.mp4',
            mimetype='video/mp4'
        )

  
        response.headers['Content-Length'] = str(file_size)

        return response

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500
def sanitize_filename(filename):
 
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)