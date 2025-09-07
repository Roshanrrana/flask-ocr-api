import os
import re
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

# Initialize Flask app
app = Flask(__name__)

# Folder to store uploaded files
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file types
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Check if uploaded file is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# OCR function
def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    text = ""
    try:
        if ext == 'pdf':
            # Convert PDF pages to images
            images = convert_from_path(filepath)
            for img in images:
                text += pytesseract.image_to_string(img)
        else:
            # Directly read image file
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
    except Exception as e:
        return None, str(e)
    return text, None

# API route
@app.route('/extract_text', methods=['POST'])
def extract_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        text, error = extract_text_from_file(filepath)
        if error:
            return jsonify({"error": "OCR failed", "details": error}), 500
        
        return jsonify({"extracted_text": text}), 200
    else:
        return jsonify({"error": "File type not allowed"}), 400

# Run the app
if __name__ == '__main__':
    # Make sure pytesseract path is set if needed (for Windows)
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    app.run(host='0.0.0.0', port=5000, debug=True)
