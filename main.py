from fastapi import FastAPI, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

from schemas import UserCreate, UserLogin
from database import engine, Base, SessionLocal
from models import User

from gemini_service import (
    analyze_resume,
    generate_mock_interview
)

import shutil
import os

app = FastAPI()

latest_resume_text = ""

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173" , 
                   "https://skillbridge-frontend-zeta.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

os.makedirs("uploads", exist_ok=True)


@app.get("/")
def home():
    return {
        "message": "SkillBridge AI Running"
    }


import re

def calculate_ats_score(text):

    text = text.lower()

    score = 0

    found_skills = []

    # -----------------------------
    # 1. CONTACT DETAILS (10)
    # -----------------------------

    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        score += 2

    if re.search(r"\+?\d[\d\s\-]{8,}", text):
        score += 2

    if "linkedin" in text:
        score += 2

    if "github" in text:
        score += 2

    if any(x in text for x in ["india", "hyderabad", "bangalore", "chennai", "mumbai", "address"]):
        score += 2

    # -----------------------------
    # 2. RESUME SECTIONS (15)
    # -----------------------------

    sections = {
        "education": 3,
        "skills": 3,
        "projects": 3,
        "experience": 3,
        "certifications": 3
    }

    for section, pts in sections.items():
        if section in text:
            score += pts

    # -----------------------------
    # 3. TECHNICAL SKILLS (25)
    # -----------------------------

    skill_categories = {

        "Programming": [
            "python","java","c++","c","javascript","typescript"
        ],

        "Frontend":[
            "html","css","react","angular","vue"
        ],

        "Backend":[
            "fastapi","flask","django","node.js","express"
        ],

        "Database":[
            "mysql","postgresql","mongodb","sqlite","sql"
        ],

        "Cloud":[
            "aws","azure","docker","kubernetes","gcp"
        ],

        "Cybersecurity":[
            "kali",
            "wireshark",
            "burp suite",
            "metasploit",
            "nmap",
            "ghidra",
            "ida",
            "digital forensics",
            "volatility",
            "autopsy",
            "yara"
        ],

        "AI":[
            "machine learning",
            "deep learning",
            "tensorflow",
            "pytorch",
            "opencv",
            "scikit-learn",
            "numpy",
            "pandas"
        ]
    }

    total_skills = 0

    for category in skill_categories.values():

        for skill in category:

            if skill in text and skill not in found_skills:

                found_skills.append(skill)

                total_skills += 1

    if total_skills >= 20:
        score += 25
    elif total_skills >= 15:
        score += 20
    elif total_skills >= 10:
        score += 15
    elif total_skills >= 5:
        score += 10
    elif total_skills >= 1:
        score += 5

    # -----------------------------
    # 4. EXPERIENCE / PROJECTS (20)
    # -----------------------------

    experience_keywords = [
        "intern",
        "internship",
        "project",
        "experience",
        "developer",
        "engineer",
        "research"
    ]

    action_verbs = [
        "developed",
        "built",
        "implemented",
        "designed",
        "created",
        "optimized",
        "integrated",
        "deployed",
        "automated",
        "analyzed"
    ]

    exp_score = 0

    if any(word in text for word in experience_keywords):
        exp_score += 10

    verb_count = 0

    for verb in action_verbs:
        verb_count += text.count(verb)

    if verb_count >= 8:
        exp_score += 5
    elif verb_count >= 4:
        exp_score += 3
    elif verb_count >= 1:
        exp_score += 2

    numbers = len(re.findall(r"\d+%|\d+\+|\d+", text))

    if numbers >= 5:
        exp_score += 5
    elif numbers >= 2:
        exp_score += 3

    score += min(exp_score,20)

    # -----------------------------
    # 5. EDUCATION (10)
    # -----------------------------

    education_words = [
        "b.tech",
        "btech",
        "bachelor",
        "university",
        "college",
        "cgpa",
        "gpa",
        "graduation"
    ]

    edu_found = 0

    for word in education_words:

        if word in text:
            edu_found += 1

    if edu_found >= 4:
        score += 10
    elif edu_found >= 2:
        score += 7
    elif edu_found >= 1:
        score += 4

    # -----------------------------
    # 6. ACTION VERBS (10)
    # -----------------------------

    if verb_count >= 10:
        score += 10
    elif verb_count >= 7:
        score += 8
    elif verb_count >= 4:
        score += 5
    elif verb_count >= 2:
        score += 3

    # -----------------------------
    # 7. WORD COUNT (10)
    # -----------------------------

    words = len(text.split())

    if 350 <= words <= 900:
        score += 10
    elif 250 <= words < 350:
        score += 8
    elif 900 < words <= 1200:
        score += 7
    elif words < 200:
        score -= 5
    elif words > 1500:
        score -= 5

    # -----------------------------
    # 8. PENALTIES
    # -----------------------------

    penalties = 0

    important_skills = [
        "git",
        "github",
        "sql"
    ]

    for skill in important_skills:

        if skill not in found_skills:
            penalties += 2

    if "projects" not in text:
        penalties += 5

    score -= penalties

    score = max(0, min(score,100))

    return score, found_skills


def calculate_job_match(skills_found):

    jobs = {

        "Frontend Developer": [
            "html",
            "css",
            "javascript",
            "react",
            "git"
        ],

        "Backend Developer": [
            "python",
            "sql",
            "fastapi",
            "mysql",
            "git"
        ],

        "Full Stack Developer": [
            "html",
            "css",
            "javascript",
            "react",
            "python",
            "sql",
            "fastapi"
        ],

        "AI Engineer": [
            "python",
            "sql",
            "docker",
            "aws"
        ],

        "Cloud Engineer": [
            "aws",
            "docker",
            "git"
        ]
    }

    results = []

    for role, required_skills in jobs.items():

        matched = 0

        for skill in required_skills:

            if skill in skills_found:
                matched += 1

        percentage = int(
            (matched / len(required_skills)) * 100
        )

        results.append({
            "role": role,
            "match_percentage": percentage
        })

    results.sort(
        key=lambda x: x["match_percentage"],
        reverse=True
    )

    return results


@app.post("/register")
def register(user: UserCreate):

    db: Session = SessionLocal()

    new_user = User(
        name=user.name,
        email=user.email,
        password=user.password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    db.close()

    return {
        "message": "User Registered Successfully",
        "user_id": new_user.id
    }


@app.post("/login")
def login(user: UserLogin):

    db = SessionLocal()

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        print("User found:", existing_user.email)
        print("Stored password:", existing_user.password)
        print("Entered password:", user.password)
    else:
        print("User NOT found")

    db.close()

    if not existing_user:
        raise HTTPException(status_code=401, detail="Email not found")

    if existing_user.password != user.password:
        raise HTTPException(status_code=401, detail="Wrong password")

    return {
        "message": "Login Successful",
        "user_id": existing_user.id,
        "name": existing_user.name,
        "email": existing_user.email
    }


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):

    global latest_resume_text

    file_path = f"uploads/{file.filename}"

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    reader = PdfReader(file_path)

    text = ""

    for page in reader.pages:

        page_text = page.extract_text()

        if page_text:
            text += page_text
    import re
    text = re.sub(r'(?<=\w)\s+(?=\w)', '', text)
    latest_resume_text = text

    score, skills = calculate_ats_score(text)
    

    analysis = analyze_resume(text)
    
    if score >= 85:
        strength = "Excellent"
    elif score >= 70:
        strength = "Strong"
    elif score >= 55:
        strength = "Average"
    elif score >= 40:
        strength = "Needs Improvement"
    else:
        strength = "Weak"
    
    return {
    
        "filename": file.filename,
    
        "ats_score": score,
    
        "skills_found": skills,
    
        "resume_strength": strength,
    
        "summary": analysis["summary"],
    
        "strengths": analysis["strengths"],
    
        "weaknesses": analysis["weaknesses"],
    
        "missing_skills": analysis["missing_skills"],
    
        "recommended_roles": analysis["recommended_roles"],
    
        "improvement_suggestions": analysis["improvement_suggestions"],
    
        "recommended_projects": analysis["recommended_projects"],
    
        "interview_questions": analysis["interview_questions"]
}


@app.get("/generate-interview")
def generate_interview():

    global latest_resume_text

    if not latest_resume_text:
        raise HTTPException(
            status_code=400,
            detail="Please upload and analyze a resume first."
        )

    questions = generate_mock_interview(
        latest_resume_text
    )

    print("QUESTIONS:", questions)

    return questions


@app.get("/users")
def get_users():

    db = SessionLocal()

    users = db.query(User).all()

    result = []

    for user in users:

        result.append({

            "id": user.id,
            "name": user.name,
            "email": user.email,
            "password" : user.password

        })

    db.close()

    return result
