import re
import os
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

def extract_text_from_file(filepath):
    if filepath.lower().endswith(".pdf"):
        images = convert_from_path(filepath)
        text = ""
        for img in images:
            text += pytesseract.image_to_string(img)
        return text
    else:
        return pytesseract.image_to_string(Image.open(filepath))

def parse_invoice_text(text):
    structured_data = {
        "bill_info": {
            "aliases": ["Bill Number", "Bill", "Reference number"],
            "bill_number": None
        },
        "dates": {
            "aliases": {
                "created_date": ["Date", "Created Date"],
                "due_date": ["Due Date", "Last Date"]
            },
            "created_date": None,
            "due_date": None
        },
        "items": [],
        "vendor_info": {
            "aliases": ["Name", "Vendor Name", "Customer Name"],
            "name": None
        }
    }

    # ✅ Extract vendor/customer name
    name_match = re.search(r"(?:Name|Customer Name|Vendor Name)[:\s]+([A-Za-z ]+)", text, re.IGNORECASE)
    if name_match:
        structured_data["vendor_info"]["name"] = name_match.group(1).strip()

    # ✅ Extract Bill number
    bill_match = re.search(r"(?:Bill\s*No|Bill\s*Number|Invoice\s*No)[:\s]+(\d+)", text, re.IGNORECASE)
    if bill_match:
        structured_data["bill_info"]["bill_number"] = bill_match.group(1).strip()

    # ✅ Extract Dates (Created + Due Date)
    created_match = re.search(r"(?:Created\s*Date|Date)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if created_match:
        structured_data["dates"]["created_date"] = created_match.group(1).strip()

    due_match = re.search(r"(?:Due\s*Date|Last\s*Date)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if due_match:
        structured_data["dates"]["due_date"] = due_match.group(1).strip()

    # ✅ Extract Items (flexible table parser)
    # Looks for: Item | Qty | Quantity | Rate | Amount | Price
    lines = text.split("\n")
    for line in lines:
        if re.search(r"\b(Item|Product)\b", line, re.IGNORECASE):
            continue  # skip header line
        parts = re.split(r"\s{2,}|\t", line.strip())
        if len(parts) >= 3:
            try:
                item_name = parts[0]
                qty = int(re.findall(r"\d+", parts[1])[0]) if len(parts) > 1 and re.search(r"\d+", parts[1]) else None
                rate = int(re.findall(r"\d+", parts[2])[0]) if len(parts) > 2 and re.search(r"\d+", parts[2]) else None
                amount = int(re.findall(r"\d+", parts[-1])[0]) if re.search(r"\d+", parts[-1]) else None

                structured_data["items"].append({
                    "aliases": {
                        "item_name": ["Item", "Product", "Item Name"],
                        "description": ["Item Description", "Description"],
                        "rate": ["Rate", "Price"],
                        "amount": ["Amount", "Total Amount"]
                    },
                    "item_name": item_name,
                    "item_quantity": qty,
                    "rate": rate,
                    "amount": amount,
                    "description": None
                })
            except:
                continue

    return {"raw_text": text, "structured_data": structured_data}

@app.route('/extract_text', methods=['POST'])
def extract_text_api():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        text = extract_text_from_file(filepath)
        structured_data = parse_invoice_text(text)

        return jsonify(structured_data)

    return jsonify({"error": "Invalid file type"}), 400

if __name__ == '__main__':
    app.run(debug=True)
