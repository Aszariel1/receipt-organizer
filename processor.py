import re
from datetime import datetime
from dateutil import parser
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def categorize_vendor(vendor_name, raw_text):
    """Assigns a category based on keywords found in the text."""
    text_to_scan = (vendor_name + " " + raw_text).lower()

    categories = {
        "Food & Dining": ["restaurant", "cafe", "mcdonald", "starbucks", "grill", "pizza", "burger", "subway", "taco"],
        "Travel": ["uber", "lyft", "airline", "hotel", "inn", "railway", "taxi", "gas", "shell", "chevron", "bp"],
        "Supplies": ["amazon", "walmart", "target", "staples", "office", "apple", "best buy", "costco"],
        "Services": ["subscription", "netflix", "cloud", "hosting", "insurance", "medical", "gym"]
    }

    for category, keywords in categories.items():
        if any(kw in text_to_scan for kw in keywords):
            return category

    return "Miscellaneous"


def extract_vendor(lines):
    blacklist = ["RECEIPT", "TAX INVOICE", "INVOICE", "WELCOME"]
    for line in lines:
        clean_line = line.strip()
        # Skip empty lines or generic titles
        if clean_line and not any(word in clean_line.upper() for word in blacklist):
            return clean_line
    return "Unknown Vendor"


def extract_date(text):
    """Finds a date and converts it to DD/MM/YY format."""
    # Look for the word 'Date' followed by characters and then something that looks like a date
    date_keyword_match = re.search(r"Date[:\s]+([A-Za-z0-9/\s,.-]+)", text, re.IGNORECASE)

    if date_keyword_match:
        raw_date = date_keyword_match.group(1).split('\n')[0].strip()
        try:
            # dateutil.parser is smart: it handles "April 9/2025" or "09-04-2025"
            parsed_date = parser.parse(raw_date, fuzzy=True)
            return parsed_date.strftime("%d/%m/%y")
        except (ValueError, OverflowError):
            pass

    # Fallback to standard numeric DD/MM/YYYY search if keyword search fails
    numeric_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text)
    if numeric_match:
        try:
            parsed_date = parser.parse(numeric_match.group(0))
            return parsed_date.strftime("%d/%m/%y")
        except:
            pass

    return datetime.now().strftime("%d/%m/%y")


def extract_total(text):
    """Target the absolute final total, ignoring subtotals."""
    # 1. Search for 'Total Paid' specifically first (strongest signal)
    # This regex looks for 'Total Paid', skips non-digits, and grabs the number
    final_match = re.search(r"Total Paid\s*[^\d]*([\d,.]+)", text, re.IGNORECASE)

    # 2. If not found, look for 'Total' but NOT 'Subtotal'
    if not final_match:
        # Finds 'Total' as long as 'Sub' isn't right before it
        final_match = re.search(r"(?<!Sub)Total\s*[^\d]*([\d,.]+)", text, re.IGNORECASE)

    if final_match:
        raw_val = final_match.group(1).replace(',', '')  # Remove thousands separator
        try:
            return float(raw_val)
        except:
            return 0.0

    # 3. Last resort: Max number logic
    amounts = re.findall(r"(\d+[\.,]\d{2})", text)
    return max([float(x.replace(',', '.')) for x in amounts]) if amounts else 0.0


def extract_receipt_data(image_file):
    img = Image.open(image_file)
    text = pytesseract.image_to_string(img)
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Improved Vendor Logic from previous step
    vendor = extract_vendor(lines)

    # New Improved Total Logic
    total = extract_total(text)

    # New Standardized Date Logic
    receipt_date = extract_date(text)

    category = categorize_vendor(vendor, text)

    return {
        "vendor": vendor,
        "total": total,
        "date": receipt_date,
        "category": category,
        "raw_text": text
    }
