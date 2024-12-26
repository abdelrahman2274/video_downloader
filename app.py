from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp as youtube_dl
import os

app = Flask(__name__)

# المسار لحفظ الملفات
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# دالة للتحقق من وجود الملف وإضافة رقم في حالة التكرار
def get_unique_filename(filepath):
    base, ext = os.path.splitext(filepath)
    counter = 1
    # إذا كان الملف موجودًا، أضف رقمًا إلى اسم الملف
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{ext}"
        counter += 1
    return filepath

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_formats', methods=['POST'])
def get_formats():
    video_url = request.form.get('video_url')
    
    if not video_url:
        return jsonify({"error": "No URL provided."}), 400

    try:
        # إعداد خيارات yt-dlp لاستخراج الجودات
        ydl_opts = {
            'quiet': True,
            'format': 'bestaudio/best',  # هذه إعدادات احتياطية لاختيار أفضل جودة
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)  # لا نقوم بتحميل الفيديو في هذه المرحلة
            formats = info_dict.get('formats', [])

        # قائمة الجودات المتاحة
        available_formats = []
        quality_map = {
            230: 144,
            384: 240,
            576: 360,
            769: 480,
            1150: 720,
            960: 720,
            1280: 720,
            1920: 1080,
            426: 240,
            640: 360,
            2560: 1440,
            854: 480
        }

        # إضافة الجودات المطلوبة فقط وتجنب التكرار
        seen_quality = set()

        for f in formats:
            if f.get('height'):
                new_quality = quality_map.get(f['height'], f['height'])
                # إذا كانت الجودة أقل من 144p أو كانت هذه الجودة موجودة بالفعل، نعيد تجاهلها
                if new_quality >= 144 and new_quality not in seen_quality:
                    available_formats.append({
                        'quality': f"{new_quality}p",
                        'quality_value': f['format_id']
                    })
                    seen_quality.add(new_quality)  # إضافة الجودة إلى المجموعات لتجنب التكرار
            elif f.get('format_note') == 'audio only':
                if 'MP3' not in seen_quality:  # تحقق من أن MP3 لم تضاف بعد
                    available_formats.append({
                        'quality': 'MP3',
                        'quality_value': f['format_id']
                    })
                    seen_quality.add('MP3')  # إضافة MP3 إلى المجموعات لتجنب التكرار

        return jsonify(available_formats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    video_url = request.form.get('video_url')
    quality = request.form.get('quality')
    audio_only = request.form.get('audio_only')

    # التحقق من وجود رابط الفيديو والجودة
    if not video_url:
        return jsonify({"error": "No URL provided."}), 400

    # إعدادات yt_dlp بناءً على اختيار الجودة أو التحويل إلى MP3
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s.%(ext)s',
        'noplaylist': True,
    }

    # إذا كان الخيار Audio Only مفعل، اختر أفضل جودة صوت فقط وتحويله إلى MP3
    if audio_only == 'true':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegAudioConvertor',  # نستخدم هنا معالج تحويل الصوت إلى MP3
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        # إذا كانت الجودة محددة، قم بتحديد الجودة
        ydl_opts['format'] = quality if quality else 'bestvideo+bestaudio/best'

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info_dict)  # مسار الفيديو المحمل
            
            # التحقق من وجود الملف وتحديثه إذا كان مكررًا
            unique_file_path = get_unique_filename(file_path)

            # إعادة تسمية الملف إذا كان مكررًا
            os.rename(file_path, unique_file_path)

        # إرسال الملف للمستخدم
        return send_file(unique_file_path, as_attachment=True)

    except Exception as e:
        return jsonify({"error": f"حدث خطأ: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)