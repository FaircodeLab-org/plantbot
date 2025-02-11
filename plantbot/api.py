# File: plantbot/plantbot/api.py

import frappe
import openai
import requests
import base64
import json
import threading
import numpy as np
import os
import time

# Import helper functions from faqs.py
from plantbot.plantbot.doctype.faqs.faqs import get_openai_api_key, get_embedding

# Global variables
faq_embeddings = []
embeddings_initialized = False
embeddings_lock = threading.Lock()

def initialize_faq_embeddings():
    """
    Initializes embeddings for FAQs by loading them from the database.
    """
    global faq_embeddings
    global embeddings_initialized

    with embeddings_lock:
        if embeddings_initialized:
            # Embeddings have already been initialized
            return

        try:
            # Fetch all FAQs with their embeddings
            faqs = frappe.get_all('FAQS', fields=['name', 'question', 'answer', 'embedding'])

            # Load embeddings for each FAQ
            faq_embeddings = []
            for faq in faqs:
                if faq['embedding']:
                    try:
                        # Load the embedding from JSON string
                        embedding = json.loads(faq['embedding'])
                        faq_embeddings.append({
                            'name': faq['name'],
                            'question': faq['question'],
                            'answer': faq['answer'],
                            'embedding': embedding
                        })
                        frappe.logger().debug(f"Loaded embedding for FAQ '{faq['name']}': First 5 values: {embedding[:5]}...")
                    except Exception as e:
                        frappe.log_error(f"Error loading embedding for FAQ {faq['name']}: {str(e)}", "Chatbot Embedding Error")
                else:
                    # If embedding is missing, compute and save it
                    openai_api_key = get_openai_api_key()
                    if not openai_api_key:
                        frappe.log_error("OpenAI API key is not set.", "Chatbot Error")
                        continue

                    embedding = get_embedding(faq['question'])
                    # Save the embedding in the database
                    frappe.db.set_value('FAQS', faq['name'], 'embedding', json.dumps(embedding))
                    frappe.db.commit()
                    faq_embeddings.append({
                        'name': faq['name'],
                        'question': faq['question'],
                        'answer': faq['answer'],
                        'embedding': embedding
                    })
            embeddings_initialized = True  # Mark embeddings as initialized
        except Exception as e:
            frappe.log_error(f"Error initializing embeddings: {str(e)}", "Chatbot Embedding Initialization Error")

@frappe.whitelist(allow_guest=True)
def get_bot_response(user_message):
    """
    Public method to get the bot's response.
    """
    # Ensure embeddings are initialized
    if not embeddings_initialized:
        initialize_faq_embeddings()

    response = process_message(user_message)
    return response

def process_message(user_message):
    """
    Processes the user's message and returns the bot's response.
    """
    user_message = user_message.strip()

    # Search the knowledge base for an exact match
    faq_answer = search_faq(user_message)
    if faq_answer:
        return faq_answer

    # If no exact match, use embeddings to find relevant FAQs
    relevant_faqs = get_relevant_faqs(user_message, top_k=5)
    gpt_answer = get_gpt_interpreted_response(user_message, relevant_faqs)
    return gpt_answer

def search_faq(user_message):
    """
    Searches for an exact match in the FAQs.
    """
    faqs = frappe.get_all('FAQS', fields=['question', 'answer'])
    for faq in faqs:
        if user_message.lower() == faq['question'].lower():
            return faq['answer']
    return None

def get_embedding(text, model="text-embedding-ada-002"):
    """
    Generates an embedding for the given text using the specified OpenAI model.
    """
    # Ensure OpenAI API key is set
    if not openai.api_key:
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            frappe.log_error("OpenAI API key is not set.", "Chatbot Error")
            return []

        openai.api_key = openai_api_key

    try:
        response = openai.Embedding.create(
            input=[text],
            model=model
        )
        embedding = response['data'][0]['embedding']
        return embedding
    except Exception as e:
        frappe.log_error(f"Error generating embedding: {str(e)}", "Chatbot Embedding Error")
        return []

def cosine_similarity(a, b):
    """
    Computes the cosine similarity between two vectors.
    """
    a = np.array(a)
    b = np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def get_relevant_faqs(user_message, top_k=5):
    global faq_embeddings

    if not faq_embeddings:
        frappe.log_error("FAQ embeddings are not initialized.", "Chatbot Error")
        return []

    # Generate embedding for user message
    user_embedding = get_embedding(user_message)
    if not user_embedding:
        frappe.log_error("Failed to get embedding for user message.", "Chatbot Error")
        return []
    frappe.logger().debug(f"Generated embedding for user message: First 5 values: {user_embedding[:5]}...")

    # Compute cosine similarity between user message and FAQs
    similarities = []
    for faq in faq_embeddings:
        try:
            sim = cosine_similarity(user_embedding, faq['embedding'])
            similarities.append((sim, faq))
            # Log each similarity score
            frappe.logger().debug(f"Similarity between user message and FAQ '{faq['name']}': {sim}")
        except Exception as e:
            frappe.log_error(f"Error computing similarity for FAQ {faq['name']}: {str(e)}", "Chatbot Similarity Error")

    # Sort FAQs by similarity score in descending order
    similarities.sort(key=lambda x: x[0], reverse=True)

    # # Return top_k most similar FAQs
    # relevant_faqs = [faq for sim, faq in similarities[:top_k] if sim > 0]  # Exclude FAQs with zero similarity
    MIN_SIMILARITY_THRESHOLD = 0.0  # You can adjust this value
    relevant_faqs = [faq for sim, faq in similarities[:top_k] if sim >= MIN_SIMILARITY_THRESHOLD]

    # Log the selected relevant FAQs
    frappe.logger().debug(f"Top {len(relevant_faqs)} relevant FAQs selected.")
    return relevant_faqs

def get_gpt_interpreted_response(user_message, relevant_faqs):
    """
    Uses OpenAI's ChatCompletion API to generate a response based on relevant FAQs.
    """
    # Ensure OpenAI API key is set
    if not openai.api_key:
        openai_api_key = get_openai_api_key()
        if not openai_api_key:
            frappe.log_error("OpenAI API key is not set.", "Chatbot Error")
            return "I'm sorry, I cannot process your request at the moment."

        openai.api_key = openai_api_key

    # Prepare the FAQ prompt with relevant FAQs
    if relevant_faqs:
        faq_prompt = "\n".join([f"Q: {faq['question']}\nA: {faq['answer']}" for faq in relevant_faqs])
    else:
        faq_prompt = ""

    # Incorporate company description, vision, and mission into the system prompt
    company_description = """
    Plantrich Agritech Private Limited, nestled in the heart of Kerala, India, is a beacon of sustainability and innovation in organic agribusiness. Specializing in premium organic spice extractions, spice powders, spice blends, green coffee beans, cocoa beans, coconut oil, and herbs, Plantrich brings the authentic flavours and rich aroma of the Western Ghats to tables across the globe.

    With a mission deeply rooted in sustainability and fairness, Plantrich empowers over 5,000 farmers from South India, fostering ethical farming practices and promoting a fair trade system that strengthens local economies. Certified by USDA NOP, EU Organic, Fairtrade, Natureland, and Rainforest Alliance, every product reflects our unwavering commitment to quality, health, and environmental protection.

    Plantrich has established a strong global presence in India, Europe, US, and the Middle East. Guided by a vision of healthy living and environmental stewardship, Plantrich is redefining how the world experiences organic food.

    Our Ethical Business Model allows all parties to participate in a fully traceable and fair trade chain, from our farmers to our factory and on to our customers. Everyone has a part to play in supporting a sustainable environment.

    Vision:
    To empower farmers, promote sustainable living, and deliver organic riches to the global market.

    Mission:
    To bring the finest organic products to the world while supporting sustainable farming practices, fair trade, and environmental stewardship.
    """

    system_prompt = f"""
    You are a helpful assistant for Plantrich Agritech Private Limited. Use the following information to answer the user's questions in a clear and friendly manner.

    Company Description:
    {company_description}

    FAQs:
    {faq_prompt}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-1106-preview",  # Make sure this model is available to you
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_message.strip()}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        frappe.log_error(f"OpenAI API Error: {str(e)}", "Chatbot Response Error")
        return "I'm sorry, I'm having trouble responding right now. Please try again later."

@frappe.whitelist(allow_guest=True)
def process_image():
    if 'image' in frappe.request.files:
        image_file = frappe.request.files['image']

        # Call the Plant.id API with the image
        diagnosis = get_plant_diagnosis(image_file)

        # Return the diagnosis to the frontend
        return diagnosis
    else:
        return "No image provided."

@frappe.whitelist(allow_guest=True)
def get_plant_diagnosis(image_file):
    # Retrieve the Plant.id API key from the site configuration
    plantid_api_key = frappe.conf.get("plantid_api_key")
    if not plantid_api_key:
        frappe.log_error("Plant.id API key not found in site config.", "Chatbot Error")
        return "I'm sorry, I cannot process your request at the moment."

    url = "https://api.plant.id/v3/identification"

    headers = {
        "Content-Type": "application/json",
        "Api-Key": plantid_api_key,
    }

    # Read the image content
    image_bytes = image_file.read()
    if not image_bytes:
        frappe.log_error("Image file is empty.", "Image Processing Error")
        return "The uploaded image is empty or unreadable."

    # Convert the image to base64
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')

    # Prepare the request payload
    payload = {
        "images": [encoded_image],
        "health": "all",  # Include health assessment
        "classification_level": "species",  # Level of classification
        # Omit 'similar_images' if False
    }

    # Prepare query parameters
    params = {
        "plant_details": "common_names,url,wiki_description,wiki_image,taxonomy,synonyms",
        "disease_details": "description,treatment",
        "language": "en",
    }

    try:
        # Make the POST request with query parameters
        response = requests.post(url, headers=headers, params=params, json=payload)

        # Log response status and content for debugging
        frappe.logger().debug(f"Plant.id API response status code: {response.status_code}")
        frappe.logger().debug(f"Plant.id API response text: {response.text}")

        # Check if response is successful
        if response.ok:
            result = response.json()
            # Process the API Response
            diagnosis = process_plant_id_response(result)
            return diagnosis
        else:
            error_message = f"Plant.id API Error {response.status_code}: {response.text}"
            frappe.log_error(error_message[:140], "Plant.id API Error")  # Truncate error_message
            return "An error occurred while processing the image. Please try again later."
    except Exception as e:
        frappe.log_error(f"Exception in get_plant_diagnosis: {str(e)}\nTraceback:\n{frappe.get_traceback()}", "Plant.id API Error")
        return "An error occurred while processing the image. Please try again later."

def process_plant_id_response(result):
    # Extract plant suggestions
    classification = result.get('result', {}).get('classification', {})
    suggestions = classification.get('suggestions', [])

    if suggestions:
        # Take the top suggestion
        suggestion = suggestions[0]
        plant_name = suggestion.get('name', 'Unknown plant')
        details = suggestion.get('details', {})
        common_names = details.get('common_names', [])
        description = details.get('wiki_description', {}).get('value', '')
        plant_url = details.get('url', '')

        response_message = f"<b>Plant Name:</b> {plant_name}<br>"
        if common_names:
            response_message += f"<b>Common Names:</b> {', '.join(common_names)}<br>"
        if description:
            response_message += f"<b>Description:</b> {description}<br>"
        if plant_url:
            response_message += f"<a href='{plant_url}' target='_blank'>Learn more</a><br><br>"

        # Health assessment
        health_assessment = result.get('result', {})
        is_healthy = health_assessment.get('is_healthy', {}).get('binary', True)
        if not is_healthy:
            response_message += "<b>The plant may have health issues.</b><br>"
            diseases = health_assessment.get('disease', {}).get('suggestions', [])
            if diseases:
                response_message += "<b>Possible Diseases:</b><br>"
                for disease in diseases:
                    name = disease.get('name', 'Unknown disease')
                    disease_details = disease.get('details', {})
                    disease_description = disease_details.get('description', {}).get('value', '')
                    treatment = disease_details.get('treatment', {})
                    response_message += f"<b>{name}</b><br>"
                    if disease_description:
                        response_message += f"Description: {disease_description}<br>"
                    if treatment:
                        # Treatment can be a dictionary with 'biological', 'chemical', 'prevention'
                        treatment_info = []
                        for key, value in treatment.items():
                            if value:
                                treatment_info.append(f"{key.capitalize()}: {value}")
                        if treatment_info:
                            response_message += f"Treatment: {'; '.join(treatment_info)}<br>"
                    response_message += "<br>"
            else:
                response_message += "No specific diseases identified.<br>"
        else:
            response_message += "<b>The plant appears to be healthy.</b><br>"

        return response_message
    else:
        return "Could not identify the plant or its health status."