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


def calculate_ats_score(text):

    text = text.lower()

    skills = {
        "python": 15,
        "java": 15,
        "sql": 10,
        "html": 5,
        "css": 5,
        "javascript": 10,
        "react": 15,
        "fastapi": 15,
        "mysql": 10,
        "git": 10,
        "docker": 15,
        "aws": 20
    }

    score = 0
    found_skills = []

    for skill, points in skills.items():

        if skill in text:
            score += points
            found_skills.append(skill)

    score = min(score, 100)

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
        User.email == user.email,
        User.password == user.password
    ).first()

    db.close()

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid Email or Password"
        )

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

    latest_resume_text = text

    score, skills = calculate_ats_score(text)

    job_matches = calculate_job_match(skills)

    analysis = analyze_resume(text)

    return {

        "filename": file.filename,

        "ats_score": score,

        "skills_found": skills,

        "resume_strength": (
            "Strong"
            if score > 70
            else "Average"
            if score > 40
            else "Weak"
        ),

        "summary": analysis["summary"],

        "strengths": analysis["strengths"],

        "weaknesses": analysis["weaknesses"],

        "missing_skills": analysis["missing_skills"],

        "recommended_roles": analysis["recommended_roles"],

        "improvement_suggestions":
            analysis["improvement_suggestions"],

        "recommended_projects":
            analysis["recommended_projects"],

        "interview_questions":
            analysis["interview_questions"],

        "job_matches": job_matches
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
            "email": user.email

        })

    db.close()

    return result
