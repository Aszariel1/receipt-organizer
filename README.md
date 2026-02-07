# Receipt Pulse: Expense Organizer

**Receipt Pulse** is a tool for extracting data from receipt images, storing it in a local database, and visualizing spending trends. It uses **Optical Character Recognition (OCR)** to convert images into structured text and applies parsing logic to identify key financial information.

## Features
* **Data Extraction:** Identifies **Vendor**, **Date**, and **Total Paid** from images.
* **Categorization:** Assigns expenses to categories (e.g., **Food**, **Travel**, **Supplies**) using keyword matching.
* **Dashboard:** Displays spending timelines and category distributions.
* **Database Management:** Interface to **Create, Read, Update, and Delete (CRUD)** records.
* **Date Standardization:** Converts varying date formats into a uniform **DD/MM/YY** format.

## Technical Stack
* **Language:** Python 3.10+
* **OCR:** Tesseract OCR
* **UI Framework:** Streamlit
* **Data Analysis:** Pandas & Plotly
* **Database:** SQLite3

## Logic and Implementation
* **Parsing Logic:** Uses regular expressions with negative lookbehinds to distinguish the final "Total Paid" from "Subtotal" or other intermediate values.
* **Axis Configuration:** Overrides default Plotly axis settings to display exact start and end dates on the timeline for improved clarity.
* **Validation:** Includes a verification step in the UI to allow for manual correction of OCR output before database entry.

## Installation and Setup

### 1. Install Tesseract OCR
* **Windows:** Download the installer from the [UB Mannheim Wiki](https://github.com/UB-Mannheim/tesseract/wiki). **Important:** Add the installation path to your System Environment Variables.

### 2. Execution
* **Windows:** Run run_app.bat. This script creates a virtual environment, installs dependencies, and starts the application.

### Clone the Repository
```bash
  git clone [https://github.com/Aszariel1/receipt-organizer.git](https://github.com/Aszariel1/receipt-organizer.git)
  cd receipt-organizer

