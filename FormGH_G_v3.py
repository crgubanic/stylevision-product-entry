# -----------------------------
# StyleVision Product Entry App
# Streamlit + Groq + CSV product management
# Fully GitHub/Streamlit-ready (minimal portability fixes)
# -----------------------------

# Libraries
# pip install streamlit pyinstaller Pillow pandas

from groq import Groq
from PIL import Image, ImageDraw, ImageFont

import base64
import datetime
import html
import io
import os
import pandas as pd
import random
import requests
import socket
import streamlit as st
import subprocess
import sys
import time
import uuid
import webbrowser

print("✅ Libraries imported successfully.")

# --------------------------
# Page Configuration - Set this FIRST before any other Streamlit commands
st.set_page_config(
    page_title="StyleVision Product Entry",
    page_icon="👗",
    layout="wide"
)

# --- Initialize required session state keys ---
required_keys = [
    "name", "products", "category", "price", "description", "image_url",
    "brand", "sku", "color", "material", "tags", "fabric", "style",
    "season", "fit", "occasion", "gender"
]

for key in required_keys:
    if key not in st.session_state:
        st.session_state[key] = ""

# --------------------------
# Function for absolute path (works for PyInstaller)
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Project root is the directory containing this script (portable)
project_root = os.path.dirname(os.path.abspath(__file__))

# Ensure required directories exist (relative to project_root)
os.makedirs(os.path.join(project_root, "img"), exist_ok=True)
os.makedirs(os.path.join(project_root, "ecommerce"), exist_ok=True)

print(f"✅ Project root set to: {project_root}")
print("✅ Resource path function defined.")

# --------------------------
# BACKGROUND CODE - Define function
def apply_background():
    """Apply background to the app"""
    cache_buster = random.randint(1000, 9999)
    bg_url = "https://raw.githubusercontent.com/crgubanic/stylevision-product-entry/main/background2.jpg"
    try:
        response = requests.get(bg_url, timeout=10)
        response.raise_for_status()
        base64_bg = base64.b64encode(response.content).decode()
        st.markdown(
            f"""
            <style>
            [data-testid="stAppViewContainer"] > div:first-child {{
                background-image: url("data:image/jpeg;base64,{base64_bg}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            [data-testid="stHeader"] {{
                background-color: rgba(0,0,0,0);
            }}
            label {{
                font-size: 18px !important;
                font-weight: bold !important;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )
        print("✅ Background applied successfully")
        return True
    except Exception as e:
        print(f"❌ Background error: {e}")
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] > div:first-child {
            background: linear-gradient(180deg, #4a4a4a 0%, #6e6e6e 100%) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        return False

# --------------------------
# Call background BEFORE any other Streamlit elements
apply_background()

# --------------------------
# Header Section
st.title("StyleVision Product Entry")
st.markdown("""
<div style="
    background-color: rgba(204, 51, 0, 0.75);
    border: 1px solid #4a3a8c;
    border-radius: 16px;
    padding: 20px;
    font-size: 18px;
    line-height: 1.6;
    box-shadow: 0 0 10px rgba(0,0,0,0.4);
">
    This app uses <b>Groq Generative AI</b> to create professional product descriptions from structured e-commerce data. It generates high-quality, natural-language text from user-provided attributes, demonstrating practical AI-assisted content creation. The app supports live previews, CSV storage, and robust session management, showcasing a portable, production-ready integration of AI into a web interface.
</div>
""", unsafe_allow_html=True)

st.divider()

# --------------------------
# Load API key and initialize Groq client
groq_api_key = st.secrets["GROQ_API_KEY"]
client = Groq(api_key=groq_api_key)

# --------------------------
# CSV file to save entries
csv_file = resource_path(os.path.join("ecommerce", "final_output.csv"))
print(f"✅ CSV file path: {csv_file}")

if not os.path.exists(csv_file):
    pd.DataFrame(columns=[
        "p_id", "name", "products", "price", "brand", "cold_start", "rating_bucket",
        "img", "theme_merged_color_pattern", "theme_merged_fit", "theme_merged_fabric_care",
        "formatted", "description_generated"
    ]).to_csv(csv_file, index=False)

# Columns for final CSV output
final_columns = [
    "p_id", "name", "products", "price", "brand", "img",
    "theme_merged_color_pattern", "theme_merged_fit", "theme_merged_fabric_care",
    "formatted", "description_generated"
]

print("✅ CSV file initialized.")

# --------------------------
# Generate unique Product ID
def generate_new_pid():
    year_prefix = datetime.datetime.now().strftime("%y")
    random_digits = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{year_prefix}_{random_digits}"

# --------------------------
# Initialize main session_state variables
if "p_id" not in st.session_state:
    st.session_state["p_id"] = generate_new_pid()

if "saved_success" not in st.session_state:
    st.session_state["saved_success"] = False

if "saving" not in st.session_state:
    st.session_state["saving"] = False

if "description" not in st.session_state:
    st.session_state["description"] = ""

# --------------------------
# Clear Form button
if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0

if st.button("Clear Form"):
    st.session_state["reset_counter"] += 1
    for key in ["description", "description_generated", "prev_values", "p_id", "session_products"]:
        st.session_state.pop(key, None)
    st.session_state["p_id"] = generate_new_pid()
    st.rerun()

# --------------------------
# --------------------------
# --------- DYNAMIC KEYS INITIALIZATION (SAFE SINGLE BLOCK) ---------
rc = st.session_state.get("reset_counter", 0)

dynamic_keys = {
    "name": "",
    "products": [],
    "brand": "",
    "price_str": "",
    "colour": "",
    "fit": [],
    "fabric": [],
    "pattern": [],
    "care": [],
    "garment_closure": [],
    "occasion_region": []
    # DO NOT include 'uploaded_file' here
}

# --------------------------
# Initialize dynamic keys for the current reset counter
for key, default_value in dynamic_keys.items():
    dynamic_key = f"{key}_{rc}"
    if dynamic_key not in st.session_state:
        st.session_state[dynamic_key] = default_value

#
# #
# #
# # --------------------------
# File uploader (DO NOT assign st.session_state for this key)
#uploaded_file_input = st.file_uploader(
#    "Upload Product Image (.jpg required)*",
#    type=["jpg"],
#    key=f"uploaded_file_stable"
#)

# Use stable reference in session_state
#if uploaded_file_input is not None:
#    st.session_state["uploaded_file_ref"] = uploaded_file_input

# Generate filename for image
#img_filename = f"{st.session_state['p_id']}.jpg"

#uploaded_file_to_save = st.session_state.get("uploaded_file_ref")
#if uploaded_file_to_save is not None:
#    img_path = os.path.join(project_root, "img", img_filename)
#    os.makedirs(os.path.dirname(img_path), exist_ok=True)
#    with open(img_path, "wb") as f:
#        f.write(uploaded_file_to_save.getbuffer())
#    st.session_state["img"] = img_filename
#    st.success(f"Image saved as {img_filename}")

# --------------------------
# Form Fields
name = st.text_input("Product Name*", key=f"name_{rc}")

products = st.multiselect(
    "Product Type*", [
        "Blazer", "Clothing Set", "Bralette", "Dress", "Dupatta",
        "Hoodie", "Jacket", "Jeans", "Joggers", "Jumpsuit", "Kurta", "Kurti",
        "Lehenga", "Maternity", "Other", "Pants", "Pullover", "Saree", "Shawl", "Shirt",
        "Shorts", "Skirt", "Sweater", "Sweatshirt", "T-Shirt", "Top", "Vest"
    ],
    key=f"products_{rc}"
)

price_str = st.text_input("Price (USD)*", key=f"price_str_{rc}")
price = None
if price_str:
    try:
        float(price_str)
        st.session_state['price'] = price_str
    except ValueError:
        st.error("Please enter a valid price, e.g., 808.08")
        st.session_state['price'] = ""
else:
    st.session_state['price'] = ""

colour = st.selectbox(
    "Colour (Primary)*", [
        "-- Select Colour --", "Beige", "Black", "Blue", "Bronze", "Brown", "Burgandy",
        "Camel", "Champagne", "Charcoal", "Coffee", "Copper", "Coral", "Cream",
        "Fuschia", "Gold", "Green", "Grey", "Khaki", "Magenta", "Maroon",
        "Mauve", "Multi", "Navy", "Olive", "Orange", "Peach", "Pink", "Purple",
        "Other", "Red", "Rose Gold", "Rust", "Silver", "Tan", "Taupe", "Teal",
        "Turquoise", "Violet", "White", "Yellow"
    ],
    key=f"colour_{rc}"
)

pattern = st.multiselect("Pattern (Primary)*", [
    "-- Select Pattern --", "Aari Work", "Abstract", "Animal", "Applique",
    "Arjak", "Argyle", "Bagh", "Bandhani", "Batik", "Beads and Stones",
    "Block Print", "Bohemian", "Boucle", "Brocade", "Camouflage",
    "Cartoon / Graphic / Superhero", "Checked", "Chevron", "Chikankari",
    "Colourblocked", "Cutdana Work", "Dabu", "Distressed", "Embellished",
    "Embroidered", "Ethnic", "Fair Isle", "Faux Fur Trim",
    "Faux Leather Trim", "Floral", "Foil", "Frills Bows and Ruffles",
    "Fringe / Tassel", "Geometric", "Gotta Pattie", "Houndstooth", "Ikat",
    "Jaali", "Kalamkari", "Kantha Work", "Khari", "Kutchi Embroidery",
    "Leheriya", "Micro or Ditsy", "Military", "Mirror Work", "Monochrome",
    "Mukash", "Nautical", "Ombre", "Paisley", "Patchwork", "Phulkari",
    "Pleated", "Polka Dots", "Rivets", "Ruffles", "Screen Print", "Sequins",
    "Sheer", "Shibori", "Shimmer", "Solid", "Stripes", "Tie Dye", "Tribal",
    "Utility", "Zardozi", "Zari"
], key=f"pattern_{rc}")

brand = st.text_input("Brand Name*", key=f"brand_{rc}")

fabric = st.multiselect("Fabric (choose all that apply)*", [
    "Acrylic", "Bamboo", "Cashmere", "Chiffon", "Corduroy", "Cotton", "Denim",
    "Elastane", "Fleece", "Georgette", "Hemp", "Leather", "Linen", "Lycocell",
    "Lycra", "Modal", "Nylon", "Polyester", "Rayon", "Satin", "Silk", "Spandex",
    "Suede", "Velvet", "Viscose", "Wool"
], key=f"fabric_{rc}")

# --------------------------
# File uploader (DO NOT assign st.session_state for this key)
uploaded_file_input = st.file_uploader(
    "Upload Product Image (.jpg required)*",
    type=["jpg"],
    key=f"uploaded_file_stable"
)

# Use stable reference in session_state
if uploaded_file_input is not None:
    st.session_state["uploaded_file_ref"] = uploaded_file_input

# Generate filename for image
img_filename = f"{st.session_state['p_id']}.jpg"

uploaded_file_to_save = st.session_state.get("uploaded_file_ref")
if uploaded_file_to_save is not None:
    img_path = os.path.join(project_root, "img", img_filename)
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    with open(img_path, "wb") as f:
        f.write(uploaded_file_to_save.getbuffer())
    st.session_state["img"] = img_filename
    st.success(f"Image saved as {img_filename}")

# --------------------------
# Multiselects continued
care = st.multiselect("Care (choose all that apply)*", [
    "Cold Water", "Cool Iron", "Do Not Bleach", "Dry Clean", "Hand Wash",
    "Iron on Reverse", "Line Dry", "Machine Wash", "No Fabric Softener", "Tumble Dry", "Warm Water",
    "Warm Iron"
], key=f"care_{rc}")

fit_options = [
    "Bodycon", "Bootcut", "Fitted", "Flare", "High-rise", "Loose", "Mid-rise",
    "Oversized", "Regular", "Relaxed", "Skinny", "Slim", "Straight", "Tapered",
    "Wide Leg"
]
fit = st.multiselect("Fit (choose all that apply)*", fit_options, key=f"fit_{rc}")

garment_closure = st.multiselect("Garment Closure (choose all that apply)*", [
    "Button(s)", "Drawstring", "Elasticated", "Front-open", "Hook & Eye",
    "Slip-on", "Snap", "Tie", "Toggle", "Zip"
], key=f"garment_closure_{rc}")

occasion_region = st.multiselect("Occasion & Region (for Dupattas) (choose all that apply)", [
    "Casual", "Daily", "Ethnic", "Festive", "Formal", "Fusion", "Maternity",
    "Outdoor", "Party", "Sports", "Traditional", "Western", "Work"
], key=f"occasion_region_{rc}")

# --------------------------
# Sync dynamic keys to main session_state before saving or generating
for key in dynamic_keys.keys():
    if key != "uploaded_file":
        st.session_state[key] = st.session_state.get(f"{key}_{rc}", dynamic_keys[key])
st.session_state["uploaded_file"] = st.session_state.get(f"uploaded_file_{rc}") or st.session_state.get("uploaded_file_ref", None)

# --------------------------
# Product Details HTML
def generate_product_details():
    label_buckets = {
        "Product Name": ["name"],
        "Product Type": ["products"],
        "Primary Colour": ["colour"],
        "Primary Pattern": ["pattern"],
        "Brand": ["brand"],
        "Fabric": ["fabric"],
        "Care": ["care"],
        "Fit": ["fit"],
        "Garment Closure": ["garment_closure"],
        "Occasion & Region (for Dupattas)": ["occasion_region"]
    }
    row = {
        "name": name,
        "products": ";".join(products),
        "colour": colour,
        "pattern": ";".join(pattern),
        "brand": brand,
        "fabric": ";".join(fabric),
        "care": ";".join(care),
        "fit": ";".join(fit),
        "garment_closure": ";".join(garment_closure),
        "occasion_region": ";".join(occasion_region)
    }
    lines = []
    for label, fields in label_buckets.items():
        values = []
        seen = set()
        for field in fields:
            if field in row and row[field]:
                for part in [x.strip() for x in row[field].split(";") if x.strip()]:
                    if part not in seen:
                        values.append(part)
                        seen.add(part)
        if values:
            safe_values = [html.escape(v) for v in values]
            lines.append(f"{label}: {', '.join(safe_values)}")
    return "<br>".join(lines)

if products or colour or brand or fabric:
    st.markdown("### Product Details Preview")
    st.markdown(f"""
    <div style="
        background-color: rgba(204, 51, 0, 0.75);
        border: 1px solid #4a3a8c;
        border-radius: 12px;
        padding: 18px 24px;
        font-size: 20px;
        line-height: 1.6;
        box-shadow: 0 0 8px rgba(0,0,0,0.3);
        width: fit-content;
        max-width: 80%;
        margin: 0 auto 0 0;
    ">
        {generate_product_details()}
    </div>
    """, unsafe_allow_html=True)

# --------------------------
# Description generation using Groq
def generate_description(products, colour, pattern, brand, fabric, fit, garment_closure, care, occasion_region):
    # Gather only non-empty attributes
    attributes = {
        "Product Type": ", ".join(products) if products else None,
        "Colour": colour if colour != "-- Select Colour --" else None,
        "Pattern": ", ".join(pattern) if pattern else None,
        "Brand": brand if brand.strip() else None,
        "Fabric": ", ".join(fabric) if fabric else None,
        "Fit": ", ".join(fit) if fit else None,
        "Garment Closure": ", ".join(garment_closure) if garment_closure else None,
        "Care Instructions": ", ".join(care) if care else None,
    }

    # Keep only attributes with values
    filled_attributes = {k: v for k, v in attributes.items() if v}

    # Start with your full prompt (static text, no optional attributes listed)
    prompt_text = f"""
    Write a short, catchy, marketing-friendly product description in plain text.
    Make it engaging and professional, as if for an online store, but not too long.
    ALWAYS include the field Product Name early in the description.
    Do NOT invent or hallucinate any attributes that are not explicitly provided.
    Do NOT include the occasion_region, occasion, or region in the description.
    Each description should have a unique opening that engages the reader. Focus on using varied sentence structures and adjectives for each description to make each description feel fresh by not repeating the same introduction for the last 3 descriptions.
    Vary the adjectives and sentence structures used.
    Combine the listed attributes naturally into flowing sentences.
    Use any care instructions selected by the user.
    Use correct British grammar.
    
    Attributes provided:
    Product Name: {name}
    """

    # Append Product Name (required)
    # prompt_text += f"Product Name: {name}\n"

    # Append only optional attributes that have values
    for k, v in filled_attributes.items():
        prompt_text += f"{k}: {v}\n"

    prompt_text += "\nOutput as a single, plain-text paragraph using correct British grammar."

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are an expert product description generator."},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error generating description: {e}"

    return ""  # fallback

# --------------------------
# Generate Description Button
st.markdown("<br>", unsafe_allow_html=True)
if st.button("Generate Description"):
    required_fields_filled = all([
        name.strip(),
        products,
        brand.strip(),
        fabric,
        st.session_state.get("uploaded_file_ref") is not None,  # use stable key
        colour != "-- Select Colour --",
        pattern,
        fit,
        garment_closure,
        care
    ])
    if not required_fields_filled:
        st.error("Please fill in all mandatory fields before generating the description.")
    else:
        with st.spinner("Generating awesome description. Please wait (this artistry will take a few seconds)..."):
            st.session_state['description'] = generate_description(
                tuple(products),
                colour,
                tuple(pattern),
                brand,
                tuple(fabric),
                tuple(fit),
                tuple(garment_closure),
                tuple(care),
                tuple(occasion_region)
            )

        st.markdown("### Product Description Preview")
        st.markdown(f"""
        <div style="
            background-color: rgba(204, 51, 0, 0.75);
            border: 1px solid #4a3a8c;
            border-radius: 12px;
            padding: 20px;
            font-size: 22px;
            line-height: 1.6;
            box-shadow: 0 0 10px rgba(0,0,0,0.4);
        ">
        {st.session_state['description']}
        </div>
        """, unsafe_allow_html=True)

        # Note about formatting
        st.markdown("""
        <p style="font-family: Arial, sans-serif; font-size: 18px; color: #FFFFFF; font-style: italic; line-height: 1.5;">
        <br>
        (Note: Description is plain-text and formatted using Arial for better readability. 
        If you make changes to this product before saving, please regenerate the description.)
        </p>
        """, unsafe_allow_html=True)

# --------------------------
# Initialize saving flag
if "saving" not in st.session_state:
    st.session_state["saving"] = False

# Ensure all dynamic keys exist as lists
for key in ["fit", "fabric", "pattern", "care", "garment_closure", "occasion_region"]:
    dynamic_key = f"{key}_{rc}"
    if dynamic_key not in st.session_state:
        st.session_state[dynamic_key] = []

# Sync only the dynamic-keyed inputs
st.session_state['fit'] = st.session_state.get(f"fit_{rc}", [])
st.session_state['fabric'] = st.session_state.get(f"fabric_{rc}", [])
st.session_state['pattern'] = st.session_state.get(f"pattern_{rc}", [])
st.session_state['care'] = st.session_state.get(f"care_{rc}", [])
st.session_state['garment_closure'] = st.session_state.get(f"garment_closure_{rc}", [])
st.session_state['occasion_region'] = st.session_state.get(f"occasion_region_{rc}", [])
st.session_state['products'] = st.session_state.get(f"products_{rc}", [])
st.session_state['name'] = st.session_state.get(f"name_{rc}", "").strip()
st.session_state['brand'] = st.session_state.get(f"brand_{rc}", "").strip()
st.session_state['price'] = st.session_state.get(f"price_str_{rc}", "")
st.session_state['colour'] = st.session_state.get(f"colour_{rc}", "")
st.session_state['uploaded_file'] = st.session_state.get("uploaded_file_ref", None)

# Force re-enable save button if no save is actually happening
if st.session_state.get("saving", True) and not st.session_state.get("description"):
    st.session_state["saving"] = False

# --------------------------
# Save Product Button
if st.button("Save Product", disabled=st.session_state.get("saving", False)):
    st.session_state["saving"] = True
    with st.spinner("Saving your product..."):

        missing_fields = []
        if not st.session_state['name'].strip(): missing_fields.append("Product Name")
        if not st.session_state['products']: missing_fields.append("Product Type")
        if not st.session_state['brand'].strip(): missing_fields.append("Brand Name")
        if not st.session_state['fabric']: missing_fields.append("Fabric")
        if st.session_state.get("uploaded_file_ref") is None: missing_fields.append("Product Image")  # stable key
        if st.session_state['colour'] == "-- Select Colour --": missing_fields.append("Colour")
        if not st.session_state['pattern']: missing_fields.append("Pattern")
        if not st.session_state['fit']: missing_fields.append("Fit")
        if not st.session_state['garment_closure']: missing_fields.append("Garment Closure")
        if not st.session_state['care']: missing_fields.append("Care")

        if missing_fields:
            st.error(f"Please fill in all mandatory fields: {', '.join(missing_fields)}")
            st.session_state["saving"] = False

        else:
            # Build row
            base_row = {
                "p_id": st.session_state["p_id"],
                "name": st.session_state['name'].strip(),
                "products": ", ".join(st.session_state['products']).lower(),
                "price": st.session_state.get('price', ""),
                "brand": st.session_state['brand'].strip().lower(),
                "theme_color_pattern": f"{st.session_state['colour'].lower()}, {', '.join(st.session_state['pattern']).lower()}",
                "theme_fit": ", ".join(st.session_state['fit']).lower(),
                "theme_fabric_care": f"{', '.join(st.session_state['fabric']).lower()}, {', '.join(st.session_state['care']).lower()}",
                "garment_closure": ", ".join(st.session_state['garment_closure']).lower(),
                "occasion": ", ".join(st.session_state['occasion_region']).lower(),
                "img": img_filename,
                "description_generated": st.session_state.get("description", "")
            }

            # Deduplicate merged buckets as before
            def dedup_buckets_row(row):
                fabric = set(map(str.strip, row['theme_fabric_care'].split(','))) if row['theme_fabric_care'] else set()
                colors = set(map(str.strip, row['theme_color_pattern'].split(','))) if row['theme_color_pattern'] else set()
                fit = set(map(str.strip, row['theme_fit'].split(','))) if row['theme_fit'] else set()
                colors -= fabric
                fit -= fabric | colors
                return pd.Series({
                    'theme_merged_fabric_care': ', '.join(sorted(fabric)),
                    'theme_merged_color_pattern': ', '.join(sorted(colors)),
                    'theme_merged_fit': ', '.join(sorted(fit))
                })
            
            merged_cols = dedup_buckets_row(base_row)
            base_row.update(merged_cols.to_dict())

            # Save formatted HTML
            label_buckets = {
                "Color and Pattern": ['theme_merged_color_pattern'],
                "Fabric and Care": ['theme_merged_fabric_care'],
                "Fit": ['theme_merged_fit'],
                "Garment Closure": ['garment_closure'],
                "Occasion & Region (Dupatta)": ['occasion']
            }
            
            def format_row_html(row, buckets):
                lines = []
                for label, fields in buckets.items():
                    values = []
                    seen = set()
                    for field in fields:
                        if field in row and row[field]:
                            for part in [x.strip() for x in str(row[field]).split(",") if x.strip()]:
                                if part.lower() not in seen:
                                    values.append(part)
                                    seen.add(part.lower())
                    if values:
                        lines.append(f"{label}: {', '.join(values)}")
                return "<br>".join(lines)

            base_row["formatted"] = format_row_html(base_row, label_buckets)
            base_row["description_generated"] = st.session_state.get("description", "")

            # Save to CSV
            df_final = pd.DataFrame([base_row]).reindex(columns=final_columns)
            df_final.to_csv(csv_file, mode="a", index=False, header=False)

            # -----------------------------
            # SESSION CSV LOGIC (added only)
            if "session_products" not in st.session_state:
                st.session_state["session_products"] = pd.DataFrame(columns=final_columns)

            st.session_state["session_products"] = pd.concat(
                [st.session_state["session_products"], df_final],
                ignore_index=True
            )

            csv_buffer = io.StringIO()
            st.session_state["session_products"].to_csv(csv_buffer, index=False)
            st.download_button(
                label="Download Saved Product to CSV",
                data=csv_buffer.getvalue().encode(),
                file_name="saved_product.csv",
                mime="text/csv"
            )
            # -----------------------------

            st.success(f"Product '{st.session_state.get('name', '')}' saved successfully with ID {st.session_state['p_id']}!  Product cannot be updated after saving.")

            # Reset for next product
            st.session_state['p_id'] = generate_new_pid()
            st.session_state['description'] = ""
            st.session_state["saving"] = False
    
# --------------------------
# Function to launch Streamlit with retries
def find_available_port(start=8501, end=8510):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    return None

# --------------------------
# Footer
st.markdown("---")
st.caption("Created by **Chris G.** | Generative AI-powered product description tool | Powered by Groq")