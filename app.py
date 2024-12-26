import streamlit as st
import sqlite3
import pandas as pd
import random
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from difflib import get_close_matches
import requests
import datetime
from decimal import Decimal

# Function to add background image
def add_bg_image(image_url):
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url({image_url});
            background-size: cover; 
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Function to add custom text styles
def add_custom_text_styles():
    st.markdown(   
        """
        <style>
        h1 {
            color: black;  
            font-family: 'Arial', sans-serif;          
            font-size: 50px;
            text-align: center;
            letter-spacing: 2px;
        }
        h2 {
            color: #2E8B57;
            font-family: 'Verdana', sans-serif;
            font-size: 35px;
            text-align: left;
        }
        h3 {
            color: #4682B4;
            font-weight: bold;
            font-size: 20px;
        }
        p {
            font-size: 18px;
            color: #333333;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# Database connection and setup
def create_connection():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    return conn

def create_user_table():
    conn = create_connection()
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE,
                            password TEXT
                        );''')
        conn.execute('''CREATE TABLE IF NOT EXISTS cart (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT,
                            product_id TEXT,
                            product_name TEXT,
                            price REAL,
                            image_url TEXT,
                            FOREIGN KEY (username) REFERENCES users (username)
                        );''')
        conn.execute('''CREATE TABLE IF NOT EXISTS wishlist (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT,
                            product_id TEXT,
                            product_name TEXT,
                            image_url TEXT,
                            FOREIGN KEY (username) REFERENCES users (username)
                        );''')
    conn.close()

# Add a new user to the database
def add_user(username, password):
    conn = create_connection()
    try:
        with conn:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    except sqlite3.IntegrityError:
        st.error("Username already exists!")
    conn.close()

# Check if the user exists in the database
def login_user(username, password):
    conn = create_connection()
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))
        user = cursor.fetchone()
    conn.close()
    return user is not None

# Check if the username is already taken
def is_user_exists(username):
    conn = create_connection()
    with conn:
        cursor = conn.execute('SELECT * FROM users WHERE username=?', (username,))
        exists = cursor.fetchone() is not None
    conn.close()
    return exists

# Utility function to truncate text
def truncate(text, length):
    if len(text) > length:
        return text[:length] + "..."
    else:
        return text

# Load merged data from CSV files
def load_data():
    # Load data from CSV files
    cleans_data = pd.read_csv('cleans_data.csv')
    styles_data = pd.read_csv('styles.csv')

    # Strip whitespace from column names
    cleans_columns = ['ID', 'Product Id', 'Category', 'Name', 'Brand', 'Rating', 'ReviewCount', 'Description', 'ImageURL', 'Tags', 'Gender']
    styles_columns = ['Product Id', 'baseColour', 'gender', 'masterCategory']

# Merge the datasets on 'Product Id'
    merged_data = pd.merge(cleans_data[cleans_columns], styles_data[styles_columns], on='Product Id', how='inner')

    # Rename columns if necessary
    merged_data.rename(columns={
        'Product Brand': 'Brand',
        'Product Rating': 'Rating',
        'Product Image Url': 'ImageURL'
    }, inplace=True)

    return merged_data  # Return the merged DataFrame

# Function to get product ID by name
def get_product_id_by_name(data, product_name):
    # Find the product with the matching name
    matches = data[data['Name'] == product_name]
    
    # Return the 'Product Id' instead of 'ProductId'
    if not matches.empty:
        return matches['Product Id'].values[0]
    else:
        return None

# Content-based recommendations
def content_based_recommendations(data, product_id, top_n=5):
    tfidf_vectorizer = TfidfVectorizer(stop_words='english')
    data['Description'] = data['Description'].fillna('')  # Handle missing descriptions
    tfidf_matrix = tfidf_vectorizer.fit_transform(data['Description'])
    
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
    
    indices = pd.Series(data.index, index=data['Product Id']).drop_duplicates()
    idx = indices[product_id]

    sim_scores = list(enumerate(cosine_sim[idx]))
    sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
    sim_scores = sim_scores[1:top_n + 1]
    product_indices = [i[0] for i in sim_scores]

    # Update with correct column names
    return data.iloc[product_indices][['Product Id', 'Name', 'Brand', 'baseColour', 'Gender', 'Rating', 'ImageURL']]

# Add to cart function
# Add to wishlist function
def add_to_wishlist(product_id, product_name, image_url):
    conn = create_connection()
    with conn:
        conn.execute('INSERT INTO wishlist (username, product_id, product_name, image_url) VALUES (?, ?, ?, ?)', 
                     (st.session_state["username"], product_id, product_name, image_url))
    conn.close()
    st.success(f"{product_name} has been added to your wishlist!")

# Signup function
def signup():
    add_bg_image('https://t4.ftcdn.net/jpg/06/34/09/69/360_F_634096945_nT013AXOaokOmXXU0mRlfSLmnSbbmZXw.jpg')
    add_custom_text_styles()
    st.header("Create an Account") 
    new_user = st.text_input("Username")
    new_password = st.text_input("Password", type="password")
    
    if st.button("Signup"):
        if is_user_exists(new_user):
            st.error("Username already exists!")
        else:
            add_user(new_user, new_password)
            st.success(f"Signup successful for {new_user}!")
            st.info("Go to the login page to log in.") 

# Login function
def login():
    add_bg_image('https://t4.ftcdn.net/jpg/06/34/09/69/360_F_634096945_nT013AXOaokOmXXU0mRlfSLmnSbbmZXw.jpg')
    add_custom_text_styles()
    st.header("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if login_user(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

def store_cart_in_db(username):
    conn = create_connection()
    with conn:
        conn.execute('DELETE FROM cart WHERE username=?', (username,))  # Clear existing items
        for item in st.session_state['cart']:
            conn.execute('INSERT INTO cart (username, product_id, product_name, price, image_url) VALUES (?, ?, ?, ?, ?)', 
                         (username, item['Product ID'], item['Product Name'], item['Price'], item['Image URL']))
    conn.close()

# Function to load cart from the database
def load_cart_from_db(username):
    conn = create_connection()
    with conn:
        cursor = conn.execute('SELECT product_id, product_name, price, image_url FROM cart WHERE username=?', (username,))
        cart_items = cursor.fetchall()
    conn.close()
    return cart_items
def show_cart_page():
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    st.title("🛒 Your Cart 🛒")

    conn = create_connection()
    if conn:
        if st.session_state.get('logged_in', False):
            # Fetch cart items from the database
            cursor = conn.execute('SELECT product_id, product_name, image_url, price FROM cart WHERE username=?',
                                  (st.session_state["username"],))
            cart_items = cursor.fetchall()

            if cart_items:
                total_price = 0  # Variable to keep track of total price

                for item in cart_items:
                    product_id, product_name, image_url, price = item

                    # Display product details
                    st.image(image_url, width=150)
                    st.subheader(product_name)
                    price = random.randint(150, 500)
                    st.write(f"Price: ₹{int(price)}")
                    # Calculate total price for the cart
                    total_price += price

                    # Button to remove item from cart
                    if st.button("Remove from Cart", key=f"remove_{product_id}"):
                        with conn:
                            conn.execute('DELETE FROM cart WHERE username=? AND product_id=?',
                                         (st.session_state["username"], product_id))
                        st.success(f"Removed {product_name} from the cart.")
                          # Refresh to show updated cart
                        st.rerun()

                # Display the overall total price for the cart
                st.subheader(f"Total Price for Your Cart: ₹{int(total_price)}")

                # Checkout button
                if st.button("Proceed to Checkout"):
                    # Remove all items from the cart after checkout
                    with conn:
                        conn.execute('DELETE FROM cart WHERE username=?', (st.session_state["username"],))
                    
                    # Optionally, save order details in another table (e.g., "orders")
                    st.success("Proceeding to Checkout... Your cart has been cleared.")
                    st.session_state['show_checkout_page'] = True  # Redirect to checkout
                    st.rerun()  # Refresh the page to reflect cart clearance
            else:
                st.write("Your cart is empty.")
        else:
            st.warning("Please log in to view your cart.")

        conn.close()  # Close the connection after usage
    else:
        st.error("Could not connect to the database.")

def remove_from_cart(product_id):
    conn = create_connection()
    with conn:
        conn.execute('DELETE FROM cart WHERE username=? AND product_id=?', 
                     (st.session_state["username"], product_id))
    conn.close()
    
    # Update session state
    st.session_state['cart'] = [item for item in st.session_state['cart'] if item['Product ID'] != product_id]

def update_cart_quantity(product_id):
    """Function to update the quantity in the cart."""
    for item in st.session_state['cart']:
        if item['Product ID'] == product_id:
            item['Quantity'] = st.session_state[f'quantity_{product_id}']
            break

# Add to cart function
def add_to_cart(product_id, product_name, price, image_url):
    if 'cart' not in st.session_state:
        st.session_state['cart'] = []
    st.session_state['cart'].append({
        'Product ID': product_id,
        'Product Name': product_name,
        'Price': price,
        'Image URL': image_url
    })
    st.success(f"Added {product_name} to the cart!")
    store_cart_in_db(st.session_state["username"]) 

# Function to display the Wishlist page
def show_wishlist_page():
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    st.title("💖 Your Wishlist 💖")

    conn = create_connection()
    if conn:
        cursor = conn.execute('SELECT product_id, product_name, image_url FROM wishlist WHERE username=?', 
                              (st.session_state["username"],))
        wishlist_items = cursor.fetchall()

        if wishlist_items:
            for item in wishlist_items:
                product_id, product_name, image_url = item
                
                # Display product details
                st.image(image_url, width=150)
                st.subheader(product_name)
                
                st.write(f"Rating: {random.uniform(1, 5):.1f}")  # Random rating between 1 and 5
                st.write(f"Base Colour: {random.choice(['Red', 'Blue', 'Green'])}")  # Placeholder
                st.write(f"Gender: {random.choice(['Male', 'Female'])}")  # Placeholder
                st.write(f"Price: ₹{random.choice([150, 195, 210, 380, 500, 550])}")

                # Add to Cart button
                if st.button("Add to Cart", key=f"add_cart_{product_id}"):
                    add_to_cart(product_id, product_name, random.uniform(10, 100), image_url)
                    
                # Remove from Wishlist button
                if st.button("Remove from Wishlist", key=f"remove_{product_id}"):
                    with conn:
                        conn.execute('DELETE FROM wishlist WHERE username=? AND product_id=?', 
                                     (st.session_state["username"], product_id))
                    st.success(f"Removed {product_name} from your wishlist.")
                    st.rerun()
                    st.stop()  # Refresh to show updated wishlist

        else:
            st.write("Your wishlist is empty.")
        
        conn.close()  # Close the connection after usage
    else:
        st.error("Could not connect to the database.")

def show_checkout_page():
    # Check if checkout page should be displayed
    if not st.session_state.get('show_checkout_page', False):
        return  # Exit if we are not showing the checkout page

    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    st.title("🛍 Checkout 🛍")

    if st.session_state.get('logged_in', False):
        # Display user's personal information form
        st.subheader("Billing Information")

        with st.form(key='checkout_form'):
            full_name = st.text_input("Full Name", "")
            address = st.text_input("Address", "")
            city = st.text_input("City", "")
            state = st.text_input("State", "")
            zip_code = st.text_input("Pin Code", "")
            country = st.text_input("Country", "")
            phone = st.text_input("Phone Number", "")

            submit_button = st.form_submit_button("Submit Billing Information")

            if submit_button:
                # Validate all fields are filled
                if not all([full_name, address, city, state, zip_code, country, phone]):
                    st.warning("Please fill out all fields before submitting.")
                else:
                    # Save billing information to session state or database
                    st.session_state["billing_info"] = {
                        "full_name": full_name,
                        "address": address,
                        "city": city,
                        "state": state,
                        "zip_code": zip_code,
                        "country": country,
                        "phone": phone,
                    }
                    st.success("Billing information submitted successfully!")
        
        # Display the cart items for confirmation
        st.subheader("Your Cart Items")
        if 'cart' in st.session_state and st.session_state['cart']:
            total_price = 0  # Variable to keep track of total price
            for item in st.session_state['cart']:
                item['Price'] = random.randint(150, 500)
                item_total = item['Price'] * item.get('Quantity', 1)
                total_price += item_total
                st.write(f"{item['Product Name']} - Price: ₹{int(item['Price']):} x {item.get('Quantity', 1)} = ₹{int(item_total):}")

            st.subheader(f"Total Amount: ₹{int(total_price):}")

            # Payment method selection
            st.subheader("Payment Method")
            payment_method = st.radio(
                "Select your payment method:",
                options=[ "Cash on Delivery","Pay Online"]
            )
            
            if payment_method=="Pay Online":
                payment_method = st.radio(
                "Pay Online:",
                options=["GPay", "Phonepe", "Credit Card", "Debit Card", "Net Banking"]
            )

            if st.button("Confirm Purchase"):
                # Validate billing info is filled before confirming the purchase
                if 'billing_info' not in st.session_state:
                    st.warning("Please fill in the billing information before confirming your order.")
                else:
                    # Check again if the address fields are filled
                    billing_info = st.session_state['billing_info']
                    if not all([billing_info['full_name'], billing_info['address'], billing_info['city'], 
                                billing_info['state'], billing_info['zip_code'], billing_info['country'], 
                                 billing_info['phone']]):
                        st.error("Please fill out the complete billing information before proceeding.")
                    else:
                        # Generate a random delivery date
                        delivery_date = generate_random_delivery_date()

                        # Save order details (including delivery date)
                        if 'orders' not in st.session_state:
                            st.session_state['orders'] = []

                        st.session_state['orders'].append({
                            'order_id': generate_order_id(),  # Assume a function to generate unique order ID5
                            'billing_info': st.session_state['billing_info'],
                            'cart_items': st.session_state['cart'],
                            'total_amount': total_price,
                            'payment_method': payment_method,
                            'delivery_date': delivery_date,
                            'canceled': False
                        })

                        # Clear the cart after purchase
                        st.session_state['cart'] = []

                        # Reset the checkout state
                        st.session_state['show_checkout_page'] = False
                        st.session_state['order_confirmed'] = True

                        st.success("Your order has been placed successfully!")
                        st.write(f"Your order will be delivered on: *{delivery_date.strftime('%Y-%m-%d')}*")

                        st.rerun()  # Refresh the page to reflect changes
        else:
            st.write("Your cart is empty.")
    else:
        st.warning("Please log in to proceed to checkout.")

def generate_random_delivery_date():
    """Generate a random delivery date within the next 7-14 days."""
    today = datetime.date.today()
    random_days = random.randint(7, 14)
    return today + datetime.timedelta(days=random_days)

def generate_order_id():
    """Generate a unique order ID (for simplicity, using random numbers here)."""
    return random.randint(100000, 999999)

def show_order_summary():
    # Check if the order summary should be displayed
    if not st.session_state.get('order_confirmed', False):
        return  # Exit if no order is confirmed

    # Add background image and custom text styles
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    st.title("🛒 Order Summary 🛒")

    # Display billing information
    if 'billing_info' in st.session_state:
        billing_info = st.session_state['billing_info']
        st.subheader("Billing Information")
        
        # Generate and display an order ID
        order_id = generate_order_id()
        st.write(f"*Order ID:* {order_id}")

        st.write(f"*Full Name:* {billing_info['full_name']}")
        st.write(f"*Address:* {billing_info['address']}, {billing_info['city']}, {billing_info['state']}, {billing_info['zip_code']}, {billing_info['country']}")
        st.write(f"*Phone Number:* {billing_info['phone']}")

        # Generate delivery date and display
        delivery_date = generate_random_delivery_date()
        st.write(f"*Delivery Date:* {delivery_date.strftime('%Y-%m-%d')}")

    # Optionally add a button to allow users to return to the main page or continue shopping
    if st.button("Continue Shopping"):
        st.session_state['show_checkout_page'] = False  # Reset checkout state
        st.session_state['order_confirmed'] = False  # Reset order confirmation
        st.rerun()  # Refresh the page


def show_my_orders():
    # Check if the user is logged in
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    if not st.session_state.get('logged_in', False):
        st.warning("Please log in to view your orders.")
        return

# Check if the user has any orders
    if 'orders' not in st.session_state or not st.session_state['orders']:
        
        st.subheader("You have no past orders.")
        return
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    st.title("🛍 My Orders 🛍")

    # Display each order
    for order_idx, order in enumerate(st.session_state['orders']):
        st.subheader(f"Order ID: {order['order_id']}")
        st.write(f"*Billing Information:*")
        st.write(f"Full Name: {order['billing_info']['full_name']}")
        st.write(f"Address: {order['billing_info']['address']}, {order['billing_info']['city']}, {order['billing_info']['state']}, {order['billing_info']['zip_code']}, {order['billing_info']['country']}")
        st.write(f"Phone: {order['billing_info']['phone']}")

        st.write("*Items Ordered:*")
        for item in order['cart_items']:
            st.write(f"{item['Product Name']} - Price: ₹{item['Price']:} x {item.get('Quantity', 1)}")

        # Display total amount
        st.write(f"*Total Amount:* ₹{order['total_amount']:}")

        # Display delivery date
        delivery_date = order.get('delivery_date', generate_random_delivery_date())
        st.write(f"*Delivery Date:* {delivery_date.strftime('%Y-%m-%d')}")

        # Add "Cancel Order" button if the order hasn't been canceled already
        if not order.get('canceled', False):
            if st.button(f"Cancel Order {order['order_id']}", key=f"cancel_order_{order_idx}"):
                st.session_state['orders'][order_idx]['canceled'] = True  # Mark order as canceled
                st.success(f"Order {order['order_id']} has been canceled.")
                st.rerun()  # Refresh the page to reflect changes
        else:
            st.write(f"*Status:* Order Canceled")
        
        st.write("---")  # Separator for each orde
# Function to display the Account page
def show_account_page():
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
    add_custom_text_styles()
    st.title("👤 Your Account 👤")
    
    st.write(f"Username: {st.session_state['username']}")
    
    # Delete Account Button
    if st.button("Delete Account"):
        conn = create_connection()
        with conn:
            conn.execute('DELETE FROM users WHERE username=?', (st.session_state["username"],))
            st.success("Your account has been deleted.")
            st.session_state["logged_in"] = False  # Log the user out
            st.session_state.pop("username", None)
            st.rerun()  # Clear the username
    
    # Logout Button
    if st.button("Logout"):
        st.session_state["logged_in"] = False  # Log the user out
        st.session_state.pop("username", None)  # Clear the username
        st.success("You have been logged out.")
        st.stop()  # Refresh the page to reflect the logout status
        st.rerun()

# Simple knowledge base for the fashion chatbot
fashion_knowledge_base = {
    "summer": "For summer, light fabrics like cotton and linen are great! Try floral dresses, shorts, or breathable t-shirts.",
    "winter": "For winter, layering is key! A wool coat, scarves, and insulated boots will keep you warm and stylish.",
    "formal event": "For formal events, a tailored suit for men or an elegant gown for women is perfect. Neutral colors are always safe.",
    "casual": "For casual wear, jeans and a t-shirt or a comfortable dress work great! Try brands like Levi's, Uniqlo, or H&M.",
    "trends": "The latest trends include oversized blazers, wide-leg pants, and sustainable clothing.",
    "workout": "For workouts, wear breathable and moisture-wicking fabrics like polyester or spandex. Leggings and tank tops are popular choices.",
    "jeans": "Style your jeans with a tucked-in shirt for a classic look, or pair them with a leather jacket for something edgy.",
    "brands": "Popular fashion brands include Zara, Nike, Gucci, and Adidas. For sustainable fashion, try Patagonia or Everlane.",
    "accessories": "Accessories like watches, belts, scarves, or a statement bag can elevate your outfit. Keep them minimal for a clean look.",
    "shoes": "For casual looks, sneakers or loafers are great. For formal outfits, opt for leather shoes or heels.",
    "party": "For a party, try bold colors or sequins. A cocktail dress or a sharp blazer with dark trousers works perfectly.",
    "date night": "For a date night, try a chic midi dress or a smart casual outfit like a blazer with slim-fit pants.",
    "wedding": "For weddings, formal dresses or traditional attire like sarees are great for women, while men can wear suits or sherwanis.",
    "business casual": "For business casual, go for chinos or trousers paired with a button-down shirt. Add a blazer for a polished touch.",
    "sustainable fashion": "Sustainable fashion focuses on eco-friendly materials and ethical production. Brands like Reformation and Everlane are great examples.",
    "fashion tips": "Always dress for the occasion and prioritize comfort. Choose clothes that fit well and complement your body type.",
    "color combinations": "Some classic color combinations are navy and white, black and gold, or pastels with neutral tones.",
    "rainy season": "For rainy days, try waterproof jackets, gumboots, and quick-dry fabrics. Add a fun umbrella to stay stylish!",
    "beachwear": "For the beach, try swimsuits or bikinis with a sarong. Add a wide-brimmed hat and sunglasses for a chic look.",
    "fall fashion": "For fall, cozy sweaters, ankle boots, and trench coats are perfect. Layering works beautifully in this season.",
    "office wear": "Office wear staples include pencil skirts, tailored trousers, button-down shirts, and blazers. Keep it professional and polished.",
    "streetwear": "Streetwear includes hoodies, sneakers, oversized t-shirts, and joggers. Brands like Supreme and Off-White are popular."
}

def chatbot_response(user_input):
    """Generate a chatbot response based on user input."""
    greetings = ["hi", "hello", "hey"]
    farewell = ["bye", "goodbye", "see you"]
    thanks = ["thank you", "thanks", "thanks a lot", "thank you so much"]
    user_input = user_input.lower().strip()
    if any(greeting in user_input for greeting in greetings):
        return "Hello! How can I help you with fashion today? 😊"
    if any(farewell_word in user_input for farewell_word in farewell):
        return "Goodbye! Stay stylish and take care! 👋"
    if any(thank_you in user_input for thank_you in thanks):
        return "You're welcome! I'm happy to help. 😊"
    # Check if the user is asking about fashion topics in the knowledge base
    for key, response in fashion_knowledge_base.items():
        if key in user_input:
         return response
    # Default response if no match is found
    return "I'm here to help with all your fashion questions! Ask me about trends, outfit ideas, or anything fashion-related."
 
# Streamlit app
def fashion_chatbot_app():
    st.title("Fashion Chat Assistant 💁‍♀️")
    st.write("Hi! I'm your fashion assistant. Ask me about fashion trends, outfit ideas, or what to wear for any occasion!")
    add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")

    # Initialize session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # User Input
    user_query = st.text_input(
        "Your Question:",
        placeholder="E.g., What should I wear in winter?",
        key="user_input"
    )

    # Send button
    if st.button("Send"):
        if user_query:
            # Append user query to the chat history
            st.session_state.chat_history.append({"sender": "User", "message": user_query})

            # Get chatbot response
            response = chatbot_response(user_query)

            # Append chatbot response to the chat history
            st.session_state.chat_history.append({"sender": "ChatBot", "message": response})

    # Display Chat History
    st.write("### Chat History")
    for chat in st.session_state.chat_history:
        if chat["sender"] == "User":
            st.markdown(f"**You:** {chat['message']}")
        else:
            st.markdown(f"**ChatBot:** {chat['message']}")

    # Clear Chat History Button
    if st.button("Clear Chat"):
        st.session_state.chat_history.clear()
        st.success("Chat history cleared!")
        st.rerun()

# Initialize app with login status check
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# Create the users table when the app starts
create_user_table()

from streamlit_option_menu import option_menu
# Top navigation menu
if not st.session_state.get("logged_in", False):
    st.title("👉Welcome To Fashion Life Style👖")
    option = option_menu(
        None,  # No title
        ["Signup", "Login"],
        icons=["person-plus", "box-arrow-in-right"],  # Icons for Signup, Login
        menu_icon="cast",
        default_index=0,
        orientation="horizontal",  # Horizontal navigation
        styles={
            "container": {"padding": "0", "background-color": "#f5f5f5"},
            "nav-link": {"font-size": "18px", "text-align": "center", "margin": "0px"},
            "nav-link-selected": {"background-color": "#4CAF50", "color": "white"},
        },
    )
else:
    st.title("Fashion Life Style⌚👖")
    option = option_menu(
    None,
    ["Trending Products", "Recommendations", "Cart", "Wishlist", "Account", "My Orders", "Help"],
    icons=["stars", "lightbulb", "cart", "heart", "person", "box-seam", "question-circle"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "10px",
            "background-color": "#f5f5f5",  # Background color of the menu
            "border-radius": "10px",  # Rounded corners for the menu container
            "box-shadow": "0px 4px 6px rgba(0, 0, 0, 0.1)",  # Subtle shadow for depth
            "display": "flex",
            "gap": "30px",  # Increased space between buttons
            "align-items": "center",  # Vertically center the buttons
        },
        "nav-link": {
            "font-size": "16px",  # Font size of the button text
            "padding": "8px 16px",  # Larger padding to make buttons more clickable
            "border-radius": "20px",  # Make the buttons rounded
            "text-align": "center",  # Center the text in the button
            "background-color": "transparent",  # Remove background color
            "color": "#333",  # Text color
            "border": "2px solid #ccc",  # Border around each button
            "transition": "background-color 0.3s, transform 0.3s",  # Smooth transition effect
        },
        "nav-link:hover": {
            "background-color": "#4CAF50",  # Change background color on hover
            "color": "#4CAF50",  # Change text color on hover
            "transform": "scale(1.1)",  # Slightly enlarge the button on hover
        },
        "nav-link-selected": {
            "background-color": "#4CAF50",  # Transparent background when selected
            "color": "white",  # Text color when selected
            "font-weight": "bold",  # Make the text bold for selected item
        },
    },
)
    
# Login page logic
if option == "Login":
    login()
elif option == "Signup":
    signup()
# Trending Products Page
elif option == "Trending Products":
    if st.session_state["logged_in"]:
        merged_data = load_data()  # Load the merged data
        add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
        add_custom_text_styles()
        st.title("🛒 Trending Products 😎")

        # Randomly select 8 products without fixed random_state
        random_products = merged_data.sample(n=8)  # No random_state for new selection every time

        cols_per_row = 4  # Number of columns in the grid
        for row_index in range(0, len(random_products), cols_per_row):
            cols = st.columns(cols_per_row)
            for col_index, col in enumerate(cols):
                if row_index + col_index < len(random_products):
                    product = random_products.iloc[row_index + col_index]
                    with col:
                        # Ensure the image URL is valid
                        if isinstance(product['ImageURL'], str) and pd.notna(product['ImageURL']):
                            # Check if the URL is accessible
                            try:
                                response = requests.head(product['ImageURL'])
                                if response.status_code == 200:
                                    st.image(product['ImageURL'], width=150)
                                else:
                                    st.error(f"Invalid image URL: {product['ImageURL']}")
                            except Exception as e:
                                   st.error(f"Failed to load image: {e}")
                        else:
                             st.error("Invalid image URL")  

                        st.subheader(product['Name'])
                        st.write(f"Rating: {product['Rating']}")
                        st.write(f"Base Colour: {product['baseColour']}")
                        
                        st.write(f"Price: ₹{int(random.uniform(150, 500)):}")  # Random price for example
                        st.button("Add to Cart", key=product['Product Id'], on_click=add_to_cart,
                                   args=(product['Product Id'], product['Name'], random.uniform(10, 100), product['ImageURL']))
                        st.button("Add to Wishlist", key=f"wishlist_{product['Product Id']}", on_click=add_to_wishlist,
                                   args=(product['Product Id'], product['Name'], product['ImageURL']))
    else:
        st.warning("You need to log in to view trending products.")

# Recommendations Page
elif option == "Recommendations":
    if st.session_state["logged_in"]:
        add_bg_image("https://t3.ftcdn.net/jpg/03/59/68/80/360_F_359688056_TjlQsvMEyfNxQfsXc5D3HFXwttrfPOEi.jpg")
        add_custom_text_styles()
        st.title("🔍 Product Recommendations 👗")

        # Load the merged data
        merged_data = load_data()
        product_name = st.text_input("Enter a product name or category (e.g., 'shirts'):") 

        if st.button("Get Recommendations"):
            # Filter the merged data for the specified product name
            filtered_products = merged_data[merged_data['Name'].str.contains(product_name, case=False, na=False)]

            if not filtered_products.empty:
                # Shuffle the filtered products and select a random sample
                random_products = filtered_products.sample(frac=1).reset_index(drop=True)  # Corrected line

                # Select a number of random products for display
                num_recommendations = 5  # Number of recommendations to show
                recommendations = random_products.head(num_recommendations)  # Select the top N products after shuffling

                # Display the random recommendations
                st.write("Top Recommendations:")
                for i, rec in recommendations.iterrows():
                    image_url = rec['ImageURL']
                    if isinstance(image_url, str) and pd.notna(image_url):
                        try:
                            response = requests.head(image_url)
                            if response.status_code == 200:
                                st.image(image_url, width=250)
                            else:
                                st.error(f"Invalid image URL: {image_url}")
                        except Exception as e:
                              st.error(f"Failed to load image: {e}")
                    else:
                        st.error("Invalid image URL")  

                    st.subheader(rec['Name'])
                    st.write(f"Rating: {rec['Rating']}")
                    st.write(f"Base Colour: {rec['baseColour']}")
                    st.write(f"Gender: {rec['Gender']}")
                    st.write(f"Price: ₹{random.choice([150, 195, 210, 380, 500]):}")

                    # Add buttons for cart and wishlist
                    st.button("Add to Cart", key=f"cart_{rec['Product Id']}", 
                               on_click=add_to_cart, args=(rec['Product Id'], rec['Name'], random.uniform(10, 100), image_url))
                    st.button("Add to Wishlist", key=f"wishlist_{rec['Product Id']}", 
                               on_click=add_to_wishlist, args=(rec['Product Id'], rec['Name'], image_url))
            else:
                st.error("No products found for the given category or name.")
    else:
        st.warning("You need to log in to view recommendations.")

elif option == "Cart":
    show_cart_page()
    if st.session_state.get('show_checkout_page', False):
        show_checkout_page()
    elif st.session_state.get('order_confirmed', False):
        show_order_summary()
    
# Wishlist Page
elif option == "Wishlist":
    show_wishlist_page()
elif option == "My Orders":
    show_my_orders()
# Account Page
elif option == "Account":
    show_account_page()
elif option == "Help":
     fashion_chatbot_app()
# If not logged in, prompt to log in
if not st.session_state["logged_in"]:
    st.warning("Please log in to access the app.")