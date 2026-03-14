import os
import streamlit as st
import json
from groq import Groq
from dotenv import load_dotenv

# Load API key
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    st.error("GROQ_API_KEY not found in .env file")
    st.stop()
client = Groq(api_key=api_key)

def generate_quiz(subject, topic):
    prompt = f"""
Generate 5 multiple choice questions for the subject {subject} on the topic {topic}.

Each question must have 4 meaningful answer options.
Do NOT use only letters like A, B, C, D as options.
Options must be full text answers.

Return ONLY valid JSON in this format:

[
  {{
    "question": "...",
    "options": ["option text 1", "option text 2", "option text 3", "option text 4"],
    "correct_answer": "exact correct option text",
    "explanation": "..."
  }}
]

Do not include any extra text outside JSON.
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    text = completion.choices[0].message.content

    # Extract JSON safely
    start = text.find("[")
    end = text.rfind("]") + 1
    json_text = text[start:end]

    quiz = json.loads(json_text)
    return quiz

#for AI TUTOR
def ask_tutor(question, level="class 10"):
    prompt = f"""
You are an intelligent tutor helping a student understand a weak concept.

Explain the following topic in simple terms suitable for a {level} student:

Topic: {question}

Rules:
- Use easy language.
- Explain step-by-step.
- Give one small real-life example.
- Keep it short and clear.
- End with encouragement like a teacher.
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    answer = completion.choices[0].message.content
    return answer