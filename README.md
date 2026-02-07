# Receipt Organizer

**Receipt Organizer** is a tool for extracting data from receipt images, storing it in a local database, and visualizing spending trends. It uses **Optical Character Recognition (OCR)** to convert images into structured text and applies parsing logic to identify key financial information.

## Features
* **Data Extraction:** Identifies **Vendor**, **Date**, and **Total Paid** from images.
* **Adaptive Learning Loop:** Uses a custom SQLite-based mapping system. When you manually correct a category, the app "learns" and automatically applies that preference to future receipts from the same vendor.
* **Categorization:** Assigns expenses to categories (e.g., **Food**, **Travel**, **Supplies**) using keyword matching.
* **Dashboard:** Displays spending timelines and category distributions.
* **Data Integrity & CRUD:**
    * **Duplicate Prevention:** Checks for existing Vendor/Date/Total combinations to prevent double-entry.
    * **Inline Editing:** A powerful data grid interface for bulk updates and one-click deletions using a dropdown-based category selector.
* **Date Standardization:** Converts varying date formats into a uniform **DD/MM/YY** format.

## Technical Stack
* **Language:** Python 3.10+
* **OCR:** Tesseract OCR
* **UI Framework:** Streamlit
* **Data Analysis:** Pandas & Plotly
* **Database:** SQLite3

## Logic and Implementation
* **Regex Engine:** Uses negative lookbehinds to skip "Subtotal" and "Tax," capturing only the final transaction amount.
* **State Management:** Utilizes Streamlit's `session_state` and `st.rerun()` to ensure the UI stays synchronized with the database after every edit.
* **Database Schema:** Implements a two-table relational structure:
    1.  `receipts`: Stores the raw and processed transaction data.
    2.  `vendor_map`: Stores learned vendor-to-category relationships.

## Installation and Setup

### 1. Install Tesseract OCR
* **Windows:** Download the installer from the [UB Mannheim Wiki](https://github.com/UB-Mannheim/tesseract/wiki). **Important:** Add the installation path to your System Environment Variables.

### 2. Execution
* **Windows:** Run run_app.bat. This script creates a virtual environment, installs dependencies, and starts the application.

### Clone the Repository
```bash
  git clone [https://github.com/Aszariel1/receipt-organizer.git](https://github.com/Aszariel1/receipt-organizer.git)
  cd receipt-organizer



