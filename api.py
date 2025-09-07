import os
import base64
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

# Check if file extension is allowed
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# OCR function
def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    text = ""
    try:
        if ext == 'pdf':
            # Convert PDF pages to images and extract text
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

# API endpoint to extract text
@app.route('/extract_text', methods=['POST'])
def extract_text_api():
    try:
        data = request.get_json()
        if not data or 'filename' not in data or 'filecontent' not in data:
            return jsonify({"error": "Invalid input, expected JSON with 'filename' and 'filecontent'"}), 400

        filename = secure_filename(data['filename'])
        if not allowed_file(filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Decode Base64 file content
        file_content = base64.b64decode(data['filecontent'])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(file_content)

        # Extract text using OCR
        text, error = extract_text_from_file(filepath)
        if error:
            return jsonify({"error": "OCR failed", "details": error}), 500

        # Return extracted text in JSON
        return jsonify({"extracted_text": text}), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

# Run the Flask app
if __name__ == '__main__':
    # Uncomment and set this path if needed on Windows
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    app.run(host='0.0.0.0', port=5000, debug=True)
