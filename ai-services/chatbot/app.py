"""
SmartRentAI - NLP Chatbot Microservice
Intent classification using TF-IDF + Naive Bayes
Run: python app.py  (port 8003)
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import joblib
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

app = Flask(__name__)
CORS(app)

MODEL_PATH = 'chatbot_model.joblib'

# ── Training data ─────────────────────────────────────────────
TRAINING_DATA = [
    # (text, intent)
    ("what is the price of this property", "rental_pricing"),
    ("how much does it cost to rent", "rental_pricing"),
    ("what is the monthly rent", "rental_pricing"),
    ("rental price estimate", "rental_pricing"),
    ("how much should I pay", "rental_pricing"),
    ("predict rent for 3 bedrooms in Colombo", "rental_pricing"),

    ("show me property recommendations", "property_recommendation"),
    ("suggest properties for me", "property_recommendation"),
    ("what properties match my preferences", "property_recommendation"),
    ("find me a house in kandy", "property_recommendation"),
    ("I need an apartment in Colombo", "property_recommendation"),
    ("recommend properties with 2 bedrooms", "property_recommendation"),

    ("what is the lease duration", "lease_information"),
    ("how long is the rental contract", "lease_information"),
    ("can I break the lease early", "lease_information"),
    ("what happens if I terminate early", "lease_information"),
    ("lease agreement details", "lease_information"),

    ("how do I contact the landlord", "landlord_support"),
    ("I want to message the property owner", "landlord_support"),
    ("landlord phone number", "landlord_support"),
    ("how to post a property listing", "landlord_support"),
    ("I want to list my property", "landlord_support"),
    ("how to add property as landlord", "landlord_support"),

    ("I forgot my password", "account_issues"),
    ("how do I reset my password", "account_issues"),
    ("can't login to my account", "account_issues"),
    ("email verification not working", "account_issues"),
    ("how do I register", "account_issues"),
    ("create a new account", "account_issues"),

    ("what facilities are nearby", "nearby_facilities"),
    ("is there a hospital near this property", "nearby_facilities"),
    ("schools close to this location", "nearby_facilities"),
    ("public transport nearby", "nearby_facilities"),
    ("supermarket near the property", "nearby_facilities"),
    ("distance to bus stop", "nearby_facilities"),

    ("how does the booking work", "booking_assistance"),
    ("how to schedule a viewing", "booking_assistance"),
    ("I want to visit this property", "booking_assistance"),
    ("how to apply for rental", "booking_assistance"),
    ("what documents do I need to rent", "booking_assistance"),

    ("hello", "greeting"),
    ("hi there", "greeting"),
    ("good morning", "greeting"),
    ("hey", "greeting"),

    ("thank you", "farewell"),
    ("goodbye", "farewell"),
    ("thanks for help", "farewell"),
    ("bye", "farewell"),

    ("how does SmartRentAI work", "general_faq"),
    ("what is this platform", "general_faq"),
    ("is this website free to use", "general_faq"),
    ("how do I save a property", "general_faq"),
    ("can I report a listing", "general_faq"),
]

# ── Response templates ────────────────────────────────────────
RESPONSES = {
    "rental_pricing": [
        "You can use our **Price Prediction** tool to get an AI-powered rent estimate. Just enter the property details (location, bedrooms, type) and our model will predict a fair market price.",
        "Rental prices in Sri Lanka vary by location. Colombo properties typically range from LKR 25,000–150,000/month. Use our Price Predictor for a precise estimate based on your property features.",
    ],
    "property_recommendation": [
        "Visit your **Recommendations** page to see AI-personalised property suggestions based on your preferences, budget, and search history.",
        "Our AI engine analyses your saved properties and preferences to recommend the best matches. Update your preferences in your profile for better results!",
    ],
    "lease_information": [
        "Lease terms are set by the landlord and typically range from 6–12 months in Sri Lanka. You can find the specific terms on the property details page.",
        "For lease agreement details, contact the landlord directly from the property listing. Most landlords require 1–2 months security deposit.",
    ],
    "landlord_support": [
        "As a landlord, you can list properties by registering with the **Landlord** role and using the **Add Property** button on your dashboard.",
        "To contact a landlord, go to the property details page and use the **Send Enquiry** button. The landlord will respond via the platform.",
    ],
    "account_issues": [
        "For password reset, click **Forgot Password** on the login page. A reset link will be sent to your email.",
        "To create an account, click **Register** and choose your role (Renter or Landlord). Email verification may be required.",
    ],
    "nearby_facilities": [
        "Property details pages show nearby hospitals, schools, bus stops, and supermarkets using our map integration. Look for the **Nearby Places** section.",
        "Our map view shows facilities within 2km of each property. You can filter by hospital, school, transport, or shopping.",
    ],
    "booking_assistance": [
        "To schedule a viewing, use the **Send Enquiry** form on the property page. Describe when you'd like to visit and the landlord will confirm.",
        "To apply for rental, contact the landlord via the property enquiry form. Typically you'll need your NIC, proof of income, and references.",
    ],
    "greeting": [
        "Hello! 👋 I'm SmartRentAI's assistant. How can I help you find your perfect rental today?",
        "Hi there! I can help you with property recommendations, price predictions, and rental advice. What would you like to know?",
    ],
    "farewell": [
        "Goodbye! Good luck with your property search. Feel free to come back anytime! 🏠",
        "Thank you for using SmartRentAI. Best of luck finding your perfect home! 🔑",
    ],
    "general_faq": [
        "SmartRentAI is a free AI-powered rental platform for Sri Lanka. You can search properties, get personalised recommendations, predict rental prices, and chat with our AI assistant.",
        "To save a property, click the **♡ Save** button on any listing. You can view all saved properties in your **Wishlist** page.",
    ],
}


def load_or_train_model():
    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)

    texts   = [t for t, _ in TRAINING_DATA]
    intents = [i for _, i in TRAINING_DATA]

    le = LabelEncoder()
    y  = le.fit_transform(intents)

    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
        ('clf',   MultinomialNB(alpha=0.5)),
    ])
    pipeline.fit(texts, y)

    model = {'pipeline': pipeline, 'label_encoder': le}
    joblib.dump(model, MODEL_PATH)
    return model


model = load_or_train_model()


@app.route('/chat', methods=['POST'])
def chat():
    data    = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'reply': 'Please type a message.', 'intent': None, 'confidence': 0})

    # Predict intent
    proba   = model['pipeline'].predict_proba([message])[0]
    top_idx = np.argmax(proba)
    intent  = model['label_encoder'].inverse_transform([top_idx])[0]
    confidence = float(proba[top_idx])

    if confidence < 0.25:
        intent = 'general_faq'

    responses = RESPONSES.get(intent, RESPONSES['general_faq'])
    reply     = responses[hash(message) % len(responses)]

    return jsonify({
        'reply':      reply,
        'intent':     intent,
        'confidence': round(confidence, 4),
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'chatbot'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8003, debug=True)
