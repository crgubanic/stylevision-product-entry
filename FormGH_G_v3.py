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
    # Cache buster
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
            /* Make field labels larger and bold */
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
        # Fallback to gradient if image fails - COOL GRAYS
        st.markdown("""
        <style>
        [data-testid="stAppViewContainer"] > div:first-child {
            background: linear-gradient(180deg, #4a4a4a 0%, #6e6e6e 100%) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        return False

# --------------------------
# Call the background function BEFORE any other Streamlit elements
apply_background()

# --------------------------
# Add page title
st.title("StyleVision Product Entry")

# --------------------------
# Load API key from Streamlit secrets
groq_api_key = st.secrets["GROQ_API_KEY"]

# --------------------------
# # Initialize Groq client
client = Groq(api_key=groq_api_key)

# --------------------------
# CSV file to save entries (same filename as original)
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
# Generate unique Product ID (2-digit year + 8 numeric digits)
def generate_new_pid():
    year_prefix = datetime.datetime.now().strftime("%y")
    random_digits = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{year_prefix}_{random_digits}"

# --------------------------
# Initialize session_state variables & description
if "p_id" not in st.session_state:
    st.session_state["p_id"] = generate_new_pid()

if "saved_success" not in st.session_state:
    st.session_state["saved_success"] = False

if "saving" not in st.session_state:
    st.session_state["saving"] = False
    
if "description" not in st.session_state:
    st.session_state["description"] = ""
    
if "fit" not in st.session_state:
    st.session_state["fit"] = []

if "garment_closure" not in st.session_state:
    st.session_state["garment_closure"] = []

if "care" not in st.session_state:
    st.session_state["care"] = []

if "occasion_region" not in st.session_state:
    st.session_state["occasion_region"] = []

if "pattern" not in st.session_state:
    st.session_state["pattern"] = []

# --------------------------
# Detect if running with Streamlit
def is_running_with_streamlit():
    return "STREAMLIT_SERVER_RUN" in os.environ

# --------------------------
# Page Title and Instructions
#st.title("StyleVision Product Entry")
st.markdown("**Fields marked with * are mandatory**")

# --------------------------
# Clear description if any key field changes (safer)
watched_keys = ["name", "products", "brand", "fabric", "colour", "pattern", "fit", "garment_closure", "care", "occasion_region"]

# Initialize prev_values on first run to current values (prevents accidental clearing)
if "prev_values" not in st.session_state:
    #st.session_state["prev_values"] = {k: st.session_state.get(k) for k in watched_keys}
    st.session_state["prev_values"] = {}
    
for key in ["name", "products", "brand", "fabric", "colour", "pattern", "fit", "garment_closure", "care", "occasion_region"]:
    if st.session_state.get(key) != st.session_state["prev_values"].get(key):
        st.session_state.pop("description", None)
        st.session_state["prev_values"][key] = st.session_state.get(key)

# Only clear description if it exists AND a watched field actually changed from the last snapshot
if st.session_state.get("description"):
    changed = False
    for k in watched_keys:
        if st.session_state.get(k) != st.session_state["prev_values"].get(k):
            changed = True
            break
    if changed:
        # Remove description because a key changed AFTER description was generated
        st.session_state.pop("description", None)
        # Update snapshot to the new values
        st.session_state["prev_values"] = {k: st.session_state.get(k) for k in watched_keys}
        
# --------------------------        
# Display success message if flagged
if st.session_state["saved_success"]:
    st.success(f"Product '{st.session_state.get('name', '')}' saved successfully with ID {st.session_state['p_id']}! Please refresh the page to add another item.")
    st.session_state["saved_success"] = False

# --------------------------    
# Print current Product ID (console)
print(f"✅ Generated Product ID: {st.session_state['p_id']}")

# Clear Form button
if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0

if st.button("Clear Form"):
    st.session_state["reset_counter"] += 1
    # Delete any other session state keys that need reset
    for key in ["description_generated", "p_id"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()
    
# --------------------------
# Fields
name = st.text_input("Product Name*", key=f"name_{st.session_state['reset_counter']}")

products = st.multiselect("Product Type*", [
    "Blazer / Jacket", "Clothing Set", "Bralette", "Dress", "Dupatta",
    "Hoodie / Pullover", "Jeans", "Joggers", "Jumpsuit", "Kurta", "Kurti",
    "Lehenga", "Maternity", "Other", "Pants", "Saree", "Shawl", "Shirt",
    "Shorts", "Skirt", "Sweater", "Sweatshirt", "T-Shirt", "Top", "Vest"
    ],
    key=f"products_{st.session_state['reset_counter']}"
)

# --------------------------
# Entered as string to allow zero immediately after the decimal
price_str = st.text_input("Price (USD)*", key=f"price_str_{st.session_state['reset_counter']}")
price = None
if price_str:
    try:
        # Convert to float to validate, but store as string
        float(price_str)
        st.session_state['price'] = price_str
    except ValueError:
        st.error("Please enter a valid price, e.g., 808.08")
        st.session_state['price'] = ""
else:
    st.session_state['price'] = ""

colour = st.selectbox("Colour (Primary)*", [
    "-- Select Colour --", "Beige", "Black", "Blue", "Bronze", "Brown", "Burgandy",
    "Camel", "Champagne", "Charcoal", "Coffee", "Copper", "Coral", "Cream",
    "Fuschia", "Gold", "Green", "Grey", "Khaki", "Magenta", "Maroon",
    "Mauve", "Multi", "Navy", "Olive", "Orange", "Peach", "Pink", "Purple",
    "Other", "Red", "Rose Gold", "Rust", "Silver", "Tan", "Taupe", "Teal",
    "Turquoise", "Violet", "White", "Yellow"
    ],
    key=f"colour_{st.session_state['reset_counter']}"
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
    ],
    key=f"pattern_{st.session_state['reset_counter']}"
)

brand = st.text_input("Brand Name*", key=f"brand_{st.session_state['reset_counter']}")

fabric = st.multiselect("Fabric (choose all that apply)*", [
    "Acrylic", "Bamboo", "Cashmere", "Chiffon", "Corduroy", "Cotton", "Denim",
    "Elastane", "Fleece", "Georgette", "Hemp", "Leather", "Linen", "Lycocell",
    "Lycra", "Modal", "Nylon", "Polyester", "Rayon", "Satin", "Silk", "Spandex",
    "Suede", "Velvet", "Viscose", "Wool"
    ],
    key=f"fabric_{st.session_state['reset_counter']}"
)

# Use a fixed key for the uploader, independent of p_id
uploaded_file = st.file_uploader(
    "Upload Product Image (.jpg required)*",
    type=["jpg"],
    key=f"uploaded_file_{st.session_state['reset_counter']}"
)

# Auto-generate image filename
img_filename = f"{st.session_state['p_id']}.jpg"
st.write(f"Image Filename (auto-generated): {img_filename}")

# Handle file saving immediately on upload
if uploaded_file is not None:
    img_filename = f"{st.session_state['p_id']}.jpg"
    img_path = os.path.join(project_root, "img", img_filename)
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    with open(img_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.session_state["img"] = img_filename
    st.success(f"Image saved as {img_filename}")

# Fields cont'd
care = st.multiselect("Care (choose all that apply)*", [
    "Cold Water", "Cool Iron", "Do Not Bleach", "Dry Clean", "Hand Wash",
    "Iron on Reverse", "Line Dry", "Machine Wash", "No Fabric Softener", "Tumble Dry", "Warm Water",
    "Warm Iron"
    ],
    key="care"
)

fit = st.multiselect("Fit (choose all that apply)*", [
    "Bodycon", "Bootcut", "Fitted", "Flare", "High Rise", "Loose", "Mid Rise",
    "Oversized", "Regular", "Relaxed", "Skinny", "Slim", "Straight", "Tapered",
    "Wide Leg"
    ],
    key="fit"
)

garment_closure = st.multiselect("Garment Closure (choose all that apply)*", [
    "Button(s)", "Drawstring", "Elasticated", "Front-open", "Hook & Eye",
    "Slip-on", "Snap", "Tie", "Toggle", "Zip"
    ],
    key="garment_closure"
)

occasion_region = st.multiselect("Occasion & Region (for Dupattas) (choose all that apply)", [
    "Casual", "Daily", "Ethnic", "Festive", "Formal", "Fusion", "Maternity",
    "Outdoor", "Party", "Sports", "Traditional", "Western", "Work"
    ],
    key="occasion_region"
)

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
    <div style="font-size: 20px; line-height: 1.6;">
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
    Do NOT start every description the same way; vary your introduction styles and phrases.
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
if st.button("Generate Description"):
    required_fields_filled = all([
        name.strip(),
        products,
        brand.strip(),
        fabric,
        uploaded_file,
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
        <div style="font-size: 22px; line-height: 1.6;">
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

# --------------------------
# Save Product Button
if st.button("Save Product", disabled=st.session_state.get("saving", False)):
    st.session_state["saving"] = True
    with st.spinner("Saving your product..."):

        # Mandatory field check
        missing_fields = []
        if not st.session_state['name'].strip(): missing_fields.append("Product Name")
        if not st.session_state['products']: missing_fields.append("Product Type")
        if not st.session_state['brand'].strip(): missing_fields.append("Brand Name")
        if not st.session_state['fabric']: missing_fields.append("Fabric")
        if uploaded_file is None: missing_fields.append("Product Image")
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