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

def extract_fields(text):
    """
    Very simple regex-based field extraction from text.
    You can improve this later with AI/NLP.
    """
    data = {
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
        "items": [
            {
                "item_name": None,
                "description": None,
                "rate": None,
                "amount": None,
                "aliases": {
                    "item_name": ["Item", "Item Name"],
                    "description": ["Item Description", "Description"],
                    "rate": ["Item Rate", "Rate", "Price"],
                    "amount": ["Total Amount", "Amount"]
                }
            }
        ],
        "expenses": [
            {
                "account": None,
                "amount": None,
                "aliases": {
                    "account": ["Account"],
                    "amount": ["Amount"]
                }
            }
        ]
    }

    # Example regex patterns (very basic)
    bill_match = re.search(r"(Bill Number|Bill|Reference number)[:\- ]+(\S+)", text, re.IGNORECASE)
    if bill_match:
        data["bill_info"]["bill_number"] = bill_match.group(2)

    vendor_match = re.search(r"(Vendor Name|Customer Name|Name)[:\- ]+(.+)", text, re.IGNORECASE)
    if vendor_match:
        data["vendor_info"]["name"] = vendor_match.group(2).strip()

    date_match = re.search(r"(Date|Created Date)[:\- ]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text, re.IGNORECASE)
    if date_match:
        data["dates"]["created_date"] = date_match.group(2)

    due_match = re.search(r"(Due Date|Last Date)[:\- ]+(\d{2}[\/\-]\d{2}[\/\-]\d{4})", text, re.IGNORECASE)
    if due_match:
        data["dates"]["due_date"] = due_match.group(2)

    # Items (basic pattern: Item, Description, Rate, Amount)
    item_match = re.search(r"Item[:\- ]+(.+)", text, re.IGNORECASE)
    if item_match:
        data["items"][0]["item_name"] = item_match.group(1).strip()

    rate_match = re.search(r"(Rate|Price)[:\- ]+([\d\.]+)", text, re.IGNORECASE)
    if rate_match:
        data["items"][0]["rate"] = rate_match.group(2)

    amount_match = re.search(r"(Amount|Total Amount)[:\- ]+([\d\.]+)", text, re.IGNORECASE)
    if amount_match:
        data["items"][0]["amount"] = amount_match.group(2)

    return data

@app.route("/extract_text", methods=["POST"])
def extract_text():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            extracted_text = ""

            if filename.lower().endswith(".pdf"):
                images = convert_from_path(filepath)
                for img in images:
                    extracted_text += pytesseract.image_to_string(img) + "\n"
            else:
                img = Image.open(filepath)
                extracted_text = pytesseract.image_to_string(img)

            structured_data = extract_fields(extracted_text)

            return jsonify({
                "raw_text": extracted_text.strip(),
                "structured_data": structured_data
            })

        return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        return jsonify({
            "error": "OCR processing failed",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
