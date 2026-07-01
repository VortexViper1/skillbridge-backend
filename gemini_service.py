import os
import json
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Read API Key
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please check your .env file.")

# Initialize Gemini Client
client = genai.Client(api_key=API_KEY)


def analyze_resume(resume_text):
    prompt = f"""
You are an expert ATS system.

Return ONLY valid JSON.

{{
  "summary":"",
  "strengths":[],
  "weaknesses":[],
  "missing_skills":[],
  "recommended_roles":[],
  "improvement_suggestions":[],
  "recommended_projects":[],
  "interview_questions":[]
}}

Resume:

{resume_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


def generate_mock_interview(resume_text):
    prompt = f"""
You are a senior technical interviewer.

Based on this resume, generate:

- 5 Technical Questions
- 3 Project Questions
- 2 HR Questions

Return ONLY valid JSON.

[
  {{
    "question":"",
    "answer":""
  }}
]

Resume:

{resume_text}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    text = response.text.strip()

    text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)