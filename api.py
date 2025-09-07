import os
import re
import pytesseract
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

def parse_text_to_json(text):
    structured_data = {
        "vendor_info": {
            "name": None,
            "aliases": ["Name", "Vendor Name", "Customer Name"]
        },
        "bill_info": {
            "bill_number": None,
            "aliases": ["Bill Number", "Bill", "Reference number"]
        },
        "dates": {
            "created_date": None,
            "due_date": None,
            "aliases": {
                "created_date": ["Date", "Created Date"],
                "due_date": ["Due Date", "Last Date"]
            }
        },
        "items": []
    }

    # --- Vendor name ---
    vendor_match = re.search(r"Name:\s*(.+)", text, re.IGNORECASE)
    if vendor_match:
        structured_data["vendor_info"]["name"] = vendor_match.group(1).strip()

    # --- Bill number ---
    bill_match = re.search(r"Bill\s*no\s*(\d+)", text, re.IGNORECASE)
    if bill_match:
        structured_data["bill_info"]["bill_number"] = bill_match.group(1).strip()

    # --- Dates ---
    due_date_match = re.search(r"Due Date\s*([0-9/]+)", text, re.IGNORECASE)
    created_date_match = re.search(r"Date\s*([0-9/]+)", text, re.IGNORECASE)

    if due_date_match:
        structured_data["dates"]["due_date"] = due_date_match.group(1).strip()
    if created_date_match:
        structured_data["dates"]["created_date"] = created_date_match.group(1).strip()

    # --- Items (table detection) ---
    lines = text.splitlines()
    item_section = False
    for line in lines:
        if re.search(r"Item\s+Quantity\s+Rate\s+amount", line, re.IGNORECASE):
            item_section = True
            continue
        if item_section and line.strip():
            parts = line.split()
            if len(parts) >= 4:
                item_name = " ".join(parts[:-3])
                qty = parts[-3]
                rate = parts[-2]
                amount = parts[-1]
                structured_data["items"].append({
                    "item_name": item_name,
                    "description": None,
                    "item_qunatity": int(qty) if qty.isdigit() else qty,
                    "rate": float(rate) if rate.replace('.', '').isdigit() else rate,
                    "amount": float(amount) if amount.replace('.', '').isdigit() else amount,
                    "aliases": {
                        "item_name": ["Item", "Item Name"],
                        "description": ["Item Description", "Description"],
                        "rate": ["Item Rate", "Rate", "Price"],
                        "amount": ["Total Amount", "Amount"]
                    }
                })

    return {
        "raw_text": text,
        "structured_data": structured_data
    }

@app.route('/extract_text', methods=['POST'])
def extract_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)

        text = extract_text_from_pdf(file_path)
        result = parse_text_to_json(text)

        return jsonify(result)
    return jsonify({"error": "Invalid file format"}), 400

if __name__ == '__main__':
    app.run(debug=True)
