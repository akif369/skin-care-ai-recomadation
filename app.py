from random import shuffle, choices
import streamlit as st
from skimage.feature import local_binary_pattern
from skimage import filters
import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import cv2
import numpy as np
import streamlit.components.v1 as components
from sklearn.cluster import KMeans
from PIL import Image
import sqlite3
from passlib.hash import bcrypt

# ------------------ Database Setup ------------------
def init_db():
    """Initialize database and create users table"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username, password):
    """Create new user with hashed password"""
    hashed = bcrypt.hash(password)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users VALUES (?, ?)', (username, hashed))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    finally:
        conn.close()

def verify_user(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    if result:
        return bcrypt.verify(password, result[0])
    return False

# ------------------ Authentication Views ------------------
def show_login():
    """Display login form"""
    st.title("🔐 Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if verify_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
    
    if st.button("Create new account"):
        st.session_state.page = "register"
        st.rerun()

def show_register():
    """Display registration form"""
    st.title("📝 Create Account")
    
    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")
        
        if submit:
            if password != confirm_password:
                st.error("Passwords do not match!")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters!")
            else:
                if create_user(username, password):
                    st.success("Account created successfully! Please login.")
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error("Username already exists!")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ------------------ Skin Analysis Functions ------------------
SKIN_TONES = {
    "Light": (200, 128, 128),
    "Medium": (150, 130, 140),
    "Olive": (130, 140, 150),
    "Tan": (110, 150, 160),
    "Dark": (80, 160, 170),
    "Deep": (50, 170, 180),
}

def classify_skin_tone(avg_color):
    """Classify skin tone based on LAB color values"""
    min_dist = float("inf")
    best_match = "Unknown"
    for tone, lab_values in SKIN_TONES.items():
        dist = np.linalg.norm(np.array(avg_color) - np.array(lab_values))
        if dist < min_dist:
            min_dist = dist
            best_match = tone
    return best_match

def extract_skin_region(image):
    """Detect face and extract skin pixels"""
    image = np.array(image)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100))

    if len(faces) == 0:
        return None
    
    x, y, w, h = faces[0]
    face_roi = image[y:y+h, x:x+w]
    lab = cv2.cvtColor(face_roi, cv2.COLOR_BGR2LAB)
    
    l, a, b = cv2.split(lab)
    skin_mask = (a > 120) & (b > 130)
    skin_pixels = lab[skin_mask]

    return skin_pixels if len(skin_pixels) > 0 else None

def detect_skin_tone(image):
    """Main function to detect skin tone from an image"""
    skin_pixels = extract_skin_region(image)
    if skin_pixels is None:
        return None
    
    kmeans = KMeans(n_clusters=1, random_state=42)
    kmeans.fit(skin_pixels)
    avg_color = kmeans.cluster_centers_[0]
    return classify_skin_tone(avg_color)

def detect_acne_severity(image):
    """Acne detection with normalized density calculation"""
    try:
        if isinstance(image, Image.Image):
            image = np.array(image)
            
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
            
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        blur1 = cv2.GaussianBlur(filtered, (5,5), 0)
        blur2 = cv2.GaussianBlur(filtered, (9,9), 0)
        dog = blur1 - blur2
        
        thresh = cv2.adaptiveThreshold(dog, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 11, 2)
        
        kernel = np.ones((3,3), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)
        
        spot_area = np.sum(cleaned)/255
        total_area = gray.shape[0] * gray.shape[1]
        normalized_density = (spot_area / total_area) * 100
        
        if normalized_density < 10: return 0
        elif normalized_density < 40: return 1
        elif normalized_density < 55: return 2
        elif normalized_density < 75: return 3
        elif normalized_density < 90: return 4
        else: return 5
    except Exception as e:
        print(f"Acne detection error: {e}")
        return 0

# ------------------ Product Recommendations ------------------
def scrape_products(query, limit=3):
    all_products = []
    
    # 1. Nykaa Scraper
    def scrape_nykaa(query, limit):
        search_url = f"https://www.nykaa.com/search/result/?q={query.replace(' ', '%20')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nykaa.com/"
        }
        
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            product_list = []
            
            for product in soup.find_all("div", class_="css-d5z3ro", limit=limit):
                try:
                    name = product.find("div", class_="css-xrzmfa").text.strip()
                    price = product.find("span", class_="css-111z9ua").text.strip()
                    link = "https://www.nykaa.com" + product.find("a")["href"]
                    image = product.find("img")["src"] if product.find("img") else ""
                    product_list.append({
                        "name": name, 
                        "price": price, 
                        "link": link, 
                        "image": image,
                        "source": "Nykaa",
                        "query": query.lower()
                    })
                except (AttributeError, KeyError):
                    continue
            
            return product_list
        except Exception as e:
            print(f"Error scraping Nykaa: {e}")
            return []

    # 2. Purplle Scraper
    def scrape_purplle(query, limit):
        search_url = f"https://www.purplle.com/search?search={query.replace(' ', '+')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            product_list = []
            
            for product in soup.find_all("div", class_="product-item", limit=limit):
                try:
                    name = product.find("div", class_="product-name").text.strip()
                    price = product.find("span", class_="product-price").text.strip()
                    link = "https://www.purplle.com" + product.find("a")["href"]
                    image = product.find("img")["data-src"] if product.find("img") else ""
                    product_list.append({
                        "name": name, 
                        "price": price, 
                        "link": link, 
                        "image": image,
                        "source": "Purplle",
                        "query": query.lower()
                    })
                except (AttributeError, KeyError):
                    continue
            
            return product_list
        except Exception as e:
            print(f"Error scraping Purplle: {e}")
            return []

    # Scrape from all websites
    per_site_limit = max(1, limit // 2)
    all_products.extend(scrape_nykaa(query, per_site_limit))
    all_products.extend(scrape_purplle(query, per_site_limit))
    
    return all_products[:limit]

   

def get_routine(skin_type):
    routines = {
        "Normal": {
            "Cleanser": ["Gentle Milk Cleanser", "pH Balanced Foaming Cleanser"],
            "Toner": ["Hydrating Toner with Hyaluronic Acid", "Rose Water Toner"],
            "Moisturizer": ["Lightweight Gel Cream", "Ceramide Moisturizer"],
            "Serum": ["Vitamin C Serum", "Niacinamide Serum"],
            "Sunscreen": ["SPF 50 PA+++ Sunscreen", "Invisible Sunscreen Gel"]
        },
        "Dry": {
            "Cleanser": ["Creamy Hydrating Cleanser", "Oil-based Cleanser"],
            "Serum": ["Hyaluronic Acid Serum", "Squalane Serum"],
            "Moisturizer": ["Rich Cream with Shea Butter", "Barrier Repair Cream"],
            "Treatment": ["Facial Oil Blend", "Sleeping Mask"],
            "Sunscreen": ["SPF 50 Cream Sunscreen", "Moisturizing Sunscreen"]
        },
        "Oily": {
            "Cleanser": ["Salicylic Acid Cleanser", "Charcoal Detox Cleanser"],
            "Toner": ["Witch Hazel Toner", "Tea Tree Toner"],
            "Moisturizer": ["Oil-Free Gel Moisturizer", "Sebum Control Cream"],
            "Serum": ["Niacinamide + Zinc Serum", "Retinol Serum"],
            "Sunscreen": ["Matte Finish Sunscreen", "Oil-Control Sunscreen"]
        },
        "Combination": {
            "Cleanser": ["Balancing Gel Cleanser", "Micellar Gel Wash"],
            "Toner": ["pH Balancing Toner", "Lotion Toner"],
            "Moisturizer": ["Dual Hydration Cream", "Zone-Control Moisturizer"],
            "Serum": ["Hyaluronic Acid + Niacinamide", "Snail Mucin Essence"],
            "Sunscreen": ["Lightweight Fluid Sunscreen", "Cream-Gel Hybrid Sunscreen"]
        },
        "Sensitive": {
            "Cleanser": ["Fragrance-Free Cleanser", "Thermal Water Cleanser"],
            "Soother": ["Aloe Vera Gel", "Centella Asiatica Cream"],
            "Moisturizer": ["Ceramide Moisturizer", "Cicaplast Baume"],
            "Treatment": ["Barrier Support Serum", "Redness Relief Essence"],
            "Sunscreen": ["Mineral Zinc Oxide Sunscreen", "Physical Sunscreen"]
        }
    }
    return routines.get(skin_type, {})


def calculate_product_weights(products, skin_concerns, acne_level, sensitivity):
    weighted_products = []
    for product in products:
        weight = 1
        
        # Base weight from query match
        if any(concern.lower() in product['query'] for concern in skin_concerns):
            weight += 3
        
        # Boost for exact matches
        name_lower = product['name'].lower()
        if any(concern.lower() in name_lower for concern in skin_concerns):
            weight += 5
            
        # Acne relevance
        if acne_level >= 3 and any(term in name_lower for term in ['acne', 'bha', 'salicylic']):
            weight += acne_level * 2
            
        # Sensitivity relevance
        if sensitivity >= 3 and any(term in name_lower for term in ['calm', 'sensitive', 'fragrance-free']):
            weight += sensitivity * 2
            
        weighted_products.append((product, weight))
    
    return weighted_products

def get_recommendations(skin_concerns, routine_steps, skin_tone, acne_level, texture, sensitivity):
    all_products = []
    
    # Get base routine products
    for step, products in routine_steps.items():
        for product_type in products:
            all_products.extend(scrape_products(product_type, limit=2))
    
    # Add specialized queries
    specialized_queries = []
    if acne_level >= 2:
        specialized_queries.extend([
            f"{acne_level}% BHA Exfoliant",
            "Acne Treatment Serum",
            "Non-Comedogenic Moisturizer"
        ])
    
    if sensitivity >= 2:
        specialized_queries.extend([
            "Fragrance-Free Cream",
            "Hypoallergenic Serum",
            "Soothing Repair Treatment"
        ])
    
    # Skin tone specific products
    if skin_tone in ["Dark", "Deep"]:
        specialized_queries.extend([
            "Dark Spot Corrector",
            "Hyperpigmentation Treatment",
            "Even Tone Serum"
        ])
    elif skin_tone in ["Light", "Medium"]:
        specialized_queries.extend([
            "Brightening Serum",
            "Vitamin C Treatment",
            "Glow Boosting Cream"
        ])
    
    for query in specialized_queries:
        all_products.extend(scrape_products(query, limit=2))
    
    # Calculate weights and randomize
    weighted_products = calculate_product_weights(all_products, skin_concerns, acne_level, sensitivity)
    
    if not weighted_products:
        return []
    
    # Separate products and weights
    products, weights = zip(*weighted_products)
    
    # Select products with weighted randomness
    selected_products = []
    remaining_products = list(products)
    remaining_weights = list(weights)
    
    # Ensure we get diverse categories
    category_counts = defaultdict(int)
    max_per_category = 4
    
    while len(selected_products) < 15 and remaining_products:
        # Choose with weights
        chosen_idx = choices(range(len(remaining_products)), weights=remaining_weights, k=1)[0]
        chosen_product = remaining_products.pop(chosen_idx)
        remaining_weights.pop(chosen_idx)
        
        # Determine category
        category = "other"
        name_lower = chosen_product['name'].lower()
        if any(word in name_lower for word in ['cleanse', 'wash']):
            category = "cleanser"
        elif any(word in name_lower for word in ['serum', 'treatment', 'acid']):
            category = "treatment"
        elif any(word in name_lower for word in ['moisturiz', 'cream', 'lotion']):
            category = "moisturizer"
        elif 'sunscreen' in name_lower or 'spf' in name_lower:
            category = "sunscreen"
        
        # Add if category not full
        if category_counts[category] < max_per_category:
            category_counts[category] += 1
            selected_products.append(chosen_product)
    
    # Final shuffle
    shuffle(selected_products)
    return selected_products[:15]

# ------------------ Main Application ------------------
def main_app():
     # Header with title and logout button
    header_col1, header_col2 = st.columns([4, 1])
    with header_col1:
        st.title("💖 Personalized Skin Care Routine")
    with header_col2:
        st.write("")  # Vertical spacer
        st.write("")  # Vertical spacer
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

    st.markdown(f"Welcome, {st.session_state.username}! Upload a selfie or take a picture to begin.")

    # Initialize session state
    if 'skin_tone' not in st.session_state:
        st.session_state.skin_tone = "Medium"
    if 'acne_level' not in st.session_state:
        st.session_state.acne_level = 2
    if 'image_source' not in st.session_state:
        st.session_state.image_source = None

    # Image upload
    uploaded_file = st.file_uploader("Upload a selfie", type=["jpg", "jpeg", "png"], key="file_uploader")
    camera_image = st.camera_input("Or take a picture", key="camera_input")
    image = uploaded_file if uploaded_file else camera_image

    if image is not None:
        try:
            img = Image.open(image)
            st.image(img, caption='Uploaded Image.', use_column_width=True)
            
            detected_tone = detect_skin_tone(img)
            if detected_tone:
                st.session_state.skin_tone = detected_tone
                st.success(f"Detected skin tone: {detected_tone}")
            else:
                st.warning("Could not detect face. Please try another photo.")
            
            acne_level = detect_acne_severity(img)
            st.session_state.acne_level = acne_level
            st.info(f"Detected acne severity: {acne_level}/5")

        except Exception as e:
            st.error(f"Error processing image: {str(e)}")

    # Sidebar form
    with st.sidebar:
        st.header("Your Skin Profile")
        skin_type = st.radio("Skin Type:", ("Normal", "Dry", "Oily", "Combination", "Sensitive"))
        
        skin_tone = st.selectbox(
            "Skin Tone:",
            ("Light", "Medium", "Olive", "Tan", "Dark", "Deep"),
            index=["Light", "Medium", "Olive", "Tan", "Dark", "Deep"].index(st.session_state.skin_tone)
        )
        
        acne_level = st.slider("Acne Level (0-5):", 0, 5, st.session_state.acne_level)
        texture = st.selectbox("Skin Texture:", ("Smooth", "Rough", "Bumpy", "Uneven"))
        sensitivity = st.slider("Sensitivity (0-5):", 0, 5, 2)
        skin_concerns = st.multiselect(
            "Skin Concerns:",
            ["Acne", "Aging", "Dryness", "Redness", "Hyperpigmentation"]
        )

    

    if st.button("Get My Skin Care Routine"):
        with st.spinner('Finding the best products for your skin...'):
            routine_steps = get_routine(skin_type)
            products = get_recommendations(
                skin_concerns, routine_steps, skin_tone, 
                acne_level, texture, sensitivity
            )

            st.subheader("🌿 Your Recommended Routine")
            for step, items in routine_steps.items():
                st.markdown(f"**{step}:** {', '.join(items)}")

            st.subheader("✨ Recommended Products")
            if products:
                cols = st.columns(3)
                for idx, product in enumerate(products):
                    with cols[idx % 3]:
                        st.markdown(f"""
                        <div style="border:1px solid #e0e0e0; border-radius:8px; padding:15px; margin-bottom:20px; text-align:center;">
                            <img src="{product['image']}" style="max-height:150px; width:auto; border-radius:4px; margin-bottom:10px;">
                            <h4 style="margin:5px 0; font-size:16px;">{product['name']}</h4>
                            <p style="color:#f43397; font-weight:bold; margin:5px 0;">{product['price']}</p>
                            <a href="{product['link']}" target="_blank" style="background:#f43397; color:white; padding:8px 12px; border-radius:4px; text-decoration:none;">
                                View Product
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.warning("No products found. Try adjusting your filters.")

# ------------------ Main Function ------------------
def main():
    init_db()
    
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'page' not in st.session_state:
        st.session_state.page = "login"
    
    if not st.session_state.logged_in:
        if st.session_state.page == "login":
            show_login()
        else:
            show_register()
        return
    
    main_app()

if __name__ == "__main__":
    main()
