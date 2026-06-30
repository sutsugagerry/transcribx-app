import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore

# Konfigurasi Halaman (Wajib di paling atas)
st.set_page_config(page_title="TranscribX - Enterprise AI", layout="wide")

# =====================================================================
# CSS UNTUK MENYEMBUNYIKAN TOOLBAR STREAMLIT (Kanan Atas)
# =====================================================================
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            .stApp > header {
                background-color: transparent;
            }
            .st-emotion-cache-1vt4ygl {
                display: none;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# =====================================================================
# INISIALISASI FIREBASE ADMIN
# =====================================================================
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase_admin"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =====================================================================
# FUNGSI FIREBASE REST API & MANAGEMENT
# =====================================================================
def login_firebase(email, password):
    api_key = st.secrets["FIREBASE_WEB_API_KEY"]
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=data).json()

def register_firebase(email, password):
    api_key = st.secrets["FIREBASE_WEB_API_KEY"]
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={api_key}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=data).json()

def check_subscription(uid):
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict().get("status_subscription", "non-aktif")
    return "non-aktif"

def get_user_data(uid):
    """Mengambil seluruh data profil dan kuota user dari Firestore"""
    doc = db.collection("users").document(uid).get()
    if doc.exists:
        return doc.to_dict()
    return {}

def deduct_quota(uid, quota_type):
    """Memotong kuota spesifik sebanyak 1 poin"""
    db.collection("users").document(uid).update({
        quota_type: firestore.Increment(-1)
    })

# =====================================================================
# FUNGSI BACKEND AI PROCESSING (Guna Mengamankan API Key Anda)
# =====================================================================
def process_ai_summary(transcript_text):
    """Memproses Summary via backend Streamlit menggunakan sk-key Anda"""
    llm_key = st.secrets["LITELLM_API_KEY"]
    url = "https://litellm.koboi2026.biz.id/v1/chat/completions"
    headers = {"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"}
    
    prompt = f"""Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
    ATURAN JSON NOTULENSI:
    - ringkasan_eksekutif: Buat array of strings (poin-poin padat).
    - jalannya_diskusi: Buat array of strings. WAJIB NARASI DETAIL, PANJANG, dan LENGKAP untuk setiap poin kronologis agar tidak ada info hilang.
    - keputusan: Array of strings. Kesimpulan utama.
    - rencana_tindak_lanjut: Ekstrak tabel penugasan. JIKA TIDAK ADA TUGAS spesifik, WAJIB BUAT 1 TUGAS DEFAULT.
    - hubungan_topik (CYTOSCAPE): Ekstrak 5-15 entitas penting dan hubungannya.

    ATURAN MARKMAP (PENTING!):
    Gunakan kode murni markdown. Isi Markmap HARUS RINGKAS berupa poin-poin. WAJIB ikuti pola ini: # [Judul] ## Ringkasan Eksekutif ## Agenda ## Peserta ## Jalannya Diskusi ## Kendala & Solusi ## Keputusan Utama ## Rencana Tindak Lanjut
    ATURAN MERMAID: WAJIB format 'graph LR' dengan tanda kutip ganda pada node (A["Teks"]). Root diagram WAJIB berisi Judul Topik Rapat/Agenda.
    
    Transkrip Rapat: "{transcript_text}" """

    payload = {
        "model": "gemini/gemini-2.5-flash", 
        "messages": [{"role": "user", "content": prompt}], 
        "temperature": 0.2,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "meeting_summary", "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "ringkasan_eksekutif": { "type": "array", "items": { "type": "string" } },
                        "notulensi_rapat": {
                            "type": "object",
                            "properties": {
                                "agenda": { "type": "string" }, "peserta": { "type": "array", "items": { "type": "string" } },
                                "jalannya_diskusi": { "type": "array", "items": { "type": "string" } }, "keputusan": { "type": "array", "items": { "type": "string" } },
                                "rencana_tindak_lanjut": { "type": "array", "items": { "type": "object", "properties": { "tugas": { "type": "string" }, "pic": { "type": "string" }, "deadline": { "type": "string" }, "prioritas": { "type": "string" } }, "required": ["tugas", "pic", "deadline", "prioritas"], "additionalProperties": false } },
                                "hubungan_topik": { "type": "array", "items": { "type": "object", "properties": { "sumber": { "type": "string" }, "target": { "type": "string" }, "relasi": { "type": "string" } }, "required": ["sumber", "target", "relasi"], "additionalProperties": false } }
                            }, "required": ["agenda", "peserta", "jalannya_diskusi", "keputusan", "rencana_tindak_lanjut", "hubungan_topik"], "additionalProperties": false
                        },
                        "visual_mindmap": { "type": "string" }, "markmap_code": { "type": "string" }
                    }, "required": ["ringkasan_eksekutif", "notulensi_rapat", "visual_mindmap", "markmap_code"], "additionalProperties": false
                }
            }
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code == 200:
        return json.loads(res.json()["choices"][0]["message"]["content"]), True
    return res.text, False

# =====================================================================
# SIDEBAR RADAR & ICON GERMIC
# =====================================================================
with st.sidebar:
    st.markdown("<h3 style='text-align: center; color: #475569;'>🤖 AI Assistant</h3>", unsafe_allow_html=True)
    germic_html = """
    <style>
        @keyframes float { 0%, 100% { transform: translateY(0px) rotate(0deg); } 50% { transform: translateY(-15px) rotate(2deg); } }
        @keyframes signal { 0% { transform: scale(0.5); opacity: 0; } 50% { opacity: 1; } 100% { transform: scale(1.5); opacity: 0; } }
        body { margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 250px; background-color: transparent; overflow: hidden; }
        .germic-container { width: 180px; height: 180px; animation: float 4s ease-in-out infinite; position: relative; cursor: pointer; }
        .signal-wave { transform-origin: 50px 12px; animation: signal 2s infinite; }
        .signal-wave-2 { transform-origin: 50px 12px; animation-delay: 0.6s; animation: signal 2s infinite; }
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    </style>
    <div id="germic-wrapper" class="germic-container">
        <svg width="100%" height="100%" viewBox="0 0 100 100" fill="none">
            <circle class="signal-wave" cx="50" cy="12" r="8" stroke="#fb7185" stroke-width="1" />
            <circle class="signal-wave signal-wave-2" cx="50" cy="12" r="8" stroke="#fb7185" stroke-width="1" />
            <path d="M50 25V15M50 15L45 10M50 15L55 10" stroke="#3b82f6" stroke-width="2" stroke-linecap="round"/>
            <circle cx="50" cy="12" r="3" fill="#fb7185" class="animate-pulse"/>
            <rect x="5" y="45" width="8" height="20" rx="4" fill="#1e293b"/>
            <rect x="87" y="45" width="8" height="20" rx="4" fill="#1e293b"/>
            <rect x="15" y="25" width="70" height="65" rx="18" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="2"/>
            <rect x="22" y="35" width="56" height="40" rx="12" fill="#1e1b4b"/>
            <g id="germic-face">
                <rect id="eye-l" x="33" y="45" width="12" height="15" rx="3" fill="#38bdf8"/>
                <rect id="eye-r" x="55" y="45" width="12" height="15" rx="3" fill="#38bdf8"/>
                <rect id="mouth" x="42" y="65" width="16" height="3" rx="1.5" fill="#818cf8"/>
            </g>
        </svg>
    </div>
    """
    components.html(germic_html, height=250)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 13px; font-weight: bold;'>GERMIC System Online</p>", unsafe_allow_html=True)
    st.markdown("---")

# =====================================================================
# CONFIG SESSION STATE
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "offline_transcript" not in st.session_state:
    st.session_state["offline_transcript"] = ""
if "offline_summary" not in st.session_state:
    st.session_state["offline_summary"] = None
if "live_summary_result" not in st.session_state:
    st.session_state["live_summary_result"] = None

# =====================================================================
# GATE KEEPER: PORTAL LOGIN
# =====================================================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.markdown("<h2 style='text-align: center;'>🔒 Portal TranscribX Enterprise</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            email_login = st.text_input("Email", placeholder="email@klien.com")
            pass_login = st.text_input("Password", type="password")
            btn_login = st.form_submit_button("🚀 Masuk ke Sistem", use_container_width=True)
            if btn_login and email_login and pass_login:
                user_data = login_firebase(email_login, pass_login)
                if "idToken" in user_data:
                    uid = user_data["localId"]
                    if check_subscription(uid) == "aktif":
                        st.session_state["logged_in"] = True
                        st.session_state["user_email"] = email_login
                        st.session_state["user_uid"] = uid
                        st.rerun()
                    else:
                        st.error("⚠️ Masa aktif akun habis atau status belum diaktifkan oleh Admin.")
                else:
                    st.error(f"⚠️ {user_data.get('error', {}).get('message', 'Kredensial salah.')}")

# =====================================================================
# CORE APPLICATION ENGINE (Setelah Login)
# =====================================================================
else:
    colA, colB = st.columns([8, 1])
    with colB:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ TranscribX: Enterprise Transcription & AI Summarizer")
    
    ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "admin@domain.com")
    user_uid = st.session_state["user_uid"]
    
    # Sinkronisasi sisa kuota user dari DB
    u_profile = get_user_data(user_uid)
    quota_live = u_profile.get("live_summary_quota", 0)
    quota_upload = u_profile.get("upload_quota", 0)
    current_tier = u_profile.get("tier_package", "Basic")

    # Tampilkan Badge Kuota Di Atas Layar Utama
    st.markdown(f"""
    <div style="background-color:#f8fafc; padding:15px; border-radius:15px; border:1px solid #e2e8f0; margin-bottom:20px; display:flex; gap:20px; align-items:center;">
        <div>👤 User: <b>{st.session_state["user_email"]}</b></div>
        <div style="background-color:#e0f2fe; color:#0369a1; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:bold;">Paket: {current_tier.upper()}</div>
        <div style="margin-left:auto;">⚡ Sisa Kuota Summary Live: <b>{quota_live}</b> | 📁 Sisa Kuota Upload: <b>{quota_upload}</b></div>
    </div>
    """, unsafe_allow_html=True)

    # PEMBAGIAN TAB
    if st.session_state.get("user_email") == ADMIN_EMAIL:
        tabs = st.tabs(["👑 Admin Panel", "🔴 Live Zoom (Web API)", "📁 Upload Rekaman (Offline LiteLLM)"])
        tab_admin, tab1, tab2 = tabs[0], tabs[1], tabs[2]
        
        # --- TAB ADMIN PANEL (TEMPAT SETTING TIERING) ---
        with tab_admin:
            st.markdown("### 👑 Dashboard Admin: Registrasi & Pengaturan Paket Klien")
            with st.form("admin_register_form", clear_on_submit=True):
                col_reg1, col_reg2 = st.columns(2)
                with col_reg1:
                    email_reg = st.text_input("Email Klien Baru", placeholder="email@klien.com")
                with col_reg2:
                    pass_reg = st.text_input("Password Klien", type="password")
                
                # Input Tiering Paket Baru
                selected_tier = st.selectbox("Pilih Paket Langganan", ["Basic (Rp 29k)", "Executive (Rp 49k)", "Master (Rp 129k)"])
                status_reg = st.selectbox("Status Langganan Awal", ["aktif", "non-aktif"])
                btn_reg = st.form_submit_button("📝 Daftarkan & Suntik Kuota", type="primary")
                
                if btn_reg and email_reg and len(pass_reg) >= 6:
                    new_user = register_firebase(email_reg, pass_reg)
                    if "idToken" in new_user:
                        uid = new_user["localId"]
                        
                        # Logika Aturan Distribusi Kuota Berdasarkan Paket Terpilih
                        if "Basic" in selected_tier:
                            l_q, u_q, t_name = 5, 1, "Basic"
                        elif "Executive" in selected_tier:
                            l_q, u_q, t_name = 10, 3, "Executive"
                        else:
                            l_q, u_q, t_name = 30, 10, "Master"
                            
                        db.collection("users").document(uid).set({
                            "email": email_reg,
                            "status_subscription": status_reg,
                            "tier_package": t_name,
                            "live_summary_quota": l_q,
                            "upload_quota": u_q,
                            "transcribe_live_unlimited": True
                        })
                        st.success(f"✅ Akun {email_reg} berhasil disuntik paket {t_name}!")
                        st.rerun()
                    else:
                        st.error(f"⚠️ Gagal: {new_user.get('error', {}).get('message', 'Error')}")

            # DAFTAR USER YANG SUDAH TERSEDIA DI DB
            st.markdown("---")
            st.markdown("### 📋 Daftar Klien & Sisa Kuota Terkini")
            users_ref = db.collection("users").stream()
            users_list = []
            for doc in users_ref:
                u = doc.to_dict()
                users_list.append({
                    "Email Klien": u.get("email", "-"),
                    "Paket": u.get("tier_package", "Basic"),
                    "Sisa Summary Live": u.get("live_summary_quota", 0),
                    "Sisa Upload": u.get("upload_quota", 0),
                    "Status": u.get("status_subscription", "non-aktif")
                })
            st.dataframe(pd.DataFrame(users_list), use_container_width=True, hide_index=True)
    else:
        tabs = st.tabs(["🔴 Live Zoom (Web API)", "📁 Upload Rekaman (Offline LiteLLM)"])
        tab1, tab2 = tabs[0], tabs[1]

    # =====================================================================
    # TAB 1: LIVE CAPTURE (Web Speech API - Rp 0 Bebas Kuota)
    # =====================================================================
    with tab1:
        st.markdown("Mesin **Web Speech API** otomatis berjalan tanpa memotong kuota Anda sewaktu merekam.")
        
        # Jembatan Input Teks Mentah dari Sisi Klien ke Sisi Server (Aman dari pembajakan Key)
        st.markdown("#### 💬 Eksekusi AI Summary")
        with st.expander("Prosedur Generate AI Summary"):
            st.caption("1. Lakukan Perekaman pada panel di bawah hingga selesai.")
            st.caption("2. Copy teks final dari layar lalu paste ke dalam box di bawah ini.")
            st.caption("3. Tekan tombol 'Proses AI' untuk menghasilkan Notulensi lengkap & Mindmap.")
            
        txt_to_process = st.text_area("Paste Teks Transkrip Rapat di Sini:", height=150, placeholder="Hasil rekaman...")
        
        # Validasi Tombol Berdasarkan Sisa Kuota Live Pengguna
        is_live_disabled = quota_live <= 0
        if is_live_disabled:
            st.error("❌ Kuota Live AI Summary Anda telah habis (0). Silakan lakukan upgrade paket.")
            
        if st.button("✨ Generate AI Summary (Potong 1 Kuota)", disabled=is_live_disabled, type="primary"):
            if not txt_to_process.strip():
                st.warning("Kotak transkrip teks kosong!")
            else:
                with st.spinner("⏳ Menghubungi Server AI..."):
                    res_data, success = process_ai_summary(txt_to_process)
                    if success:
                        st.session_state["live_summary_result"] = res_data
                        deduct_quota(user_uid, "live_summary_quota")
                        st.success("✅ Berhasil! Jatah Kuota Summary berkurang 1.")
                        st.rerun()
                    else:
                        st.error(f"Gagal memproses AI: {res_data}")

        # Menampilkan Output JSON Jika Proses Berhasil
        if st.session_state["live_summary_result"]:
            data_res = st.session_state["live_summary_result"]
            st.success("🤖 NOTULENSI AI RAFIK READY:")
            st.write(data_res.get("ringkasan_eksekutif", []))
            st.table(pd.DataFrame(data_res["notulensi_rapat"]["rencana_tindak_lanjut"]))

        st.markdown("---")
        st.markdown("#### 🎙️ Panel Perekaman Live Rapat (Unlimited)")
        
        # Embedded HTML Recorder System (Murni Sisi Depan Browser Klien)
        html_code = """
        <!DOCTYPE html><html><head><script src="https://cdn.tailwindcss.com"></script><style>body{font-family:'Inter',sans-serif;background:transparent;margin:0;}.transcript-box{border:2px solid #cbd5e1;padding:20px;border-radius:16px;height:300px;overflow-y:auto;background:white;}.btn-custom{background:#3b82f6;color:white;padding:10px 20px;border-radius:8px;font-weight:bold;cursor:pointer;}.line-final{margin-bottom:12px;padding:12px;background:#f1f5f9;border-radius:8px;border-left:4px solid #3b82f6;font-size:14px;}</style></head>
        <body>
            <div class="flex gap-4 mb-4 items-center">
                <button id="startBtn" class="btn-custom">🚀 START CAPTURE (GRATIS)</button>
                <button id="stopBtn" class="btn-custom bg-red-500" disabled>⏹️ STOP</button>
                <button id="copyBtn" class="btn-custom bg-gray-500">📋 COPY ALL TEXT</button>
                <span id="status" class="font-bold text-gray-500">Standby...</span>
            </div>
            <div id="transcriptBox" class="transcript-box"><div id="placeholder" class="text-center text-gray-400 mt-20">Klik 'Start' dan silakan berbicara atau putar audio rapat...</div></div>
            <script>
                const startBtn=document.getElementById('startBtn'),stopBtn=document.getElementById('stopBtn'),copyBtn=document.getElementById('copyBtn'),transcriptBox=document.getElementById('transcriptBox'),status=document.getElementById('status');
                let rec,isRec=false;
                if(!('webkitSpeechRecognition' in window)&&!('SpeechRecognition' in window)){ status.innerText="Browser tidak mendukung Speech API."; }else{
                    const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;rec=new SpeechRecognition();rec.continuous=true;rec.interimResults=false;rec.lang='id-ID';
                    rec.onresult=(e)=>{
                        document.getElementById('placeholder').style.display='none';
                        let f='';for(let i=e.resultIndex;i<e.results.length;++i){if(e.results[i].isFinal)f+=e.results[i][0].transcript;}
                        if(f){const d=document.createElement('div');d.className='line-final';d.innerText=f;transcriptBox.appendChild(d);transcriptBox.scrollTop=transcriptBox.scrollHeight;}
                    };
                    rec.onend=()=>{if(isRec)rec.start();};
                    startBtn.onclick=()=>{rec.start();isRec=true;startBtn.disabled=true;stopBtn.disabled=false;status.innerText="Merekam Aktif (Rp 0)...";status.className="text-red-500 font-bold";};
                    stopBtn.onclick=()=>{isRec=false;rec.stop();startBtn.disabled=false;stopBtn.disabled=true;status.innerText="Standby";status.className="text-gray-500 font-bold";};
                    copyBtn.onclick=()=>{const txt=Array.from(transcriptBox.querySelectorAll('.line-final')).map(l=>l.innerText).join('\\n');navigator.clipboard.writeText(txt);alert('Teks berhasil disalin ke clipboard! Silakan paste di box atas.');};
                }
            </script>
        </body></html>
        """
        components.html(html_code, height=450)

    # =====================================================================
    # TAB 2: UPLOAD REKAMAN OFFLINE (Memotong Kuota Jatah Whisper)
    # =====================================================================
    with tab2:
        st.markdown("### 📁 Transkripsi File Rekaman (Offline)")
        st.info("Setiap file yang diproses akan memakan jatah modal token Whisper Anda.")

        is_upload_disabled = quota_upload <= 0
        if is_upload_disabled:
            st.error("❌ Kuota pemrosesan file audio Anda sudah habis (0). Silakan lakukan upgrade paket Anda.")

        uploaded_file = st.file_uploader("Upload File Rekaman Anda", type=["mp3", "wav", "m4a", "mp4"])

        if uploaded_file is not None:
            if uploaded_file.size > 26214400: 
                st.error("⚠️ Ukuran file melebihi batas sistem 25MB.")
            else:
                st.audio(uploaded_file)
                
                # Mengunci eksekusi jika kuota dari database habis
                if st.button("🎙️ Mulai Transkripsi (Potong 1 Kuota)", disabled=is_upload_disabled, type="primary"):
                    with st.spinner("⏳ Sedang memproses transkripsi file media (Whisper AI)..."):
                        try:
                            llm_key = st.secrets["LITELLM_API_KEY"]
                            url = "https://litellm.koboi2026.biz.id/v1/audio/transcriptions"
                            headers = {"Authorization": f"Bearer {llm_key}"}
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            data = {"model": "whisper-1", "response_format": "json"}
                            
                            response = requests.post(url, headers=headers, files=files, data=data)

                            if response.status_code == 200:
                                transcript_text = response.json().get("text", "")
                                st.session_state["offline_transcript"] = transcript_text
                                
                                # Otomatis langsung buat Summary
                                st.markdown("#### Proses Pembuatan Notulensi...")
                                res_json, ai_ok = process_ai_summary(transcript_text)
                                
                                if ai_ok:
                                    st.session_state["offline_summary"] = res_json
                                    # Poin krusial: Kuota dipotong hanya jika sukses
                                    deduct_quota(user_uid, "upload_quota")
                                    st.success("✅ File berhasil diproses secara penuh!")
                                    st.rerun()
                                else:
                                    st.error(f"Gagal menyusun ringkasan: {res_json}")
                            else: 
                                st.error(f"Gagal Whisper: {response.text}")
                        except Exception as e: 
                            st.error(f"Koneksi Gagal: {str(e)}")

        # Tampilkan data keluaran summary jika ada
        if st.session_state["offline_summary"]:
            st.markdown("#### 📋 Hasil Dokumen Hasil Rapat (Arsip)")
            st.json(st.session_state["offline_summary"])
