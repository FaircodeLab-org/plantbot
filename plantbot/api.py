# File: ~/frappe-bench/apps/plantbot/plantbot/api.py

import frappe
import openai

@frappe.whitelist(allow_guest=True)
def get_bot_response(user_message):
    response = process_message(user_message)
    return response

def process_message(user_message):
    user_message = user_message.lower().strip()

    # Search Knowledge Base
    faq = search_faq(user_message)
    if faq:
        return faq

    # If no match, use GPT to find the most relevant FAQ
    faqs = get_all_faqs()  # Fetch all FAQs from the database
    gpt_answer = get_gpt_interpreted_faq(user_message, faqs)
    return gpt_answer

def search_faq(user_message):
    # Perform a basic search for FAQs (exact match or contains)
    faqs = frappe.get_all('FAQS', fields=['question', 'answer'])
    for faq in faqs:
        if user_message in faq['question'].lower():  # Basic matching
            return faq['answer']
    return None

def get_all_faqs():
    # Fetch all FAQs from the database
    faqs = frappe.get_all('FAQS', fields=['question', 'answer'])
    return [{"question": faq["question"], "answer": faq["answer"]} for faq in faqs]

def get_gpt_interpreted_faq(user_message, faqs):
    openai_api_key = frappe.conf.get("openai_api_key")
    if not openai_api_key:
        frappe.log_error("OpenAI API key not found in site config.", "Chatbot Error")
        return "I'm sorry, I cannot process your request at the moment."

    openai.api_key = openai_api_key

    # Prepare the GPT prompt with all FAQs
    faq_prompt = "\n".join([f"Q: {faq['question']}\nA: {faq['answer']}" for faq in faqs])

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
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=150,
            temperature=0.7,
            # Optional: You can add 'n=1' to return one response
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "OpenAI API Error")
        return "I'm sorry, I'm having trouble responding right now. Please try again later."