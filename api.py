so i need to update my pu code with this below code
"import re
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

# -------------------------------
# Root route for quick check
# -------------------------------
@app.route("/", methods=["GET"])
def home():
    return "✅ Flask OCR API is running! Use POST /extract_text with a file."

# -------------------------------
# Extract Text Route
# -------------------------------
@app.route('/extract_text', methods=['GET', 'POST'])
def extract_text():
    if request.method == "GET":
        return "Send a POST request with a file to extract text."

    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Unsupported file format"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    text = ""

    # Handle PDF or Image
    if filename.lower().endswith(".pdf"):
        images = convert_from_path(filepath)
        for img in images:
            text += pytesseract.image_to_string(img) + "\n"
    else:
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img)

    # Extract Header Info
    date_match = re.search(r"Date[: ]+(\d{2}/\d{2}/\d{4})", text)
    due_date_match = re.search(r"Due Date[: ]+(\d{2}/\d{2}/\d{4})", text)
    bill_no_match = re.search(r"Bill no[: ]+(\d+)", text, re.IGNORECASE)

    vendor_match = re.search(r"Vendor Name[: ]+([A-Za-z ]+)", text)
    customer_match = re.search(r"Customer Name[: ]+([A-Za-z ]+)", text)
    name_match = re.search(r"Name[: ]+([A-Za-z ]+)", text)

    # Extract Item Table
    items = []
    lines = text.splitlines()
    start_extract = False
    for line in lines:
        line = line.strip()
        if re.search(r"Item\s+Quantity\s+Rate\s+amount", line, re.IGNORECASE):
            start_extract = True
            continue
        if start_extract and line:
            parts = line.split()
            if len(parts) >= 4:
                item_name = " ".join(parts[:-3])
                qty = parts[-3]
                rate = parts[-2]
                amount = parts[-1]
                items.append({
                    "Item Name": item_name,
                    "Quantity": qty,
                    "Rate": rate,
                    "Amount": amount
                })

    # Final JSON Response
    response = {
        "Date": date_match.group(1) if date_match else None,
        "Due Date": due_date_match.group(1) if due_date_match else None,
        "Reference No/Bill No": bill_no_match.group(1) if bill_no_match else None,
        "Vendor Name": vendor_match.group(1) if vendor_match else None,
        "Customer Name": customer_match.group(1) if customer_match else None,
        "Name": name_match.group(1) if name_match else None,
        "Items": items,
        "Raw Extracted Text": text
    }

    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
"
