import streamlit as st
import requests
import io
import os
import zipfile
from fpdf import FPDF

API_URL = "http://127.0.0.1:8000"

def text_to_ascii(text: str) -> str:
    replacements = {'ğ': 'g', 'Ğ': 'G', 'ş': 's', 'Ş': 'S', 'ı': 'i', 'İ': 'I', 'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C', 'ü': 'u', 'Ü': 'U'}
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text

def create_pdf(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)
    safe_text = text_to_ascii(text)
    # Satır sonlarını pdf'in anlayacağı şekle getir ve multi_cell ile yazdır
    pdf.multi_cell(0, 6, txt=safe_text)
    return bytes(pdf.output())

def create_project_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk("."):
            if ".git" in root or "__pycache__" in root or ".gemini" in root:
                continue
            for f in files:
                if f in ["lms.db", "lms_backup.db", ".env"]:
                    continue
                file_path = os.path.join(root, f)
                zf.write(file_path, file_path)
    return buf.getvalue()

st.set_page_config(page_title="AI Destekli LMS", page_icon="🎓", layout="wide")

st.title("🎓 AI Destekli Eğitim Yönetim Sistemi (LMS)")

# Sidebar model seçimi
st.sidebar.header("Ayarlar")
selected_model = st.sidebar.selectbox("Yapay Zeka Modeli Seçin", ["Groq", "Gemini"])

st.sidebar.markdown("---")
st.sidebar.header("📥 Projeyi İndir")
st.sidebar.markdown("Tüm projeyi **GitHub** kopyası gibi kaynak kodlarıyla indirebilirsiniz.")
st.sidebar.download_button("📦 Kaynak Kodu İndir (.zip)", data=create_project_zip(), file_name="ai_lms_project.zip", mime="application/zip")

# Sekmeler
tab1, tab2 = st.tabs(["📚 Tüm Kurslar", "➕ Yeni Kurs Ekle"])

with tab2:
    st.subheader("Yeni Kurs/Ders Ekle")
    with st.form("add_course_form"):
        title = st.text_input("Kurs Başlığı")
        description = st.text_area("Kısa Açıklama")
        materials = st.text_area("Ders İçeriği / Notlar (AI bunun üzerinden çalışacak)", height=200)
        submitted = st.form_submit_button("Kursu Ekle")
        
        if submitted:
            if title and materials:
                response = requests.post(f"{API_URL}/courses/", json={
                    "title": title,
                    "description": description,
                    "materials": materials
                })
                if response.status_code == 200:
                    st.success(f"'{title}' başarıyla eklendi!")
                    st.rerun()
                else:
                    st.error("Kurs eklenirken hata oluştu.")
            else:
                st.warning("Lütfen başlık ve ders içeriği giriniz.")

with tab1:
    st.subheader("Mevcut Kurslar")
    try:
        response = requests.get(f"{API_URL}/courses/")
        if response.status_code == 200:
            courses = response.json()
            if not courses:
                st.info("Henüz eklenmiş bir kurs bulunmuyor.")
            else:
                for c in courses:
                    with st.expander(f"📖 {c['title']} - {c.get('description', '')[:50]}..."):
                        
                        st.markdown("**Ders İçeriği (Önizleme):**")
                        mat = c.get('materials', '')
                        st.info(mat[:300] + "..." if len(mat) > 300 else mat)
                        
                        st.markdown("---")
                        st.markdown("### 🤖 Yapa Zeka Asistanı")
                        col1, coldl1, col2, coldl2, col3, coldl3 = st.columns([3, 2, 3, 2, 3, 2])
                        
                        req_data = {
                            "course_id": c['id'],
                            "model_name": selected_model
                        }

                        if col1.button("📝 Konuyu Özetle", key=f"sum_{c['id']}", use_container_width=True):
                            with st.spinner(f"{selected_model} Özet Çıkarıyor..."):
                                req_data["operation_type"] = "summary"
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.session_state[f"ai_res_sum_{c['id']}"] = ai_res.json().get("response")
                                else:
                                    st.error(f"Hata: {ai_res.text}")
                        if f"ai_res_sum_{c['id']}" in st.session_state:
                            coldl1.download_button("📥 PDF", data=create_pdf(st.session_state[f"ai_res_sum_{c['id']}"]), file_name=f"ozet_{c['id']}.pdf", mime="application/pdf", key=f"dl_pdf_sum_{c['id']}", use_container_width=True)

                        if col2.button("❓ Quiz Hazırla", key=f"quiz_{c['id']}", use_container_width=True):
                             with st.spinner(f"{selected_model} Quiz Oluşturuyor..."):
                                req_data["operation_type"] = "quiz"
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.session_state[f"ai_res_quiz_{c['id']}"] = ai_res.json().get("response")
                                else:
                                    st.error(f"Hata: {ai_res.text}")
                        if f"ai_res_quiz_{c['id']}" in st.session_state:
                            coldl2.download_button("📥 PDF", data=create_pdf(st.session_state[f"ai_res_quiz_{c['id']}"]), file_name=f"quiz_{c['id']}.pdf", mime="application/pdf", key=f"dl_pdf_quiz_{c['id']}", use_container_width=True)
                                    
                        if col3.button("🗣️ Basitçe Anlat", key=f"exp_{c['id']}", use_container_width=True):
                             with st.spinner(f"{selected_model} Konuyu Açıklıyor..."):
                                req_data["operation_type"] = "explain"
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.session_state[f"ai_res_exp_{c['id']}"] = ai_res.json().get("response")
                                else:
                                    st.error(f"Hata: {ai_res.text}")
                        if f"ai_res_exp_{c['id']}" in st.session_state:
                            coldl3.download_button("📥 PDF", data=create_pdf(st.session_state[f"ai_res_exp_{c['id']}"]), file_name=f"aciklama_{c['id']}.pdf", mime="application/pdf", key=f"dl_pdf_exp_{c['id']}", use_container_width=True)

                        # Sadece sonuç metinlerini aşağıda göster
                        for op_type, display_name in [("sum", "Özet"), ("quiz", "Quiz"), ("exp", "Açıklama")]:
                            state_key = f"ai_res_{op_type}_{c['id']}"
                            if state_key in st.session_state:
                                st.success(f"**{display_name}:**\n\n{st.session_state[state_key]}")
                                    
                        st.markdown("**Özel Soru Sor:**")
                        custom_q = st.text_input(f"{c['title']} hakkında bir soru sorun", key=f"q_{c['id']}")
                        if st.button("Sor", key=f"ask_{c['id']}"):
                            with st.spinner(f"{selected_model} Düşünüyor..."):
                                req_data["operation_type"] = "custom"
                                req_data["custom_prompt"] = custom_q
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.session_state[f"ai_res_custom_{c['id']}"] = ai_res.json().get("response")
                                else:
                                    st.error(f"Hata: {ai_res.text}")
                                    
                        if f"ai_res_custom_{c['id']}" in st.session_state:
                            st.info(st.session_state[f"ai_res_custom_{c['id']}"])
                            st.download_button(
                                label="📥 Sorunun Cevabını PDF İndir",
                                data=create_pdf(st.session_state[f"ai_res_custom_{c['id']}"]),
                                file_name=f"cevap_{c['id']}.pdf",
                                mime="application/pdf",
                                key=f"dl_pdf_custom_{c['id']}"
                            )

        else:
            st.error("API'ye ulaşılamıyor. Lütfen FastAPI sunucusunun çalıştığından emin olun.")
    except Exception as e:
        st.error(f"Bağlantı Hatası: Sunucu kapalı olabilir. `uvicorn ai_service:app` komutunu çalıştırdınız mı? Hata: {e}")

