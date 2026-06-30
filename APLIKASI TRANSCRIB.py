import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import pandas as pd
import firebase_admin
import datetime
from firebase_admin import credentials, firestore

# Konfigurasi Halaman (Hanya boleh dipanggil sekali di paling atas)
st.set_page_config(page_title="TranscribX - Enterprise AI", layout="wide")

# =====================================================================
# CSS UNTUK MENYEMBUNYIKAN TOOLBAR STREAMLIT (Kanan Atas)
# =====================================================================
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            header {visibility: hidden;}
            footer {visibility: hidden;}
            /* Menyembunyikan ikon GitHub/Deploy di versi Streamlit terbaru */
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
# INISIALISASI FIREBASE ADMIN (Dijalankan sekali)
# =====================================================================
if not firebase_admin._apps:
    # Mengambil kredensial dari st.secrets (secrets.toml)
    cred = credentials.Certificate(dict(st.secrets["firebase_admin"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =====================================================================
# FUNGSI FIREBASE (REST API & FIRESTORE) + LOGIKA 30 HARI & KUOTA
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
    """Mengecek status aktif dan batas waktu 30 hari langganan"""
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()
    if doc.exists:
        user_data = doc.to_dict()
        status = user_data.get("status_subscription", "non-aktif")
        expired_at_str = user_data.get("expired_at")
        
        if status == "aktif" and expired_at_str:
            expired_date = datetime.datetime.fromisoformat(expired_at_str)
            if datetime.datetime.now() > expired_date:
                # Jika sudah lewat batas waktu, status menjadi expired
                return "expired", user_data
        
        return status, user_data
    return "non-aktif", {}

def deduct_quota(uid, quota_type):
    """Memotong kuota spesifik sebanyak 1 poin di database"""
    db.collection("users").document(uid).update({
        quota_type: firestore.Increment(-1)
    })

# =====================================================================
# AREA SIDEBAR: HIASAN ROBOT GERMIC (DENGAN EFEK MELAYANG)
# =====================================================================
with st.sidebar:
    st.markdown("<h3 style='text-align: center; color: #475569;'>🤖 AI Assistant</h3>", unsafe_allow_html=True)

    germic_html = """
    <style>
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); }
            50% { transform: translateY(-15px) rotate(2deg); }
        }
        @keyframes signal {
            0% { transform: scale(0.5); opacity: 0; }
            50% { opacity: 1; }
            100% { transform: scale(1.5); opacity: 0; }
        }
        body {
            margin: 0; padding: 0; display: flex; justify-content: center;
            align-items: center; height: 250px; background-color: transparent; overflow: hidden;
        }
        .germic-container {
            width: 180px; height: 180px; animation: float 4s ease-in-out infinite;
            position: relative; cursor: pointer;
        }
        .signal-wave { transform-origin: 50px 12px; animation: signal 2s infinite; }
        .signal-wave-2 { transform-origin: 50px 12px; animation-delay: 0.6s; animation: signal 2s infinite; }
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    </style>
    <div id="germic-wrapper" class="germic-container">
        <svg width="100%" height="100%" viewBox="0 0 100 100" fill="none">
            <circle class="signal-wave" cx="50" cy="12" r="8" stroke="#fb7185" stroke-width="1" />
            <circle class="signal-wave signal-wave-2" cx="50" cy="12" r="8" stroke="#fb7185" stroke-width="1" />
            <circle cx="50" cy="12" r="8" stroke="#3b82f6" stroke-opacity="0.2" />
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
# INISIALISASI SESSION STATE
# =====================================================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "offline_transcript" not in st.session_state:
    st.session_state["offline_transcript"] = ""
if "offline_summary" not in st.session_state:
    st.session_state["offline_summary"] = None
if "user_data" not in st.session_state:
    st.session_state["user_data"] = {}
if "live_summary_data" not in st.session_state:
    st.session_state["live_summary_data"] = None

# =====================================================================
# HALAMAN LOGIN & REGISTER FIREBASE
# =====================================================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        st.markdown("<h2 style='text-align: center;'>🔒 Portal TranscribX Enterprise</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Gunakan kredensial Anda untuk mengakses sistem Notulensi AI.</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            email_login = st.text_input("Email", placeholder="Ketik email Anda di sini...")
            pass_login = st.text_input("Password", type="password", placeholder="Ketik password Anda...")
            btn_login = st.form_submit_button("🚀 Masuk ke Sistem", use_container_width=True)
            
            if btn_login:
                if email_login and pass_login:
                    with st.spinner("Memverifikasi kredensial..."):
                        user_data_fb = login_firebase(email_login, pass_login)
                        if "idToken" in user_data_fb:
                            uid = user_data_fb["localId"]
                            sub_status, user_db_data = check_subscription(uid)
                            
                            if sub_status == "aktif":
                                st.session_state["logged_in"] = True
                                st.session_state["user_email"] = email_login
                                st.session_state["user_uid"] = uid
                                st.session_state["user_data"] = user_db_data
                                st.success("Login berhasil! Memuat sistem...")
                                st.rerun()
                            elif sub_status == "expired":
                                st.error("⚠️ Masa aktif akun (30 hari) telah habis. Silakan perpanjang paket langganan Anda.")
                            else:
                                st.error("⚠️ Akun Anda belum diaktifkan. Hubungi Admin.")
                        else:
                            err_msg = user_data_fb.get("error", {}).get("message", "Login gagal")
                            st.error(f"⚠️ {err_msg}")
                else:
                    st.warning("Silakan masukkan email dan password.")

# =====================================================================
# APLIKASI UTAMA (Setelah Login)
# =====================================================================
else:
    colA, colB = st.columns([8, 1])
    with colB:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ TranscribX: Enterprise Transcription & AI Summarizer")
    
    # Ambil data user saat ini untuk mengecek sisa kuota secara real-time
    uid_current = st.session_state["user_uid"]
    doc_current = db.collection("users").document(uid_current).get()
    current_user_data = doc_current.to_dict() if doc_current.exists else {}
    
    quota_live = current_user_data.get("live_summary_quota", 0)
    quota_upload = current_user_data.get("upload_quota", 0)
    tier_aktif = current_user_data.get("tier", "Custom")

    # Banner Info Kuota
    st.info(f"👤 **{st.session_state['user_email']}** | 🏅 Paket: **{tier_aktif}** | ⚡ Sisa Kuota Summary Live: **{quota_live}x** | 📁 Sisa Kuota Upload: **{quota_upload}x**")
    
    ADMIN_EMAIL = st.secrets.get("ADMIN_EMAIL", "admin@domain.com") 

    if st.session_state.get("user_email") == ADMIN_EMAIL:
        tabs = st.tabs(["👑 Admin Panel", "🔴 Live Zoom (Web API)", "📁 Upload Rekaman (Offline LiteLLM)"])
        tab_admin = tabs[0]
        tab1 = tabs[1]
        tab2 = tabs[2]
        
        # --- TAB ADMIN PANEL ---
        with tab_admin:
            st.markdown("### 👑 Dashboard Admin: Registrasi & Suntik Paket Klien")
            
            with st.form("admin_register_form", clear_on_submit=True):
                col_reg1, col_reg2 = st.columns(2)
                with col_reg1:
                    email_reg = st.text_input("Email Klien Baru", placeholder="email@klien.com")
                with col_reg2:
                    pass_reg = st.text_input("Password Klien", type="password", help="Minimal 6 karakter")
                
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    selected_tier = st.selectbox("Pilih Paket Langganan", ["Basic (Rp 29k)", "Executive (Rp 49k)", "Master (Rp 129k)"])
                with col_t2:
                    status_reg = st.selectbox("Status Langganan Awal", ["aktif", "non-aktif"])
                
                btn_reg = st.form_submit_button("📝 Daftarkan & Suntik Kuota", type="primary")
                
                if btn_reg:
                    if email_reg and len(pass_reg) >= 6:
                        with st.spinner("Mendaftarkan akun..."):
                            new_user = register_firebase(email_reg, pass_reg)
                            if "idToken" in new_user:
                                uid = new_user["localId"]
                                
                                # Logika Distribusi Kuota Berdasarkan Tier
                                if "Basic" in selected_tier:
                                    live_q, up_q, t_name = 5, 1, "Basic"
                                elif "Executive" in selected_tier:
                                    live_q, up_q, t_name = 10, 3, "Executive"
                                else:
                                    live_q, up_q, t_name = 30, 10, "Master"
                                
                                # Kadaluarsa 30 Hari dari Sekarang
                                exp_date = datetime.datetime.now() + datetime.timedelta(days=30)
                                
                                db.collection("users").document(uid).set({
                                    "email": email_reg,
                                    "status_subscription": status_reg,
                                    "tier": t_name,
                                    "live_summary_quota": live_q,
                                    "upload_quota": up_q,
                                    "expired_at": exp_date.isoformat()
                                })
                                st.success(f"✅ Akun {email_reg} berhasil dibuat dengan paket {t_name} (Aktif 30 Hari)!")
                                st.rerun()
                            else:
                                err = new_user.get('error', {}).get('message', 'Gagal mendaftar')
                                st.error(f"⚠️ Gagal mendaftar: {err}")
                    else:
                        st.warning("Pastikan email terisi dan password minimal 6 karakter.")

            st.markdown("---")
            st.markdown("### 📋 Daftar Klien Terdaftar")
            
            with st.spinner("Memuat data klien..."):
                users_ref = db.collection("users").stream()
                users_list = []
                
                for doc in users_ref:
                    u_info = doc.to_dict()
                    # Format tanggal expired
                    exp_str = u_info.get("expired_at", "")
                    if exp_str:
                        exp_dt = datetime.datetime.fromisoformat(exp_str)
                        exp_format = exp_dt.strftime("%d-%m-%Y %H:%M")
                    else:
                        exp_format = "-"

                    users_list.append({
                        "Email": u_info.get("email", "-"),
                        "Paket": u_info.get("tier", "-"),
                        "Sisa Live": u_info.get("live_summary_quota", 0),
                        "Sisa Upload": u_info.get("upload_quota", 0),
                        "Kedaluwarsa": exp_format,
                        "Status": u_info.get("status_subscription", "non-aktif")
                    })
                
                if users_list:
                    df_users = pd.DataFrame(users_list)
                    st.dataframe(df_users, use_container_width=True, hide_index=True)
                else:
                    st.info("Belum ada klien yang terdaftar di sistem.")

    else:
        tabs = st.tabs(["🔴 Live Zoom (Web API)", "📁 Upload Rekaman (Offline LiteLLM)"])
        tab1 = tabs[0]
        tab2 = tabs[1]

    # =====================================================================
    # TAB 1: LIVE CAPTURE (Perekaman Gratis, AI Potong Kuota)
    # =====================================================================
    with tab1:
        st.markdown("Mesin **Web Speech API** otomatis berjalan tanpa memotong kuota Anda sewaktu merekam.")
        
        # Sisi Python: Proses AI Summary untuk memotong kuota secara aman
        st.markdown("#### ✨ Eksekusi AI Summary")
        with st.expander("Cara menggunakan AI Summary di Live Zoom"):
            st.markdown("1. Lakukan perekaman rapat menggunakan panel hitam di bawah.")
            st.markdown("2. Setelah selesai, klik tombol **📋 Copy Text** di dalam panel tersebut.")
            st.markdown("3. **Paste** teks tersebut ke dalam kotak di bawah ini, lalu klik **Generate AI Summary**.")

        text_to_process = st.text_area("Paste Teks Transkrip Anda di Sini:", height=150, placeholder="Hasil teks rapat Anda...")
        
        is_live_disabled = quota_live <= 0
        if is_live_disabled:
            st.error("❌ Kuota Live Summary Anda sudah habis. Anda tetap bisa merekam secara gratis di panel bawah.")

        if st.button("✨ Generate AI Summary & Mindmap (Potong 1 Kuota)", type="primary", disabled=is_live_disabled):
            if not text_to_process.strip():
                st.warning("Teks transkrip masih kosong. Silakan paste teks terlebih dahulu.")
            else:
                with st.spinner("⏳ Menggunakan otak AI untuk menyusun Notulensi & Visual..."):
                    llm_key = st.secrets["LITELLM_API_KEY"]
                    prompt = f"""Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                    ATURAN JSON NOTULENSI:
                    - ringkasan_eksekutif: Buat array of strings (poin-poin padat).
                    - jalannya_diskusi: Buat array of strings. WAJIB NARASI DETAIL, PANJANG, dan LENGKAP untuk setiap poin kronologis agar tidak ada info hilang.
                    - keputusan: Array of strings. Kesimpulan utama.
                    - rencana_tindak_lanjut: Ekstrak tabel penugasan. JIKA TIDAK ADA TUGAS spesifik, WAJIB BUAT 1 TUGAS DEFAULT (contoh: Review hasil rapat).
                    - hubungan_topik (CYTOSCAPE): Ekstrak 5-15 entitas penting dan hubungannya.

                    ATURAN MARKMAP (PENTING!):
                    Gunakan kode murni markdown. Isi Markmap HARUS RINGKAS berupa poin-poin. WAJIB ikuti POLA STRUKTUR INI secara lengkap tanpa ada yang dihilangkan:
                    # [Judul Topik Utama Rapat]
                    ## Ringkasan Eksekutif
                    - [Poin ringkas]
                    ## Agenda / Topik
                    - [Poin]
                    ## Peserta
                    - [Nama]
                    ## Jalannya Diskusi
                    - [Poin diskusi ringkas 1]
                      - [Detail singkat]
                    - [Poin diskusi ringkas 2]
                    ## Kendala & Solusi (Jika ada)
                    - [Kendala]
                      - [Solusi]
                    ## Keputusan Utama
                    - [Poin keputusan]
                    ## Rencana Tindak Lanjut
                    - [Nama Tugas]
                      - PIC: [Nama]
                      - Deadline: [Waktu]
                      - Prioritas: [Level]

                    ATURAN MERMAID: WAJIB format 'graph LR' dengan tanda kutip ganda pada node (A["Teks"]). Root diagram WAJIB berisi Judul Topik Rapat/Agenda.
                    Transkrip Rapat: "{text_to_process}" """

                    payload = {
                        "model": "gemini/gemini-2.5-flash", "messages": [{ "role": "user", "content": prompt }], "temperature": 0.2,
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
                                                "rencana_tindak_lanjut": { "type": "array", "items": { "type": "object", "properties": { "tugas": { "type": "string" }, "pic": { "type": "string" }, "deadline": { "type": "string" }, "prioritas": { "type": "string" } }, "required": ["tugas", "pic", "deadline", "prioritas"], "additionalProperties": False } },
                                                "hubungan_topik": { "type": "array", "items": { "type": "object", "properties": { "sumber": { "type": "string" }, "target": { "type": "string" }, "relasi": { "type": "string" } }, "required": ["sumber", "target", "relasi"], "additionalProperties": False } }
                                            }, "required": ["agenda", "peserta", "jalannya_diskusi", "keputusan", "rencana_tindak_lanjut", "hubungan_topik"], "additionalProperties": False
                                        },
                                        "visual_mindmap": { "type": "string" }, "markmap_code": { "type": "string" }
                                    }, "required": ["ringkasan_eksekutif", "notulensi_rapat", "visual_mindmap", "markmap_code"], "additionalProperties": False
                                }
                            }
                        }
                    }

                    try:
                        res = requests.post("https://litellm.koboi2026.biz.id/v1/chat/completions", headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"}, json=payload)
                        if res.status_code == 200: 
                            st.session_state["live_summary_data"] = json.loads(res.json()["choices"][0]["message"]["content"])
                            # Pemotongan Kuota jika proses berhasil
                            deduct_quota(uid_current, "live_summary_quota")
                            st.success("✅ Berhasil! Sisa Kuota Live Summary Anda berkurang 1.")
                        else: 
                            st.error(f"Error AI: {res.text}")
                    except Exception as e: 
                        st.error(f"Koneksi LLM Gagal: {str(e)}")

        # Jika berhasil membuat AI Summary, tampilkan hasilnya menggunakan komponen Python kita
        if st.session_state["live_summary_data"]:
            data = st.session_state["live_summary_data"]
            with st.container(border=True):
                st.markdown("**🌟 RINGKASAN EKSEKUTIF:**")
                rx_html = "<div style='background-color:#eff6ff; padding:15px; border-radius:10px; color:#1e3a8a; font-weight:bold; margin-bottom:15px;'><ul style='margin:0; padding-left:20px; line-height:1.6;'>"
                for r in data.get('ringkasan_eksekutif', []): rx_html += f"<li style='margin-bottom:5px;'>{r}</li>"
                rx_html += "</ul></div>"
                st.markdown(rx_html, unsafe_allow_html=True)
                
                st.markdown("**📅 RENCANA TINDAK LANJUT (ACTION ITEMS):**")
                df_tasks = pd.DataFrame(data['notulensi_rapat']['rencana_tindak_lanjut'])
                df_tasks.columns = ["Tugas", "PIC", "Deadline", "Prioritas"]
                st.table(df_tasks)
            st.info("⚠️ Silakan buka tab Offline untuk melihat render visual Markmap/Mermaid secara penuh.")

        st.markdown("---")
        st.markdown("#### 🎙️ Panel Perekaman Live Zoom (Gratis Unlimited)")
        
        # HTML Asli Anda dengan modifikasi penghapusan field API Key agar aman
        html_code = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body { font-family: 'Inter', sans-serif; background: transparent; margin: 0; }
                .controls-wrapper { margin-bottom: 20px; display: flex; flex-direction: column; gap: 15px; padding: 15px; background: #f1f5f9; border-radius: 16px; box-shadow: inset 0 2px 4px 0 rgba(0,0,0,0.06); }
                .controls-line { display: flex; align-items: center; gap: 15px; flex-wrap: wrap; }
                .visualizer-container { width: 100%; height: 80px; border-radius: 12px; overflow: hidden; background: #111827; position: relative; }
                #visualizer { width: 100%; height: 100%; display: block; }
                .transcript-box { border: 2px solid #cbd5e1; padding: 20px; border-radius: 16px; height: 300px; overflow-y: auto; background: white; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin-bottom: 20px; scroll-behavior: smooth; }
                .btn-custom { background: #3b82f6; color: white; padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-weight: bold; transition: all 0.2s; display: flex; align-items: center; gap: 8px; font-size: 14px; }
                .btn-custom:hover { background: #2563eb; }
                .btn-stop { background: #ef4444; } .btn-stop:hover { background: #dc2626; }
                .btn-custom:disabled { background: #94a3b8; cursor: not-allowed; }
                .btn-secondary { background: #e2e8f0; color: #334155; } .btn-secondary:hover { background: #cbd5e1; }
                select.btn-secondary { outline: none; border: 1px solid #cbd5e1; padding: 10px; border-radius: 8px; font-family: inherit; }
                .line-final { margin-bottom: 12px; padding: 12px; background: #f1f5f9; border-radius: 8px; border-left: 4px solid #3b82f6; font-size: 14px; line-height: 1.5; }
                .line-interim { margin-bottom: 12px; padding: 12px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #cbd5e1; font-size: 14px; opacity: 0.7; font-style: italic; }
                .timestamp { font-weight: bold; color: #64748b; margin-right: 8px; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="controls-wrapper">
                <div class="controls-line">
                    <select id="langSelect" class="btn-custom btn-secondary"><option value="id-ID">🇮🇩 ID (Indonesia)</option><option value="en-US">🇬🇧 EN (English)</option></select>
                    <button id="startBtn" class="btn-custom">🚀 START CAPTURE (GRATIS)</button>
                    <button id="stopBtn" class="btn-custom btn-stop" disabled>⏹️ STOP</button>
                    <div style="display: flex; align-items: center; gap: 8px; margin-left: auto;">
                        <div id="indicator" style="width: 12px; height: 12px; border-radius: 50%; background: #cbd5e1;"></div>
                        <span id="status" style="font-weight: bold; font-size: 14px; color: #64748b;">Standby...</span>
                    </div>
                </div>
                <div class="visualizer-container"><canvas id="visualizer"></canvas></div>
                <div class="controls-line" style="justify-content: flex-end;">
                    <button id="copyBtn" class="btn-custom btn-secondary">📋 Copy Text</button>
                    <button id="clearBtn" class="btn-custom btn-secondary">🗑️ Clear</button>
                    <button id="downloadTxtBtn" class="btn-custom" style="background: #10b981;">📝 Save TXT</button>
                </div>
            </div>
            <div id="transcriptBox" class="transcript-box">
                <div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px;">Suara yang ditangkap akan muncul di sini...</div>
            </div>
            <script>
                const startBtn = document.getElementById('startBtn'); const stopBtn = document.getElementById('stopBtn');
                const copyBtn = document.getElementById('copyBtn'); const clearBtn = document.getElementById('clearBtn');
                const downloadTxtBtn = document.getElementById('downloadTxtBtn');
                const langSelect = document.getElementById('langSelect'); const status = document.getElementById('status');
                const indicator = document.getElementById('indicator'); const transcriptBox = document.getElementById('transcriptBox');
                const visualizer = document.getElementById('visualizer'); const canvasCtx = visualizer.getContext('2d');

                let recognition, mediaRecorder, audioChunks = [], audioStream, isRecording = false;
                let audioContext, analyser, dataArray, bufferLength, drawVisual;
                let currentInterimDiv = null; let lastFinalText = "";

                if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                    status.innerText = "Browser tidak mendukung Speech API.";
                } else {
                    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                    recognition = new SpeechRecognition();
                    recognition.continuous = true; recognition.interimResults = true;

                    function getTimestamp() { const now = new Date(); return `[${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}]`; }

                    recognition.onresult = (event) => {
                        let interimTranscript = ''; let finalTranscript = '';
                        for (let i = event.resultIndex; i < event.results.length; ++i) {
                            if (event.results[i].isFinal) finalTranscript += event.results[i][0].transcript;
                            else interimTranscript += event.results[i][0].transcript;
                        }

                        if (finalTranscript) {
                            if (finalTranscript.trim() === lastFinalText.trim()) return;
                            lastFinalText = finalTranscript; const timeStr = getTimestamp();
                            if (currentInterimDiv) {
                                currentInterimDiv.className = 'line-final'; currentInterimDiv.innerHTML = `<span class="timestamp">${timeStr}</span> ${finalTranscript}`; currentInterimDiv = null;
                            } else {
                                const line = document.createElement('div'); line.className = 'line-final'; line.innerHTML = `<span class="timestamp">${timeStr}</span> ${finalTranscript}`; transcriptBox.appendChild(line);
                            }
                            transcriptBox.scrollTop = transcriptBox.scrollHeight;
                        } else if (interimTranscript) {
                            if (!currentInterimDiv) { currentInterimDiv = document.createElement('div'); currentInterimDiv.className = 'line-interim'; transcriptBox.appendChild(currentInterimDiv); }
                            currentInterimDiv.innerText = interimTranscript; transcriptBox.scrollTop = transcriptBox.scrollHeight;
                        }
                    };
                    recognition.onend = () => { if (isRecording) { try { recognition.start(); } catch(e){} } };

                    function setupVisualizer(stream) {
                        audioContext = new (window.AudioContext || window.webkitAudioContext)();
                        const source = audioContext.createMediaStreamSource(stream);
                        analyser = audioContext.createAnalyser(); analyser.fftSize = 256;
                        bufferLength = analyser.frequencyBinCount; dataArray = new Uint8Array(bufferLength);
                        source.connect(analyser);
                    }

                    function drawVisualizer() {
                        canvasCtx.clearRect(0, 0, visualizer.width, visualizer.height);
                        if (analyser) analyser.getByteFrequencyData(dataArray);
                        const barWidth = (visualizer.width / bufferLength) * 2.5; let x = 0;
                        for(let i = 0; i < bufferLength; i++) {
                            const barHeight = dataArray[i]; canvasCtx.fillStyle = 'rgb(' + (barHeight + 100) + ', 50, 255)';
                            canvasCtx.shadowBlur = 10; canvasCtx.shadowColor = '#3b82f6';
                            const y = (visualizer.height / 2) - (barHeight / 2);
                            canvasCtx.beginPath(); canvasCtx.roundRect(x, y, barWidth, barHeight, 5); canvasCtx.fill(); x += barWidth + 1;
                        }
                        drawVisual = requestAnimationFrame(drawVisualizer);
                    }

                    startBtn.onclick = async () => {
                        try {
                            lastFinalText = ""; recognition.lang = langSelect.value;
                            audioStream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true });
                            setupVisualizer(audioStream); recognition.start(); drawVisualizer(); isRecording = true;
                            status.innerText = "Merekam Gratis..."; indicator.style.background = "#ef4444"; indicator.style.boxShadow = "0 0 10px #ef4444";
                            startBtn.disabled = true; stopBtn.disabled = false; langSelect.disabled = true;
                            if(document.getElementById('placeholder')) document.getElementById('placeholder').style.display = 'none';
                        } catch(err) { console.error("Gagal akses mic:", err); status.innerText = "Izin Mic Ditolak!"; }
                    };

                    stopBtn.onclick = () => {
                        isRecording = false; recognition.stop();
                        if (audioStream) audioStream.getTracks().forEach(track => track.stop());
                        cancelAnimationFrame(drawVisual); if (audioContext) audioContext.close();
                        canvasCtx.clearRect(0, 0, visualizer.width, visualizer.height);
                        status.innerText = "Standby..."; indicator.style.background = "#cbd5e1"; indicator.style.boxShadow = "none";
                        startBtn.disabled = false; stopBtn.disabled = true; langSelect.disabled = false;
                    };

                    function getTranscriptText() {
                        const lines = transcriptBox.querySelectorAll('.line-final');
                        if (lines.length === 0) return ""; return Array.from(lines).map(line => line.innerText).join('\\n');
                    }

                    copyBtn.onclick = () => {
                        const text = getTranscriptText(); if (!text) return alert("Belum ada teks untuk dicopy!");
                        navigator.clipboard.writeText(text).then(() => { const originalText = copyBtn.innerText; copyBtn.innerText = "✅ Copied!"; setTimeout(() => copyBtn.innerText = originalText, 2000); });
                    };

                    downloadTxtBtn.onclick = () => {
                        const text = getTranscriptText(); if (!text) return alert("Belum ada teks untuk disimpan!");
                        const blob = new Blob([text], { type: 'text/plain' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'Transkrip_Raw.txt'; a.click();
                    };

                    clearBtn.onclick = () => {
                        if(confirm("Yakin ingin menghapus semua teks di layar?")) {
                            transcriptBox.innerHTML = '<div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px;">Suara yang ditangkap akan muncul di sini...</div>';
                            lastFinalText = ""; 
                        }
                    };
                }
            </script>
        </body>
        </html>
        """
        components.html(html_code, height=650, scrolling=True)

    # =====================================================================
    # TAB 2: FITUR OFFLINE TRANSCRIPTION (DIPOTONG KUOTA UPLOAD)
    # =====================================================================
    with tab2:
        st.markdown("### 📁 Transkripsi File Rekaman (Offline)")
        st.info("💡 Sistem ini menggunakan **LiteLLM Proxy** untuk proses Transkripsi (Whisper) sekaligus Summarization (Gemini). Setiap pemrosesan yang berhasil akan memotong kuota Anda.")

        is_upload_disabled = quota_upload <= 0
        if is_upload_disabled:
            st.error("❌ Kuota pemrosesan file audio Anda sudah habis. Tombol tidak dapat digunakan.")

        uploaded_file = st.file_uploader("Upload File Rekaman Anda", type=["mp3", "wav", "m4a", "mp4"])

        if uploaded_file is not None:
            if uploaded_file.size > 26214400: 
                st.error("⚠️ Ukuran file melebihi 25MB. Silakan kompres audio Anda terlebih dahulu.")
            else:
                st.audio(uploaded_file)
                if st.button("🎙️ Mulai Transkripsi & Summary (Potong 1 Kuota)", disabled=is_upload_disabled, use_container_width=True, type="primary"):
                    with st.spinner("⏳ Sedang mentranskripsi audio... Proses ini memakan waktu tergantung durasi file."):
                        try:
                            # Pemanggilan Whisper API di Backend Server
                            llm_key = st.secrets["LITELLM_API_KEY"]
                            url = "https://litellm.koboi2026.biz.id/v1/audio/transcriptions"
                            headers = {"Authorization": f"Bearer {llm_key}"}
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            data = {"model": "whisper-1", "response_format": "json"}
                            response = requests.post(url, headers=headers, files=files, data=data)

                            if response.status_code == 200:
                                st.session_state["offline_transcript"] = response.json().get("text", "")
                                st.success("✅ Transkripsi berhasil! Mulai memproses Notulensi & Peta Konsep...")
                                
                                # Setelah dapat teks, langsung generate AI
                                prompt = f"""Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                                ATURAN JSON NOTULENSI:
                                - ringkasan_eksekutif: Buat array of strings (poin-poin padat).
                                - jalannya_diskusi: Buat array of strings. WAJIB NARASI DETAIL, PANJANG, dan LENGKAP untuk setiap poin kronologis agar tidak ada info hilang.
                                - keputusan: Array of strings. Kesimpulan utama.
                                - rencana_tindak_lanjut: Ekstrak tabel penugasan. JIKA TIDAK ADA TUGAS spesifik, WAJIB BUAT 1 TUGAS DEFAULT (contoh: Review hasil rapat).
                                - hubungan_topik (CYTOSCAPE): Ekstrak 5-15 entitas penting dan hubungannya.

                                ATURAN MARKMAP (PENTING!):
                                Gunakan kode murni markdown. Isi Markmap HARUS RINGKAS berupa poin-poin. WAJIB ikuti POLA STRUKTUR INI secara lengkap tanpa ada yang dihilangkan:
                                # [Judul Topik Utama Rapat]
                                ## Ringkasan Eksekutif
                                - [Poin ringkas]
                                ## Agenda / Topik
                                - [Poin]
                                ## Peserta
                                - [Nama]
                                ## Jalannya Diskusi
                                - [Poin diskusi ringkas 1]
                                  - [Detail singkat]
                                - [Poin diskusi ringkas 2]
                                ## Kendala & Solusi (Jika ada)
                                - [Kendala]
                                  - [Solusi]
                                ## Keputusan Utama
                                - [Poin keputusan]
                                ## Rencana Tindak Lanjut
                                - [Nama Tugas]
                                  - PIC: [Nama]
                                  - Deadline: [Waktu]
                                  - Prioritas: [Level]

                                ATURAN MERMAID: WAJIB format 'graph LR' dengan tanda kutip ganda pada node (A["Teks"]). Root diagram WAJIB berisi Judul Topik Rapat/Agenda.
                                Transkrip Rapat: "{st.session_state['offline_transcript']}" """

                                payload_ai = {
                                    "model": "gemini/gemini-2.5-flash", "messages": [{ "role": "user", "content": prompt }], "temperature": 0.2,
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
                                                            "rencana_tindak_lanjut": { "type": "array", "items": { "type": "object", "properties": { "tugas": { "type": "string" }, "pic": { "type": "string" }, "deadline": { "type": "string" }, "prioritas": { "type": "string" } }, "required": ["tugas", "pic", "deadline", "prioritas"], "additionalProperties": False } },
                                                            "hubungan_topik": { "type": "array", "items": { "type": "object", "properties": { "sumber": { "type": "string" }, "target": { "type": "string" }, "relasi": { "type": "string" } }, "required": ["sumber", "target", "relasi"], "additionalProperties": False } }
                                                        }, "required": ["agenda", "peserta", "jalannya_diskusi", "keputusan", "rencana_tindak_lanjut", "hubungan_topik"], "additionalProperties": False
                                                    },
                                                    "visual_mindmap": { "type": "string" }, "markmap_code": { "type": "string" }
                                                }, "required": ["ringkasan_eksekutif", "notulensi_rapat", "visual_mindmap", "markmap_code"], "additionalProperties": False
                                            }
                                        }
                                    }
                                }

                                res_ai = requests.post("https://litellm.koboi2026.biz.id/v1/chat/completions", headers={"Authorization": f"Bearer {llm_key}", "Content-Type": "application/json"}, json=payload_ai)
                                if res_ai.status_code == 200: 
                                    st.session_state["offline_summary"] = json.loads(res_ai.json()["choices"][0]["message"]["content"])
                                    # Pemotongan kuota setelah SEMUA berhasil
                                    deduct_quota(uid_current, "upload_quota")
                                    st.success("🎉 Pemrosesan Selesai! Kuota Upload Anda telah terpotong 1.")
                                    st.rerun()
                                else: 
                                    st.error(f"Error AI: {res_ai.text}")

                            else: 
                                st.error(f"❌ Error dari API LiteLLM: {response.text}")
                        except Exception as e: 
                            st.error(f"Terjadi kesalahan saat menghubungi API: {str(e)}")

        if st.session_state["offline_transcript"]:
            st.markdown("#### 📝 Teks Mentah (Transkripsi)")
            with st.expander("Lihat Transkrip Mentah"):
                st.write(st.session_state["offline_transcript"])

        if st.session_state["offline_summary"]:
            data = st.session_state["offline_summary"]
            st.markdown("---")
            
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1: 
                st.markdown("### 📋 Laporan Notulensi AI")
            
            txt_report = "NOTULENSI RAPAT\n====================\n\n"
            txt_report += "Ringkasan Eksekutif:\n"
            for r in data.get('ringkasan_eksekutif', []): txt_report += f"- {r}\n"
            txt_report += f"\nAgenda/Topik: {data['notulensi_rapat'].get('agenda', '-')}\n"
            txt_report += f"Peserta: {', '.join(data['notulensi_rapat'].get('peserta', []))}\n\n"
            txt_report += "Jalannya Diskusi:\n"
            for d in data['notulensi_rapat'].get('jalannya_diskusi', []): txt_report += f"- {d}\n"
            txt_report += "\nKeputusan Utama:\n"
            for k in data['notulensi_rapat'].get('keputusan', []): txt_report += f"- {k}\n"
            txt_report += "\nRencana Tindak Lanjut:\n"
            for t in data['notulensi_rapat'].get('rencana_tindak_lanjut', []):
                txt_report += f"- [{t.get('prioritas')}] {t.get('tugas')} (PIC: {t.get('pic')}, Deadline: {t.get('deadline')})\n"
            
            with col_t2: 
                st.download_button(label="📝 Download Notulensi (TXT)", data=txt_report, file_name="Notulensi_Offline.txt", mime="text/plain", use_container_width=True)

            with st.container(border=True):
                st.markdown("**🌟 RINGKASAN EKSEKUTIF:**")
                rx_html = "<div style='background-color:#eff6ff; padding:15px; border-radius:10px; color:#1e3a8a; font-weight:bold; margin-bottom:15px;'><ul style='margin:0; padding-left:20px; line-height:1.6;'>"
                for r in data.get('ringkasan_eksekutif', []): rx_html += f"<li style='margin-bottom:5px;'>{r}</li>"
                rx_html += "</ul></div>"
                st.markdown(rx_html, unsafe_allow_html=True)
                
                colA, colB = st.columns(2)
                colA.markdown(f"**📌 AGENDA / TOPIK:**<br>{data['notulensi_rapat']['agenda']}", unsafe_allow_html=True)
                colB.markdown(f"**👥 PESERTA:**<br>{', '.join(data['notulensi_rapat']['peserta'])}", unsafe_allow_html=True)
                
                st.markdown("**🗣️ JALANNYA DISKUSI:**")
                diskusi_html = "<div style='background-color:#ffffff; padding:15px; border-radius:10px; border: 1px solid #e2e8f0; margin-bottom:15px; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'><ul style='margin:0; padding-left:20px; line-height: 1.6;'>"
                for d in data['notulensi_rapat'].get('jalannya_diskusi', []): diskusi_html += f"<li style='margin-bottom:8px;'>{d}</li>"
                diskusi_html += "</ul></div>"
                st.markdown(diskusi_html, unsafe_allow_html=True)
                
                st.markdown("**✅ KEPUTUSAN / KESIMPULAN UTAMA:**")
                for kep in data['notulensi_rapat']['keputusan']: 
                    st.markdown(f"- {kep}")
                
                st.markdown("**📅 RENCANA TINDAK LANJUT (ACTION ITEMS):**")
                df_tasks = pd.DataFrame(data['notulensi_rapat']['rencana_tindak_lanjut'])
                df_tasks.columns = ["Tugas", "PIC", "Deadline", "Prioritas"]
                st.table(df_tasks)

            st.markdown("### 🕸️ Visualisasi (Hover/Klik Tombol PNG di Kanan Atas)")

            col_v1, col_v2 = st.columns(2)
            with col_v1:
                st.markdown("**Cytoscape.js**")
                hubungan_json = json.dumps(data['notulensi_rapat']['hubungan_topik'])
                cytoscape_html = f"""
                <!DOCTYPE html><html><head><script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script></head>
                <body style="margin:0; padding:10px; background:#f8fafc; border-radius:12px; font-family: sans-serif; position:relative;">
                    <button onclick="dlCy()" style="position:absolute; top:20px; right:20px; z-index:100; background:#10b981; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer; font-weight:bold;">📸 PNG Full</button>
                    <div id="cy" style="width:100%; height:400px; border:1px solid #e2e8f0; border-radius:8px; background:#ffffff;"></div>
                    <script>
                        const rawData = {hubungan_json}; const cyElements = []; const nodesSet = new Set();
                        rawData.forEach(rel => {{
                            if (!nodesSet.has(rel.sumber)) {{ nodesSet.add(rel.sumber); cyElements.push({{ data: {{ id: rel.sumber, label: rel.sumber }} }}); }}
                            if (!nodesSet.has(rel.target)) {{ nodesSet.add(rel.target); cyElements.push({{ data: {{ id: rel.target, label: rel.target }} }}); }}
                            cyElements.push({{ data: {{ source: rel.sumber, target: rel.target, label: rel.relasi }} }});
                        }});
                        var cy = cytoscape({{ container: document.getElementById('cy'), elements: cyElements, style: [ {{ selector: 'node', style: {{ 'background-color': '#f43f5e', 'label': 'data(label)', 'color': '#1e293b', 'font-size': '12px', 'text-valign': 'top', 'text-halign': 'center', 'text-margin-y': -5, 'width': 30, 'height': 30 }} }}, {{ selector: 'edge', style: {{ 'width': 2, 'line-color': '#cbd5e1', 'target-arrow-color': '#cbd5e1', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'label': 'data(label)', 'font-size': '10px', 'color': '#64748b', 'text-rotation': 'autorotate', 'text-background-opacity': 1, 'text-background-color': '#ffffff', 'text-background-padding': 3 }} }} ], layout: {{ name: 'cose', padding: 20 }} }});
                        function dlCy() {{ const a = document.createElement('a'); a.href = cy.png({{full: true, scale: 4, bg: 'white'}}); a.download = 'Cytoscape.png'; a.click(); }}
                    </script>
                </body></html>
                """
                components.html(cytoscape_html, height=450)

            with col_v2:
                st.markdown("**Mermaid (Mindmap)**")
                raw_mer = data.get('visual_mindmap', '').replace("```mermaid", "").replace("```", "").strip()
                if not raw_mer.lower().startswith('graph') and not raw_mer.lower().startswith('mindmap'): 
                    raw_mer = "graph LR\\n" + raw_mer
                
                mer_html = f"""
                <!DOCTYPE html><html><head>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                    <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
                </head>
                <body style="margin:0; padding:10px; background:#f8fafc; border-radius:12px; position:relative;">
                    <button id="dlBtn" onclick="downloadMermaidImage('wrapper', 'Mermaid', event)" style="position:absolute; top:20px; right:20px; z-index:100; background:#10b981; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer; font-weight:bold;">📸 PNG</button>
                    <div id="wrapper" style="width:100%; height:400px; border:1px solid #e2e8f0; border-radius:8px; overflow-x:auto; background:#ffffff; padding:20px;">
                        <div class="mermaid">{raw_mer}</div>
                    </div>
                    <script>
                        mermaid.initialize({{startOnLoad: true}});
                        window.downloadMermaidImage = function(wrapperId, title, event) {{
                            const container = document.getElementById(wrapperId);
                            const btn = document.getElementById('dlBtn');
                            const originalText = btn.innerHTML;
                            btn.innerHTML = "⏳ MENYIMPAN..."; btn.disabled = true;

                            const originalOverflow = container.style.overflow;
                            container.style.overflow = 'visible'; 
                            
                            setTimeout(() => {{
                                html2canvas(container, {{ scale: 2, useCORS: true, backgroundColor: '#ffffff' }})
                                .then(canvas => {{
                                    container.style.overflow = originalOverflow;
                                    const link = document.createElement('a'); link.download = `Mermaid_${{title}}.png`; link.href = canvas.toDataURL('image/png', 1.0); link.click();
                                    btn.innerHTML = originalText; btn.disabled = false;
                                }}).catch(err => {{
                                    container.style.overflow = originalOverflow; btn.innerHTML = "❌ GAGAL"; setTimeout(() => {{ btn.innerHTML = originalText; btn.disabled = false; }}, 2000);
                                }});
                            }}, 500);
                        }};
                    </script>
                </body></html>
                """
                components.html(mer_html, height=450)

            st.markdown("### 🌿 Visualisasi Markmap (Peta Konsep Rapat)")
            raw_markmap = data['markmap_code'].replace("```markdown", "").replace("```", "").strip()

            markmap_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
                <script src="https://cdn.jsdelivr.net/npm/markmap-lib"></script>
                <script src="https://cdn.jsdelivr.net/npm/markmap-view"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            </head>
            <body style="margin:0; padding:10px; background:#f8fafc; border-radius:12px; position:relative;">
                <button id="dlBtnMM" onclick="downloadMarkmapImage('markmap-wrapper', 'Offline', event)" style="position:absolute; top:20px; right:20px; z-index:100; background:#10b981; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer; font-weight:bold;">📸 PNG HD</button>
                <div id="markmap-wrapper" style="width:100%; height:400px; border:1px solid #e2e8f0; border-radius:8px; overflow:hidden; background:#ffffff;">
                    <svg id="markmap" style="width:100%; height:100%;"></svg>
                </div>
                <script>
                    const markdown = `{raw_markmap}`;
                    const {{ Transformer, Markmap }} = window.markmap;
                    const transformer = new Transformer();
                    const {{ root }} = transformer.transform(markdown);
                    Markmap.create('#markmap', null, root);

                    window.downloadMarkmapImage = function(wrapperId, title, event) {{
                        const container = document.getElementById(wrapperId);
                        const svgEl = container.querySelector('svg');
                        if (!svgEl) return;

                        const btn = document.getElementById('dlBtnMM');
                        const originalText = btn.innerHTML;
                        btn.innerHTML = "⏳ MENYIMPAN..."; btn.disabled = true;

                        try {{
                            const g = svgEl.querySelector('g');
                            if (!g) throw new Error("G element not found");

                            const originalWidth = container.style.width;
                            const originalHeight = container.style.height;
                            const originalOverflow = container.style.overflow;
                            const originalTransform = g.getAttribute('transform');
                            const originalViewBox = svgEl.getAttribute('viewBox');

                            g.setAttribute('transform', 'translate(0,0) scale(1)');
                            const bbox = g.getBBox();

                            const padding = 50;
                            const trueWidth = Math.max(bbox.width, 500) + (padding * 2);
                            const trueHeight = Math.max(bbox.height, 500) + (padding * 2);

                            container.style.width = trueWidth + 'px';
                            container.style.height = trueHeight + 'px';
                            container.style.overflow = 'visible';
                            
                            svgEl.setAttribute('viewBox', `${{bbox.x - padding}} ${{bbox.y - padding}} ${{trueWidth}} ${{trueHeight}}`);
                            svgEl.style.width = '100%'; svgEl.style.height = '100%';

                            setTimeout(() => {{
                                html2canvas(container, {{
                                    scale: 2, useCORS: true, backgroundColor: '#ffffff', width: trueWidth, height: trueHeight
                                }}).then(canvas => {{
                                    container.style.width = originalWidth; container.style.height = originalHeight; container.style.overflow = originalOverflow;
                                    g.setAttribute('transform', originalTransform || '');
                                    if (originalViewBox) svgEl.setAttribute('viewBox', originalViewBox); else svgEl.removeAttribute('viewBox');

                                    const link = document.createElement('a'); link.download = `MindMap_${{title}}.png`;
                                    link.href = canvas.toDataURL('image/png', 1.0); link.click();

                                    btn.innerHTML = originalText; btn.disabled = false;
                                }}).catch(err => {{
                                    console.error("html2canvas error:", err);
                                    container.style.width = originalWidth; container.style.height = originalHeight; container.style.overflow = originalOverflow;
                                    g.setAttribute('transform', originalTransform || '');
                                    if (originalViewBox) svgEl.setAttribute('viewBox', originalViewBox); else svgEl.removeAttribute('viewBox');
                                    btn.innerHTML = "❌ GAGAL"; setTimeout(() => {{ btn.innerHTML = originalText; btn.disabled = false; }}, 2000);
                                }});
                            }}, 600); 
                        }} catch (err) {{
                            console.error("Error saving markmap:", err); btn.innerHTML = "❌ GAGAL"; setTimeout(() => {{ btn.innerHTML = originalText; btn.disabled = false; }}, 2000);
                        }}
                    }};
                </script>
            </body>
            </html>
            """
            components.html(markmap_html, height=450)

            with st.expander("Lihat Source Code Markdown"):
                st.code(raw_markmap, language="markdown")
