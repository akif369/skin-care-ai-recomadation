import streamlit as st
import requests
from bs4 import BeautifulSoup

# Function to scrape skincare products from Nykaa
def scrape_products(query):
    search_url = f"https://www.nykaa.com/search/result/?q={query.replace(' ', '%20')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nykaa.com/"
    }
    response = requests.get(search_url, headers=headers)
    
    if response.status_code != 200:
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    product_list = []
    
    for product in soup.find_all("div", class_="css-d5z3ro", limit=3):
        name = product.find("div", class_="css-xrzmfa").text.strip()
        price = product.find("span", class_="css-111z9ua").text.strip()
        link = "https://www.nykaa.com" + product.find("a")["href"]
        image = product.find("img")["src"] if product.find("img") else ""
    
        product_list.append({"name": name, "price": price, "link": link, "image": image})
    
    return product_list

# Function to get skincare routine based on skin type
def get_routine(skin_type):
    routines = {
        "Normal": ["Cleanser", "Toner", "Moisturizer", "Serum", "Sunscreen"],
        "Dry": ["Hydrating Cleanser", "Hydrating Toner", "Rich Moisturizer", "Facial Oil", "Sunscreen"],
        "Oily": ["Oil-control Cleanser", "Mattifying Toner", "Lightweight Moisturizer", "Serum", "Sunscreen"],
        "Combination": ["Balancing Cleanser", "Hydrating Toner", "Lightweight Moisturizer", "Targeted Serum", "Sunscreen"]
    }
    return routines.get(skin_type, [])

# Function to get recommended skincare products based on concerns
def get_recommendations(skin_concerns, routine_steps):
    recommended_products = []
    
    concern_products = {
        "Acne": "Salicylic Acid Cleanser",
        "Aging": "Retinol Serum",
        "Sensitive": "Hypoallergenic Moisturizer",
        "Dryness": "Hydrating Moisturizer"
    }
    
    for concern in skin_concerns:
        if concern in concern_products:
            recommended_products += scrape_products(concern_products[concern])
    
    if not recommended_products:
        for step in routine_steps:
            recommended_products += scrape_products(step)
    
    return recommended_products

# Main Streamlit app
def main():
    st.title("💖 Personalized Skin Care Routine")
    st.markdown("Upload a selfie to get personalized skin care recommendations.")

    uploaded_file = st.file_uploader("Upload a selfie", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption='Uploaded Image.', use_column_width=True)

        skin_type = st.radio("Select your skin type:", ("Normal", "Dry", "Oily", "Combination"))
        skin_concerns = st.multiselect("Select your skin concerns:", ("Acne", "Aging", "Sensitive", "Dryness"))

        if st.button("Get My Skin Care Routine"):
            routine_steps = get_routine(skin_type)
            recommended_products = get_recommendations(skin_concerns, routine_steps)

            st.subheader("🌿 Your Recommended Skin Care Routine:")
            st.write(", ".join(routine_steps))

            st.subheader("🛍 Recommended Products:")
            if recommended_products:
                st.markdown("""
                <style>
                    .product-container {
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                        gap: 20px;
                        
                        justify-content: center;
                        align-items: start;
                    }
                    .product-card {
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                        padding: 15px;
                        text-align: center;
                        margin-bottom:20px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                        transition: transform 0.3s ease;
                        background: white;
                        max-width: 280px;
                        width: 100%;
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                        overflow: hidden;
                    }
                    .product-card:hover {
                        transform: scale(1.05);
                    }
                    .product-image {
                        height: 180px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin-bottom: 12px;
                        overflow: hidden;
                        background: #f9f9f9;
                        border-radius: 6px;
                    }
                    .product-image img {
                        max-width: 100%;
                        max-height: 100%;
                        object-fit: contain;
                    }
                    h4 {
                        font-size: 16px;
                        color: #333;
                        font-weight: 600;
                        min-height: 40px;
                        display: -webkit-box;
                        -webkit-line-clamp: 2;
                        -webkit-box-orient: vertical;
                        overflow: hidden;
                    }
                    .price {
                        font-size: 18px;
                        color: #f43397;
                        font-weight: 700;
                    }
                    .view-btn {
                        margin-top: 12px;
                        padding: 8px 16px;
                        background: #f43397;
                        color: white;
                        border-radius: 4px;
                        font-size: 14px;
                        font-weight: 600;
                        display: inline-block;
                        cursor: pointer;
                        transition: background 0.3s ease;
                    }
                    .view-btn:hover {
                        background: #c9277a;
                    }
                </style>
                """, unsafe_allow_html=True)

                st.markdown('<div class="product-container">', unsafe_allow_html=True)
                for product in recommended_products:
                    st.markdown(f'<div class="product-card">\n<a href="{product["link"]}" target="_blank">\n<div class="product-image">\n<img src="{product["image"]}" alt="{product["name"]}"></div>\n<h4>{product["name"]}</h4>\n<p class="price">{product["price"]}</p>\n<div class="view-btn">View Product</div></a></div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.write("No products found.")

if __name__ == "__main__":
    main()
