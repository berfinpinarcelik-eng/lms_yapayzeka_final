import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Destekli LMS", page_icon="🎓", layout="wide")

st.title("🎓 AI Destekli Eğitim Yönetim Sistemi (LMS)")

# Sidebar model seçimi
st.sidebar.header("Ayarlar")
selected_model = st.sidebar.selectbox("Yapay Zeka Modeli Seçin", ["Gemini", "Groq"])

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
                        col1, col2, col3 = st.columns(3)
                        
                        req_data = {
                            "course_id": c['id'],
                            "model_name": selected_model
                        }

                        if col1.button("📝 Konuyu Özetle", key=f"sum_{c['id']}"):
                            with st.spinner(f"{selected_model} Özet Çıkarıyor..."):
                                req_data["operation_type"] = "summary"
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.success(ai_res.json().get("response"))
                                else:
                                    st.error(f"Hata: {ai_res.text}")

                        if col2.button("❓ Quiz Hazırla", key=f"quiz_{c['id']}"):
                             with st.spinner(f"{selected_model} Quiz Oluşturuyor..."):
                                req_data["operation_type"] = "quiz"
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.success(ai_res.json().get("response"))
                                else:
                                    st.error(f"Hata: {ai_res.text}")
                                    
                        if col3.button("🗣️ Basitçe Anlat", key=f"exp_{c['id']}"):
                             with st.spinner(f"{selected_model} Konuyu Açıklıyor..."):
                                req_data["operation_type"] = "explain"
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.success(ai_res.json().get("response"))
                                else:
                                    st.error(f"Hata: {ai_res.text}")
                                    
                        st.markdown("**Özel Soru Sor:**")
                        custom_q = st.text_input(f"{c['title']} hakkında bir soru sorun", key=f"q_{c['id']}")
                        if st.button("Sor", key=f"ask_{c['id']}"):
                            with st.spinner(f"{selected_model} Düşünüyor..."):
                                req_data["operation_type"] = "custom"
                                req_data["custom_prompt"] = custom_q
                                ai_res = requests.post(f"{API_URL}/ai_action/", json=req_data)
                                if ai_res.status_code == 200:
                                    st.success(ai_res.json().get("response"))
                                else:
                                    st.error(f"Hata: {ai_res.text}")

        else:
            st.error("API'ye ulaşılamıyor. Lütfen FastAPI sunucusunun çalıştığından emin olun.")
    except Exception as e:
        st.error(f"Bağlantı Hatası: Sunucu kapalı olabilir. `uvicorn ai_service:app` komutunu çalıştırdınız mı? Hata: {e}")

