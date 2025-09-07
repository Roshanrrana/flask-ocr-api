import os
import re
import pytesseract
import fitz  # PyMuPDF
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from pdf2image import convert_from_path
from PIL import Image

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/extract_text", methods=["POST"])
def extract_text():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            if os.path.getsize(filepath) == 0:
                return jsonify({"error": "Uploaded file is empty"}), 400

            extracted_text = ""

            # 1️⃣ Try with PyMuPDF
            try:
                doc = fitz.open(filepath)
                for page in doc:
                    extracted_text += page.get_text()
                doc.close()
            except Exception as e:
                print("PyMuPDF failed:", e)

            # 2️⃣ If still empty, try pdf2image + OCR
            if not extracted_text.strip():
                try:
                    images = convert_from_path(filepath)
                    for img in images:
                        extracted_text += pytesseract.image_to_string(img)
                except Exception as e:
                    print("pdf2image failed:", e)

            # 3️⃣ If still empty, try direct image OCR
            if not extracted_text.strip() and filename.lower().endswith(("png", "jpg", "jpeg")):
                try:
                    image = Image.open(filepath)
                    extracted_text = pytesseract.image_to_string(image)
                except Exception as e:
                    print("Image OCR failed:", e)

            # 4️⃣ If still empty → return error
            if not extracted_text.strip():
                return jsonify({
                    "error": "Unable to extract text",
                    "raw": "File may be corrupted or unsupported"
                }), 500

            # ✅ Clean extracted text
            cleaned_text = re.sub(r"\s+", " ", extracted_text).strip()

            # 🔹 Return structured JSON (template)
            response_json = {
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
                ],
                "raw_text": cleaned_text  # Keep original extracted text for debugging
            }

            return jsonify(response_json)

        return jsonify({"error": "File type not allowed"}), 400

    except Exception as e:
        return jsonify({
            "error": "OCR API error: Invalid response from OCR API",
            "raw": str(e)
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
