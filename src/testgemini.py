import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use the correct model name from your list
model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content("Say hello from Gemini 2.5 Flash")
print(response.text)
