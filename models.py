from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel
from typing import List, Optional

# SQLAlchemy Models (Veritabanı Tabloları)
class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), index=True, nullable=False)
    description = Column(Text, nullable=True)
    materials = Column(Text, nullable=True) # Ders içerikleri metin olarak
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    logs = relationship("AILog", back_populates="course")


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    model_used = Column(String(50)) # gemini, groq v.b.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course", back_populates="logs")


# Pydantic Models (Uygulama/API Şemaları)
class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    materials: Optional[str] = None

class CourseOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    materials: Optional[str] = None

    class Config:
        from_attributes = True

class AIOperationRequest(BaseModel):
    course_id: int
    operation_type: str # 'summary', 'quiz', 'explain'
    custom_prompt: Optional[str] = None
    model_name: str # 'gemini' or 'groq'

class AIResponseInfo(BaseModel):
    response: str
    model_used: str
