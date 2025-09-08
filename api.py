import os
import base64
import re
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image
import pytesseract

app = Flask(__name__)

# Upload folder for temporary storage
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# OCR function
def extract_text_from_file(filepath):
    ext = filepath.rsplit('.', 1)[1].lower()
    text = ""
    try:
        if ext == 'pdf':
            images = convert_from_path(filepath)
            for img in images:
                text += pytesseract.image_to_string(img)
        else:
            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
    except Exception as e:
        return None, str(e)
    return text, None

# Parse extracted text to find mandatory fields
def parse_invoice_text(text):
    data = {}

    # Bill/Invoice Number
    match = re.search(r'(Invoice Number|Invoice No|Bill Number|Bill No|Inv No)[:\-]?\s*(\S+)', text, re.IGNORECASE)
    if match:
        data['bill_number'] = match.group(2)

    # Vendor/Supplier Name
    match = re.search(r'(Vendor|Supplier|From|Customer|Name)[:\-]?\s*(.+)', text, re.IGNORECASE)
    if match:
        data['vendor_name'] = match.group(2).split("\n")[0].strip()

    # Invoice Date
    match = re.search(r'(Invoice Date|Bill Date|Date)[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})', text, re.IGNORECASE)
    if match:
        data['bill_date'] = match.group(2)

    # Due Date
    match = re.search(r'(Due Date)[:\-]?\s*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})', text, re.IGNORECASE)
    if match:
        data['due_date'] = match.group(2)

    # Extract line items (very basic example, can be improved with table parsing)
    items = []
    lines = text.split("\n")
    for line in lines:
        # Try to match: Item Description Quantity Rate Amount
        match = re.search(r'(.+?)\s+(\d+)\s+([\d,.]+)\s+([\d,.]+)', line)
        if match:
            items.append({
                "description": match.group(1).strip(),
                "quantity": match.group(2),
                "rate": match.group(3),
                "amount": match.group(4)
            })
    if items:
        data['items'] = items

    return data

@app.route('/extract_text', methods=['POST'])
def extract_text_api():
    try:
        data = request.get_json()
        if not data or 'filename' not in data or 'filecontent' not in data:
            return jsonify({"error": "Invalid input, expected JSON with 'filename' and 'filecontent'"}), 400

        filename = secure_filename(data['filename'])
        if not allowed_file(filename):
            return jsonify({"error": "File type not allowed"}), 400

        # Decode Base64 content into file
        file_content = base64.b64decode(data['filecontent'])
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'wb') as f:
            f.write(file_content)

        # Run OCR
        text, error = extract_text_from_file(filepath)
        if error:
            return jsonify({"error": "OCR failed", "details": error}), 500

        # Parse mandatory fields
        parsed_data = parse_invoice_text(text)

        return jsonify({
            "raw_text": text,       # full OCR text
            "parsed_data": parsed_data  # extracted structured data
        }), 200

    except Exception as e:
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

if __name__ == '__main__':
    # If running on Heroku/Render, respect PORT env var
    port = int(os.environ.get("PORT", 5000))
    # If Windows, set tesseract path manually
    # pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    app.run(host='0.0.0.0', port=port, debug=True)
