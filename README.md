# StyleVision Product Entry

This Streamlit app allows manual input of a single product into the ecommerce system via an interactive form.  
It generates marketing-friendly product descriptions using Groq, stores images locally, and saves all product data to CSV (`ecommerce/final_output.csv`).

## Features
- Interactive form for product data entry
- Ensures required fields are filled before generating descriptions or saving
- Automatically generates unique Product IDs
- Saves product images locally with the Product ID as filename
- Generates product descriptions using Groq LLM
- Provides instant feedback on save success/failure
- Displays a live Product Details preview
- Deduplicates attributes and merges them for clean CSV storage
- Responsive and visually enhanced with a background image

## Requirements
- Python 3.9+
- Dependencies listed in `requirements.txt`

## Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd stylevision-product-entry

2. Create a virtual environment:

python -m venv stylevision_env
source stylevision_env/bin/activate  # Linux/macOS
stylevision_env\Scripts\activate     # Windows


3. Install dependencies:

pip install -r requirements.txt

4. Add your Groq API key to Streamlit secrets (.streamlit/secrets.toml):

GROQ_API_KEY = "your_groq_api_key_here"


5. Run the app:

streamlit run app.py

Usage Notes
 - Fields marked with * are mandatory for description generation and saving.
 - Product images are saved in the img/ folder with filenames matching the Product ID (YY_xxxxxxxx.jpg).
 - The description preview is generated using only the attributes you provide — missing fields are not hallucinated.
 - If you make changes to a product entry before saving, regenerate the description to reflect the updates.
 - Once saved, a product cannot be updated; refresh the page to add another item.

File Structure
stylevision-product-entry/
├── app.py                  # Main Streamlit app
├── ecommerce/
│   └── final_output.csv    # CSV storage for product entries
├── img/                    # Uploaded product images
├── requirements.txt        # Python dependencies
└── README.md

Optional

Use PyInstaller to create a standalone executable:

pyinstaller --onefile app.py