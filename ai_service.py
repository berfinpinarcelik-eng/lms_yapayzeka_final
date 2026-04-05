import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from dotenv import load_dotenv

import database
import models
import google.generativeai as genai
from groq import Groq

# Çevresel değişkenleri yükle
load_dotenv()

# Veri tabanını oluştur
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="AI LMS Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# Configure Gemini
if GEMINI_KEY and GEMINI_KEY != "buraya_kendi_gemini_api_keyinizi_yazin":
    genai.configure(api_key=GEMINI_KEY)

# Initialise Groq
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY and GROQ_KEY != "buraya_kendi_groq_api_keyinizi_yazin" else None

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/courses/", response_model=List[models.CourseOut])
def get_courses(db: Session = Depends(get_db)):
    courses = db.query(models.Course).all()
    return courses

@app.post("/courses/", response_model=models.CourseOut)
def create_course(course: models.CourseCreate, db: Session = Depends(get_db)):
    db_course = models.Course(
        title=course.title, 
        description=course.description, 
        materials=course.materials
    )
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@app.get("/courses/{course_id}", response_model=models.CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.post("/ai_action/", response_model=models.AIResponseInfo)
def ai_action(request: models.AIOperationRequest, db: Session = Depends(get_db)):
    course = db.query(models.Course).filter(models.Course.id == request.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    content = course.materials or course.description or ""
    
    # Prompt hazırlığı
    system_prompt = ""
    if request.operation_type == "summary":
        system_prompt = f"Şu ders içeriğini anlaşılır ve yapılandırılmış bir şekilde özetle:\n\n{content}"
    elif request.operation_type == "quiz":
        system_prompt = f"Şu ders içeriğine dayanarak 3 soruluk bir çoktan seçmeli quiz hazırla (cevap anahtarı ile birlikte):\n\n{content}"
    elif request.operation_type == "explain":
        system_prompt = f"Şu konudaki ders içeriklerini basit bir şekilde anlat:\n\n{content}"
    else:
        system_prompt = request.custom_prompt or "Merhaba, sana nasıl yardımcı olabilirim?"
        system_prompt = f"Ders içeriği: {content}\n\nSoru: {system_prompt}"

    response_text = ""

    # Model çağrıları
    try:
        if request.model_name.lower() == "gemini":
            if not GEMINI_KEY or GEMINI_KEY == "buraya_kendi_gemini_api_keyinizi_yazin":
                 raise HTTPException(status_code=400, detail="Gemini API anahtarı ayarlanmamış.")
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(system_prompt)
            response_text = response.text
        elif request.model_name.lower() == "groq":
            if not groq_client:
                 raise HTTPException(status_code=400, detail="Groq API anahtarı ayarlanmamış.")
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": system_prompt,
                    }
                ],
                model="llama3-70b-8192",
            )
            response_text = chat_completion.choices[0].message.content
        else:
            raise HTTPException(status_code=400, detail="Geçersiz model adı. 'gemini' veya 'groq' kullanın.")
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota exceeded" in error_msg:
            raise HTTPException(status_code=429, detail="Google Gemini kullanım kotanız (rate limit) geçici olarak doldu. Lütfen 30 saniye bekleyip tekrar deneyin veya sol menüden Groq modeline geçiş yapın.")
        raise HTTPException(status_code=500, detail=f"LLM API Hatası: {error_msg}")

    # Log the action in DB
    ai_log = models.AILog(
        course_id=course.id,
        prompt=system_prompt,
        response=response_text,
        model_used=request.model_name.lower()
    )
    db.add(ai_log)
    db.commit()

    return {"response": response_text, "model_used": request.model_name.lower()}

