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

def extract_text_from_file(filepath):
    text = ""
    if filepath.endswith(".pdf"):
        images = convert_from_path(filepath)
        for img in images:
            text += pytesseract.image_to_string(img)
    else:
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img)
    return text

def parse_data(text):
    data = {
        "vendor_info": {
            "aliases": ["Name", "Vendor Name", "Customer Name"],
            "name": None
        },
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
        "expenses": [],
        "raw_text": text
    }

    # Extract vendor name
    vendor_match = re.search(r"Name[:\- ]+([A-Za-z ]+)", text, re.IGNORECASE)
    if vendor_match:
        data["vendor_info"]["name"] = vendor_match.group(1).strip()

    # Extract bill number
    bill_match = re.search(r"Bill\s*(?:No|Number)?[:\- ]+(\w+)", text, re.IGNORECASE)
    if bill_match:
        data["bill_info"]["bill_number"] = bill_match.group(1).strip()

    # Extract dates (MM/DD/YYYY or DD/MM/YYYY)
    created_date_match = re.search(r"Date[:\- ]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text, re.IGNORECASE)
    if created_date_match:
        data["dates"]["created_date"] = created_date_match.group(1).strip()

    due_date_match = re.search(r"Due\s*Date[:\- ]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text, re.IGNORECASE)
    if due_date_match:
        data["dates"]["due_date"] = due_date_match.group(1).strip()

    # Extract items (Item Name, Quantity, Rate, Amount)
    item_pattern = re.findall(r"([A-Za-z ]+)\s+(\d+)\s+(\d+)\s+(\d+)", text)
    for item in item_pattern:
        data["items"].append({
            "item_name": item[0].strip(),
            "description": None,
            "rate": item[2],
            "amount": item[3],
            "aliases": {
                "item_name": ["Item", "Item Name"],
                "description": ["Item Description", "Description"],
                "rate": ["Item Rate", "Rate", "Price"],
                "amount": ["Total Amount", "Amount"]
            }
        })

    # Extract expenses (Account + Amount) → Dummy example
    expense_match = re.findall(r"Account[:\- ]+(\w+)\s+Amount[:\- ]+(\d+)", text, re.IGNORECASE)
    for exp in expense_match:
        data["expenses"].append({
            "account": exp[0],
            "amount": exp[1],
            "aliases": {
                "account": ["Account"],
                "amount": ["Amount"]
            }
        })

    return data


@app.route("/extract_text", methods=["POST"])
def extract_text():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        extracted_text = extract_text_from_file(filepath)
        parsed_json = parse_data(extracted_text)

        return jsonify(parsed_json)

    return jsonify({"error": "Invalid file type"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
