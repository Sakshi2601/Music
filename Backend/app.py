from flask import Flask, render_template, request, session, redirect, url_for
from pydub import AudioSegment
import os, base64
import librosa
import numpy as np

# 💡 Set FFmpeg path manually
AudioSegment.converter = r"C:\Users\saksh\Downloads\ffmpeg-7.1.1-essentials_build\ffmpeg-7.1.1-essentials_build\bin\ffmpeg.exe"

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'music-yantra-🔥-secret-key'
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def home():
    return render_template('index.html')

def get_indian_note(freq):
    if freq < 20: return ""
    C4 = 261.63  # Base Sa
    semitone_names = [
        'Sa', 'Re♭ (Komal)', 'Re', 'Ga♭ (Komal)', 'Ga', 'Ma',
        'Ma♯ (Tivra)', 'Pa', 'Dha♭ (Komal)', 'Dha', 'Ni♭ (Komal)', 'Ni'
    ]
    num_semitones = int(round(12 * np.log2(freq / C4)))
    note = semitone_names[num_semitones % 12]
    octave = 4 + (num_semitones + 9) // 12
    return f"{note} (Oct {octave})"

@app.route('/analyse', methods=['POST'])
def analyse():
    file_path = ''
    if 'audio_file' in request.files and request.files['audio_file'].filename:
        file = request.files['audio_file']
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
    elif 'recorded_blob' in request.form and request.form['recorded_blob']:
        blob_data = request.form['recorded_blob'].split(',')[1]
        audio_bytes = base64.b64decode(blob_data)
        file_path = os.path.join(UPLOAD_FOLDER, 'recorded.wav')
        with open(file_path, 'wb') as f:
            f.write(audio_bytes)
    else:
        return "Search functionality coming soon"

    # Load and process
    y, sr = librosa.load(file_path)

    # Use YIN algorithm for better pitch detection
    pitches = librosa.yin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'), sr=sr)

    notes = [get_indian_note(float(p)) for p in pitches if not np.isnan(p)]
    session['expected_notes'] = notes

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    print("Extracted Notes:", notes)
    return render_template('notes.html', notes=notes, tempo=tempo.item())

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/compare', methods=['POST'])
def compare_recording():
    file = request.files['audio']
    original_filename = file.filename
    uploaded_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
    file.save(uploaded_path)

    print("Uploaded to:", uploaded_path)
    print("Exists?", os.path.exists(uploaded_path))

    # ✅ Convert to WAV
    wav_path = os.path.join(app.config['UPLOAD_FOLDER'], 'converted.wav')
    audio = AudioSegment.from_file(uploaded_path)
    audio.export(wav_path, format="wav")

    # ✅ Load with librosa
    y, sr = librosa.load(wav_path)
    pitches = librosa.yin(y, fmin=librosa.note_to_hz('C2'),
                          fmax=librosa.note_to_hz('C7'), sr=sr)
    recorded_notes = [get_indian_note(float(p)) for p in pitches if not np.isnan(p)]

    expected_notes = session.get('expected_notes', [])
    matched = sum(1 for a, b in zip(recorded_notes, expected_notes) if a == b)
    total = min(len(expected_notes), len(recorded_notes))
    accuracy = round((matched / total) * 100, 2) if total > 0 else 0

    session['recorded_notes'] = recorded_notes
    session['accuracy'] = accuracy

    return redirect(url_for('show_result'))

@app.route('/result')
def show_result():
    accuracy = session.get('accuracy', 0)
    expected_notes = session.get('expected_notes', [])
    recorded_notes = session.get('recorded_notes', [])

    if accuracy >= 85:
        message = "🎉 Amazing! Great performance!"
    elif accuracy >= 60:
        message = "👍 Good! You did well!"
    else:
        message = "📝 Keep Practicing! You can improve."

    return render_template('result.html', accuracy=accuracy, message=message,
                           expected_notes=expected_notes, recorded_notes=recorded_notes)




if __name__ == '__main__':
    app.run(debug=True)
