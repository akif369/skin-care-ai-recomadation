Sure! Here's your **README.md** formatted nicely for your Skincare Recommender System project:

---

# Skincare Recommender System Based on Skin Problem Using Content-Based Filtering

## Overview

Nowadays, skincare is becoming one of the most essential parts of daily life. The skincare product market has grown rapidly and is increasing year by year.  
However, the large number of available options makes it difficult for users to choose products that best suit their facial needs.  

This project aims to solve that problem by creating a **Skincare Recommender System** based on **facial skin problems**.  
It uses **Content-Based Filtering** (without any rating data) to recommend products using **cosine similarity** and **TF-IDF** to find feature similarities.

✅ Users receive product recommendations based on selected keywords and similar products.  
✅ The system was deployed using **Streamlit**.

---

## Dataset

The dataset was independently scraped from various skincare product websites.

| Feature Name      | Description                                                             |
| ----------------- | ----------------------------------------------------------------------- |
| `product_href`     | Product URL link                                                        |
| `product_name`     | Product name                                                            |
| `product_type`     | Type of product (Facial wash, Toner, Serum, Moisturizer, Sunscreen)      |
| `brand`            | Product brand                                                           |
| `notable_effects`  | Benefits (e.g., brightening, anti-aging)                                 |
| `skin_type`        | Suitable skin type (Normal, Dry, Oily, Combination, Sensitive)          |
| `price`            | Product price (in IDR Rp)                                                |
| `description`      | Product description                                                      |
| `picture_src`      | Product image URL link                                                  |

- 📦 **Total products**: 1224
- 🚫 **Duplicates**: 14 rows (to be removed)
- 🧹 **Clean Data**: No null values

---

## Exploratory Data Analysis (EDA)

### 1. Top Brands With Most Products
- **Top brand**: SOMETHINC (offers the most product variations across the 5 basic skincare types).

### 2. Skin Care Product Types
- Only **basic skincare** products are included:
  - Facial Wash
  - Toner
  - Serum
  - Moisturizer
  - Sunscreen

(📈 Pie chart here)

### 3. Suitable Skin Types
- Products are suitable for various skin types:
  - Normal
  - Dry
  - Oily
  - Combination
  - Sensitive

(📈 Bar graph here)

### 4. Notable Effects
- Top 5 notable effects found:
  - Pore Care
  - Brightening
  - Anti-Aging
  - Oil Control
  - Acne Treatment

(📈 Bar graph here)

---

## How the Recommendation Works

- **Preprocessing**: TF-IDF is used to vectorize the `notable_effects`, `skin_type`, and `description` features.
- **Similarity Measure**: Cosine similarity calculates the similarity between products.
- **Content-Based Filtering**: The system recommends products based on the user's keyword selection and finds similar products.

---

## App Deployment

The project is deployed using **Streamlit**.

🔗 [Try the App Here](https://skin-care-recommender-system-141.streamlit.app/)

### App Preview

| Home Page | Recommendation Results | Product Details |
| --------- | ----------------------- | --------------- |
| ![Home](image1.png) | ![Recommendation](image2.png) | ![Product](image3.png) |

---

## How to Run Locally

```bash
# 1. Clone the repository
git clone https://github.com/your-username/skincare-recommender.git
cd skincare-recommender

# 2. Create and activate a virtual environment (optional but recommended)
python -m venv env
# For Windows
env\Scripts\activate
# For Mac/Linux
source env/bin/activate

# 3. Install the required packages
pip install -r requirements.txt

# 4. Run the Streamlit app
streamlit run app.py
```

---

## Thank You! 💖

Feel free to give feedback or contribute to this project!

---

Would you also like me to help you generate a sample `requirements.txt` for this project too (with libraries like `pandas`, `scikit-learn`, `streamlit`, etc.)? 🚀  
Let me know!
