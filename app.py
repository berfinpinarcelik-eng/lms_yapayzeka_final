import streamlit as st
import io
import os
import zipfile
from fpdf import FPDF
from dotenv import load_dotenv
import google.generativeai as genai
from groq import Groq
from sqlalchemy.orm import Session

# Local database imports
import database
import models

# Environment setup
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# AI Configuration
if GEMINI_KEY and GEMINI_KEY != "buraya_kendi_gemini_api_keyinizi_yazin":
    genai.configure(api_key=GEMINI_KEY)
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY and GROQ_KEY != "buraya_kendi_groq_api_keyinizi_yazin" else None

# Database Initialization
models.Base.metadata.create_all(bind=database.engine)

def text_to_ascii(text: str) -> str:
    # Önce Türkçe karakterleri standart harflere çevir
    replacements = {'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C', 'ü': 'u', 'Ü': 'U'}
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    # Ardından PDF'in (Helvetica) desteklemediği tüm özel sembolleri (emoji vb.) temizle
    return "".join(c for c in text if ord(c) < 128)

def create_pdf(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)
    safe_text = text_to_ascii(text)
    pdf.multi_cell(0, 6, text=safe_text)
    return bytes(pdf.output())

def create_project_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            if any(x in root for x in [".git", "__pycache__", ".gemini"]):
                continue
            for f in files:
                if f in ["lms.db", "lms_backup.db", ".env"]:
                    continue
                file_path = os.path.join(root, f)
                zf.write(file_path, file_path)
    return buf.getvalue()

def run_ai_action(course_id, operation_type, model_name, custom_prompt=None):
    db = next(database.get_db())
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        return "Kurs bulunamadı."

    content = course.materials or course.description or ""
    
    # Prompt preparation
    system_prompt = ""
    if operation_type == "summary":
        system_prompt = f"Şu ders içeriğini anlaşılır ve yapılandırılmış bir şekilde özetle:\n\n{content}"
    elif operation_type == "quiz":
        system_prompt = f"Şu ders içeriğine dayanarak 3 soruluk bir çoktan seçmeli quiz hazırla (cevap anahtarı ile birlikte):\n\n{content}"
    elif operation_type == "explain":
        system_prompt = f"Şu konudaki ders içeriklerini basit bir şekilde anlat:\n\n{content}"
    else:
        q = custom_prompt or "Merhaba"
        system_prompt = f"Ders içeriği: {content}\n\nSoru: {q}"

    response_text = ""
    try:
        if model_name.lower() == "gemini":
            if not GEMINI_KEY: return "Gemini API anahtarı eksik."
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(system_prompt)
            response_text = response.text
        elif model_name.lower() == "groq":
            if not groq_client: return "Groq API anahtarı eksik."
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": system_prompt}],
                model="llama-3.3-70b-versatile",
            )
            response_text = chat_completion.choices[0].message.content
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg:
            return "KOTA HATASI: Gemini limiti doldu. Lütfen biraz bekleyin veya Groq modelini deneyin."
        return f"AI Hatası: {error_msg}"

    # Log action
    ai_log = models.AILog(course_id=course.id, prompt=system_prompt, response=response_text, model_used=model_name.lower())
    db.add(ai_log)
    db.commit()
    return response_text

st.set_page_config(page_title="AI Destekli LMS", page_icon="🎓", layout="wide")
st.title("🎓 AI Destekli Eğitim Yönetim Sistemi (LMS)")

# Sidebar
st.sidebar.header("Ayarlar")
selected_model = st.sidebar.selectbox("Yapay Zeka Modeli Seçin", ["Groq", "Gemini"])
st.sidebar.markdown("---")
st.sidebar.header("📥 Projeyi İndir")
st.sidebar.download_button("📦 Kaynak Kodu İndir (.zip)", data=create_project_zip(), file_name="ai_lms_project.zip", mime="application/zip")

# Tabs
tab1, tab2 = st.tabs(["📚 Tüm Kurslar", "➕ Yeni Kurs Ekle"])

with tab2:
    st.subheader("Yeni Kurs/Ders Ekle")
    with st.form("add_course_form"):
        title = st.text_input("Kurs Başlığı")
        description = st.text_area("Kısa Açıklama")
        materials = st.text_area("Ders İçeriği / Notlar", height=200)
        submitted = st.form_submit_button("Kursu Ekle")
        
        if submitted:
            if title and materials:
                db = next(database.get_db())
                new_course = models.Course(title=title, description=description, materials=materials)
                db.add(new_course)
                db.commit()
                st.success(f"'{title}' başarıyla eklendi!")
                st.rerun()
            else:
                st.warning("Başlık ve içeriği eksik bırakmayın.")

with tab1:
    st.subheader("Mevcut Kurslar")
    db = next(database.get_db())
    courses = db.query(models.Course).all()
    
    if not courses:
        st.info("Henüz eklenmiş bir kurs bulunmuyor.")
    else:
        for c in courses:
            with st.expander(f"📖 {c.title} - {c.description[:50] if c.description else ''}..."):
                st.markdown("**Ders İçeriği (Önizleme):**")
                mat = c.materials or ""
                st.info(mat[:300] + "..." if len(mat) > 300 else mat)
                
                st.markdown("---")
                st.markdown("### 🤖 Yapay Zeka Asistanı")
                col1, coldl1, col2, coldl2, col3, coldl3 = st.columns([3, 2, 3, 2, 3, 2])
                
                # Operation Logic
                ops = [("sum", "Özet", col1, coldl1), ("quiz", "Quiz", col2, coldl2), ("exp", "Anlat", col3, coldl3)]
                for code, name, btn_col, dl_col in ops:
                    if btn_col.button(f"📝 {name}", key=f"{code}_{c.id}", use_container_width=True):
                        with st.spinner(f"{selected_model} çalışıyor..."):
                            full_type = "summary" if code == "sum" else "quiz" if code == "quiz" else "explain"
                            res = run_ai_action(c.id, full_type, selected_model)
                            st.session_state[f"res_{code}_{c.id}"] = res
                    
                    state_key = f"res_{code}_{c.id}"
                    if state_key in st.session_state:
                        dl_col.download_button("📥 PDF", data=create_pdf(st.session_state[state_key]), file_name=f"{code}_{c.id}.pdf", key=f"dl_{code}_{c.id}", use_container_width=True)

                # Results display
                for code, name, _, _ in ops:
                    s_key = f"res_{code}_{c.id}"
                    if s_key in st.session_state:
                        st.success(f"**{name}:**\n\n{st.session_state[s_key]}")

                st.markdown("**Özel Soru Sor:**")
                custom_q = st.text_input("Bir soru sorun", key=f"q_{c.id}")
                if st.button("Sor", key=f"ask_{c.id}"):
                    with st.spinner("Düşünüyor..."):
                        res = run_ai_action(c.id, "custom", selected_model, custom_q)
                        st.session_state[f"res_custom_{c.id}"] = res
                
                if f"res_custom_{c.id}" in st.session_state:
                    st.info(st.session_state[f"res_custom_{c.id}"])
                    st.download_button("📥 Cevabı İndir", data=create_pdf(st.session_state[f"res_custom_{c.id}"]), file_name=f"cevap_{c.id}.pdf", key=f"dl_c_{c.id}")

