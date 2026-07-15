import io
import zipfile
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from PIL import Image, ImageSequence

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# --- 1. GIF ZU FRAMES (Zerlegen) ---
@app.route('/gif-to-frames', methods=['POST'])
def gif_to_frames():
    if 'file' not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Ungültige Datei"}), 400

    try:
        # GIF öffnen
        img = Image.open(io.BytesIO(file.read()))
        
        # ZIP-Archiv im Arbeitsspeicher erstellen
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Iteriere durch alle Frames des GIFs
            for i, frame in enumerate(ImageSequence.Iterator(img)):
                # Jeden Frame als PNG konvertieren und im Speicher halten
                frame_buffer = io.BytesIO()
                # Frame konvertieren, falls Palette-Modus Probleme macht
                frame_conv = frame.convert('RGBA')
                frame_conv.save(frame_buffer, format='PNG')
                frame_buffer.seek(0)
                
                # In das ZIP-Archiv schreiben
                zip_file.writestr(f"frame_{i:03d}.png", frame_buffer.read())

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name="gif_frames.zip"
        )
    except Exception as e:
        return jsonify({"error": f"Fehler beim Zerlegen des GIFs: {str(e)}"}), 500


# --- 2. BILDER ZU GIF (Zusammenfügen) ---
@app.route('/frames-to-gif', methods=['POST'])
def frames_to_gif():
    files = request.files.getlist('files')
    duration = int(request.form.get('duration', 100))  # Standard: 100ms pro Frame
    loop = int(request.form.get('loop', 0))          # Standard: Unendlich (0)

    if not files or len(files) < 2:
        return jsonify({"error": "Mindestens zwei Bilder werden benötigt."}), 400

    try:
        images = []
        for file in files:
            img = Image.open(io.BytesIO(file.read()))
            # Konvertieren in RGBA, um Transparenz zu wahren und alle Formate anzugleichen
            images.append(img.convert('RGBA'))

        # Größe vereinheitlichen (falls Bilder unterschiedlich groß sind)
        # Wir passen alle Bilder an die Maße des ersten Bildes an
        base_size = images[0].size
        resized_images = []
        for img in images:
            if img.size != base_size:
                img = img.resize(base_size, Image.Resampling.LANCZOS)
            resized_images.append(img)

        # Erstes Bild als Basis nehmen, die restlichen als Frames anhängen
        output_gif = io.BytesIO()
        resized_images[0].save(
            output_gif,
            format='GIF',
            save_all=True,
            append_images=resized_images[1:],
            duration=duration,
            loop=loop,
            disposal=2 # Vermeidet Geisterbilder-Effekte bei transparenten PNGs
        )
        output_gif.seek(0)

        return send_file(
            output_gif,
            mimetype='image/gif',
            as_attachment=True,
            download_name="animiertes_bild.gif"
        )
    except Exception as e:
        return jsonify({"error": f"Fehler beim Erstellen des GIFs: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=8080)
