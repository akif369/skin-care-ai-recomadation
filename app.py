from random import shuffle, choices
import streamlit as st
import requests
from bs4 import BeautifulSoup
from collections import defaultdict

# Function to scrape skincare products from multiple websites
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

# Function to get skincare routine based on skin type
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

def main():
    st.title("💖 Personalized Skin Care Routine")
    st.markdown("Upload a selfie or take a picture to get personalized skin care recommendations.")

    uploaded_file = st.file_uploader("Upload a selfie", type=["jpg", "jpeg", "png"])
    camera_image = st.camera_input("Or take a picture")
    
    image = uploaded_file if uploaded_file else camera_image
    
    if image is not None:
        st.image(image, caption='Uploaded Image.', use_column_width=True)

    st.markdown("Get product recommendations tailored to your skin needs")
    
    with st.sidebar:
        st.header("Your Skin Profile")
        skin_type = st.radio("Skin Type:", ("Normal", "Dry", "Oily", "Combination", "Sensitive"))
        skin_tone = st.selectbox("Skin Tone:", ("Light", "Medium", "Olive", "Tan", "Dark", "Deep"))
        acne_level = st.slider("Acne Level (0-5):", 0, 5, 1)
        texture = st.selectbox("Skin Texture:", ("Smooth", "Rough", "Bumpy", "Uneven"))
        sensitivity = st.slider("Sensitivity (0-5):", 0, 5, 1)
        skin_concerns = st.multiselect("Main Concerns:", 
                                     ["Acne", "Aging", "Dryness", "Redness", 
                                      "Hyperpigmentation", "Pores", "Dullness"])
    
    if st.button("Get Recommendations"):
        with st.spinner('Finding the best products for your skin...'):
            routine_steps = get_routine(skin_type)
            products = get_recommendations(skin_concerns, routine_steps, skin_tone, acne_level, texture, sensitivity)
            
            st.subheader("✨ Your Personalized Routine")
            for step, items in routine_steps.items():
                st.markdown(f"**{step}:** {', '.join(items)}")
            
            st.subheader("🛍 Recommended Products")
            if not products:
                st.warning("Couldn't find matching products. Try adjusting your filters.")
            else:
                cols = st.columns(3)
                for idx, product in enumerate(products):
                    with cols[idx % 3]:
                        st.image(product.get('image', ''), width=150)
                        st.markdown(f"**{product['name']}**")
                        st.markdown(f"*{product['price']}*")
                        st.markdown(f"*{product['source']}*")
                        st.markdown(f"[View Product]({product['link']})", unsafe_allow_html=True)
                        st.markdown("---")

if __name__ == "__main__":
    main()