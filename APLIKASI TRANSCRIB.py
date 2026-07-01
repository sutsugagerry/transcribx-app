import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import time
import re

# Konfigurasi Halaman
st.set_page_config(page_title="TranscribX - Enterprise AI", layout="wide")

# =====================================================================
# CSS CUSTOM UNTUK ANIMASI, CARD, DAN UI ENTERPRISE
# =====================================================================
custom_css = """
<style>
/* Menyembunyikan elemen bawaan Streamlit */
#MainMenu {visibility: hidden;}
header {visibility: hidden; background-color: transparent;}
footer {visibility: hidden;}
.st-emotion-cache-1vt4ygl {display: none;}

/* Metric Card Styling */
.metric-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    padding: 20px;
    border-radius: 16px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
    border: 1px solid #e2e8f0;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    position: relative;
    overflow: hidden;
}
.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
}
.metric-card::before {
    content: "";
    position: absolute;
    top: 0; left: 0; width: 6px; height: 100%;
}
.metric-total::before { background-color: #8b5cf6; }
.metric-aktif::before { background-color: #10b981; }
.metric-nonaktif::before { background-color: #ef4444; }
.metric-admin::before { background-color: #f59e0b; }

/* Pulse Animation for Sidebar Profile */
@keyframes pulse-border {
    0% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.4); }
    70% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); }
    100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}
@keyframes pulse-border-admin {
    0% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4); }
    70% { box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
    100% { box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
}
.profile-card {
    border-radius: 16px;
    padding: 20px;
    color: white;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
}
.profile-card.admin {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    animation: pulse-border-admin 2.5s infinite;
}
.profile-card.user-active {
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    animation: pulse-border 2.5s infinite;
}
.profile-card.user-warning {
    background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
}
.profile-card.user-inactive {
    background: linear-gradient(135deg, #64748b 0%, #334155 100%);
}

/* Mempercantik Tombol Utama Streamlit */
.stButton>button {
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    font-weight: bold !important;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3) !important;
}
/* Mempercantik Tab Navigasi */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0px 0px;
    padding: 10px 20px;
    background-color: #f1f5f9;
}
.stTabs [aria-selected="true"] {
    background-color: #3b82f6 !important;
    color: white !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# =====================================================================
# INISIALISASI FIREBASE ADMIN
# =====================================================================
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["firebase_admin"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# =====================================================================
# DATA PAKET LANGGANAN
# =====================================================================
PAKET_LANGGANAN = {
    "BASIC": {"ai_limit": 5, "upload_limit": 1, "durasi_hari": 30},
    "EXECUTIVE": {"ai_limit": 10, "upload_limit": 3, "durasi_hari": 30},
    "MASTER": {"ai_limit": 30, "upload_limit": 10, "durasi_hari": 30},
    "NON-AKTIF": {"ai_limit": 0, "upload_limit": 0, "durasi_hari": 0}
}

ADMIN_EMAILS_CONFIG = st.secrets.get("ADMIN_EMAILS", [])
if not ADMIN_EMAILS_CONFIG:
    single_admin = st.secrets.get("ADMIN_EMAIL", "")
    ADMIN_EMAILS_CONFIG = [single_admin] if single_admin else ["sutsuga.gery@gmail.com"]

def is_admin():
    return st.session_state.get("user_email") in ADMIN_EMAILS_CONFIG

def hitung_sisa_hari(tanggal_berakhir_str):
    if not tanggal_berakhir_str: return 0
    try:
        tanggal_berakhir = datetime.fromisoformat(tanggal_berakhir_str) if isinstance(tanggal_berakhir_str, str) else tanggal_berakhir_str.replace(tzinfo=None)
        selisih = tanggal_berakhir - datetime.now()
        return selisih.days if selisih.days > 0 else 0
    except: return 0

def cek_dan_update_status_kadaluarsa(uid, user_data):
    if not user_data or user_data.get("status_subscription", "non-aktif") == "non-aktif" or user_data.get("email") in ADMIN_EMAILS_CONFIG:
        return False
    
    if hitung_sisa_hari(user_data.get("tanggal_berakhir")) <= 0:
        db.collection("users").document(uid).update({
            "status_subscription": "non-aktif", "paket": "NON-AKTIF",
            "kuota_ai": 0, "kuota_upload": 0, "tanggal_kadaluarsa": datetime.now().isoformat()
        })
        return True
    return False

def get_user_login_history(uid):
    try:
        return [h.to_dict() for h in db.collection("users").document(uid).collection("login_history").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()]
    except: return []

def record_login(uid, email):
    try:
        db.collection("users").document(uid).collection("login_history").add({"timestamp": datetime.now().isoformat(), "email": email, "platform": "Streamlit Cloud"})
        db.collection("users").document(uid).update({"last_login": datetime.now().isoformat(), "login_count": firestore.Increment(1)})
    except: pass

def delete_user(uid, email):
    try:
        docs = db.collection("users").document(uid).collection("login_history").stream()
        for doc in docs: doc.reference.delete()
        db.collection("users").document(uid).delete()
        return True, f"User {email} berhasil dihapus."
    except Exception as e: return False, f"Gagal menghapus user: {str(e)}"

def get_active_users_count():
    try: return len(list(db.collection("users").where("last_login", ">=", (datetime.now() - timedelta(hours=1)).isoformat()).stream()))
    except: return 0

def reset_user_kuota(uid, paket):
    if paket in PAKET_LANGGANAN and paket != "NON-AKTIF":
        db.collection("users").document(uid).update({
            "kuota_ai": PAKET_LANGGANAN[paket]["ai_limit"], "kuota_upload": PAKET_LANGGANAN[paket]["upload_limit"], "reset_kuota_terakhir": datetime.now().isoformat()
        })
        return True
    return False

def login_firebase(email, password):
    return requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={st.secrets['FIREBASE_WEB_API_KEY']}", json={"email": email, "password": password, "returnSecureToken": True}).json()

def register_firebase(email, password):
    return requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={st.secrets['FIREBASE_WEB_API_KEY']}", json={"email": email, "password": password, "returnSecureToken": True}).json()

def check_subscription(uid):
    doc_ref = db.collection("users").document(uid)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        cek_dan_update_status_kadaluarsa(uid, data)
        data = doc_ref.get().to_dict()
        if "paket" not in data and data.get("status_subscription") == "aktif":
            data.update({"paket": "BASIC", "kuota_ai": PAKET_LANGGANAN["BASIC"]["ai_limit"], "kuota_upload": PAKET_LANGGANAN["BASIC"]["upload_limit"], "tanggal_berakhir": (datetime.now() + timedelta(days=30)).isoformat()})
            doc_ref.update({"paket": data["paket"], "kuota_ai": data["kuota_ai"], "kuota_upload": data["kuota_upload"], "tanggal_berakhir": data["tanggal_berakhir"]})
        return data
    return {"status_subscription": "non-aktif", "paket": "NON-AKTIF"}

def cek_reset_kuota_bulanan(uid, user_data):
    if not user_data or user_data.get("status_subscription") != "aktif" or user_data.get("email") in ADMIN_EMAILS_CONFIG or user_data.get("paket", "BASIC") not in PAKET_LANGGANAN: return False
    
    sekarang, perlu_reset = datetime.now(), False
    if rkt := user_data.get("reset_kuota_terakhir"):
        try: perlu_reset = (sekarang - (datetime.fromisoformat(rkt) if isinstance(rkt, str) else rkt.replace(tzinfo=None))).days >= 30
        except: perlu_reset = True
    elif tm := user_data.get("tanggal_mulai"):
        try: perlu_reset = (sekarang - (datetime.fromisoformat(tm) if isinstance(tm, str) else tm.replace(tzinfo=None))).days >= 30
        except: perlu_reset = True
    else: perlu_reset = True
    
    if perlu_reset:
        reset_user_kuota(uid, user_data["paket"])
        st.session_state["user_kuota_ai"], st.session_state["user_kuota_upload"] = PAKET_LANGGANAN[user_data["paket"]]["ai_limit"], PAKET_LANGGANAN[user_data["paket"]]["upload_limit"]
        return True
    return False

# =====================================================================
# INISIALISASI SESSION STATE
# =====================================================================
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "offline_transcript" not in st.session_state: st.session_state["offline_transcript"] = ""
if "offline_summary" not in st.session_state: st.session_state["offline_summary"] = None
if "confirm_delete" not in st.session_state: st.session_state["confirm_delete"] = None

# =====================================================================
# HALAMAN LOGIN (UI DENGAN ANIMASI NODE BACKGROUND)
# =====================================================================
if not st.session_state["logged_in"]:
    # 1. Injeksi CSS agar Streamlit transparan dan menampilkan canvas di belakangnya
    st.markdown("""
    <style>
    /* Membuat layer bawaan Streamlit menjadi transparan */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background: transparent !important;
    }
    [data-testid="stSidebar"] { display: none; }
    
    /* Styling form login tetap dipertahankan seperti aslinya, 
       sedikit penyesuaian transparansi agar background node lebih menyatu */
    div[data-testid="stForm"] {
        background: rgba(255, 255, 255, 0.85); /* Sedikit lebih transparan */
        backdrop-filter: blur(12px);
        padding: 40px 30px;
        border-radius: 24px;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.4);
    }
    .login-title {
        color: white;
        font-weight: 900;
        font-size: 3rem;
        text-shadow: 0px 4px 15px rgba(0, 0, 0, 0.5);
        margin-bottom: 0px;
    }
    .login-subtitle {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-bottom: 40px;
        text-shadow: 0px 2px 5px rgba(0, 0, 0, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. Injeksi Javascript murni untuk membuat animasi partikel/node di Body HTML (Parent)
    components.html("""
    <script>
        const parentWindow = window.parent;
        const parentDoc = parentWindow.document;
        
        // Cek dan hapus animasi lama jika Streamlit re-run untuk mencegah penumpukan frame
        if (parentWindow.nodeAnimFrame) {
            cancelAnimationFrame(parentWindow.nodeAnimFrame);
        }
        
        let canvas = parentDoc.getElementById('node-bg-canvas');
        if (!canvas) {
            canvas = parentDoc.createElement('canvas');
            canvas.id = 'node-bg-canvas';
            Object.assign(canvas.style, {
                position: 'fixed',
                top: '0',
                left: '0',
                width: '100vw',
                height: '100vh',
                zIndex: '-1', // Berada di paling belakang
                background: 'radial-gradient(circle at center, #1e1b4b 0%, #020617 100%)' // Tema gelap futuristik
            });
            parentDoc.body.prepend(canvas);
        }

        const ctx = canvas.getContext('2d');
        let w, h;
        let nodes = [];
        const maxDistance = 150;

        function resize() {
            w = canvas.width = parentWindow.innerWidth;
            h = canvas.height = parentWindow.innerHeight;
        }
        parentWindow.addEventListener('resize', resize);
        resize();

        class Node {
            constructor() {
                this.x = Math.random() * w;
                this.y = Math.random() * h;
                this.vx = (Math.random() - 0.5) * 1.5;
                this.vy = (Math.random() - 0.5) * 1.5;
                this.radius = Math.random() * 2 + 1.5;
            }
            update() {
                this.x += this.vx;
                this.y += this.vy;
                if (this.x < 0 || this.x > w) this.vx *= -1;
                if (this.y < 0 || this.y > h) this.vy *= -1;
            }
            draw() {
                ctx.beginPath();
                ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
                ctx.fillStyle = '#818cf8'; // Warna node biru/ungu terang
                ctx.fill();
            }
        }

        function initNodes() {
            nodes = [];
            const numNodes = Math.floor((w * h) / 10000); // Kepadatan node (semakin kecil pembagi = makin banyak node)
            for (let i = 0; i < numNodes; i++) {
                nodes.push(new Node());
            }
        }
        initNodes();

        function animate() {
            ctx.clearRect(0, 0, w, h);
            
            for (let i = 0; i < nodes.length; i++) {
                nodes[i].update();
                nodes[i].draw();
                
                // Cek koneksi dengan node lain
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x;
                    const dy = nodes[i].y - nodes[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    
                    if (dist < maxDistance) {
                        ctx.beginPath();
                        ctx.moveTo(nodes[i].x, nodes[i].y);
                        ctx.lineTo(nodes[j].x, nodes[j].y);
                        const opacity = 1 - (dist / maxDistance);
                        ctx.strokeStyle = `rgba(99, 102, 241, ${opacity * 0.6})`; // Garis koneksi
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                }
            }
            parentWindow.nodeAnimFrame = requestAnimationFrame(animate);
        }
        animate();
    </script>
    """, height=0, width=0)

    # 3. Struktur Form Login Tetap Menggunakan Kode Asli Anda
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("")
        st.write("")
        st.write("")
        st.markdown("<h1 class='login-title' style='text-align: center;'>✨ TranscribX</h1>", unsafe_allow_html=True)
        st.markdown("<p class='login-subtitle' style='text-align: center;'>Portal Notulensi AI Enterprise. Masuk untuk melanjutkan.</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("<h3 style='text-align: center; color: #1e293b; margin-bottom: 25px;'>Secure Login</h3>", unsafe_allow_html=True)
            email_login = st.text_input("Email Address", placeholder="Ketik email Anda di sini...")
            pass_login = st.text_input("Password", type="password", placeholder="••••••••")
            st.write("")
            btn_login = st.form_submit_button("🚀 Masuk ke Sistem", use_container_width=True, type="primary")
            
            if btn_login:
                if email_login and pass_login:
                    with st.spinner("Memverifikasi kredensial..."):
                        user_data = login_firebase(email_login, pass_login)
                        if "idToken" in user_data:
                            uid = user_data["localId"]
                            record_login(uid, email_login)
                            
                            if email_login in ADMIN_EMAILS_CONFIG:
                                st.session_state.update({"logged_in": True, "user_email": email_login, "user_uid": uid, "user_paket": "ADMIN", "user_kuota_ai": 999999, "user_kuota_upload": 999999, "sisa_hari": 999999})
                                st.success("✅ Selamat datang, Admin! Akses Unlimited diaktifkan.")
                                st.rerun()
                            
                            user_db_info = check_subscription(uid)
                            if user_db_info.get("status_subscription", "non-aktif") == "aktif":
                                cek_reset_kuota_bulanan(uid, user_db_info)
                                st.session_state.update({
                                    "logged_in": True, "user_email": email_login, "user_uid": uid, 
                                    "user_paket": user_db_info.get("paket", "BASIC"), "user_kuota_ai": user_db_info.get("kuota_ai", 0), 
                                    "user_kuota_upload": user_db_info.get("kuota_upload", 0), "sisa_hari": hitung_sisa_hari(user_db_info.get("tanggal_berakhir")), 
                                    "tanggal_berakhir": user_db_info.get("tanggal_berakhir", "")
                                })
                                st.success("Login berhasil! Memuat sistem...")
                                st.rerun()
                            else:
                                st.error(f"⚠️ Akun Anda sudah tidak aktif. Hubungi Admin untuk perpanjangan.")
                        else:
                            st.error(f"⚠️ {user_data.get('error', {}).get('message', 'Login gagal')}")
                else:
                    st.warning("Silakan masukkan email dan password.")
# =====================================================================
# APLIKASI UTAMA
# =====================================================================
else:
    st.markdown("""
    <style>
    .stApp {
        background: white;
        animation: none;
    }
    [data-testid="stSidebar"] {
        display: flex !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # =====================================================================
    # AREA SIDEBAR
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
                <circle cx="50" cy="12" r="8" stroke="#3b82f6" stroke-opacity="0.2" />
                <path d="M50 25V15M50 15L45 10M50 15L55 10" stroke="#3b82f6" stroke-width="2" stroke-linecap="round"/>
                <circle cx="50" cy="12" r="3" fill="#fb7185" class="animate-pulse"/>
                <rect x="5" y="45" width="8" height="20" rx="4" fill="#1e293b"/>
                <rect x="87" y="45" width="8" height="20" rx="4" fill="#1e293b"/>
                <rect x="15" y="25" width="70" height="65" rx="18" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="2"/>
                <rect x="22" y="35" width="56" height="40" rx="12" fill="#1e1b4b"/>
                <g id="germic-face"><rect id="eye-l" x="33" y="45" width="12" height="15" rx="3" fill="#38bdf8"/><rect id="eye-r" x="55" y="45" width="12" height="15" rx="3" fill="#38bdf8"/><rect id="mouth" x="42" y="65" width="16" height="3" rx="1.5" fill="#818cf8"/></g>
            </svg>
        </div>
        <script>
            const face = document.getElementById('germic-face');
            function trackMouse(clientX, clientY, screenWidth) {
                if (!face) return;
                const robotX = screenWidth * 0.2; const robotY = 125;
                const mouseX = clientX - robotX; const mouseY = clientY - robotY;
                const limit = 8;
                face.style.transform = `translate(${Math.max(Math.min(mouseX/50, limit), -limit)}px, ${Math.max(Math.min(mouseY/50, limit), -limit)}px)`;
                face.style.transition = "transform 0.1s ease-out";
            }
            document.addEventListener('mousemove', (e) => trackMouse(e.clientX, e.clientY, window.innerWidth));
            try { window.parent.document.addEventListener('mousemove', (e) => trackMouse(e.clientX, e.clientY, window.parent.innerWidth)); } catch (err) { }
        </script>
        """
        components.html(germic_html, height=250)
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 13px; font-weight: bold; margin-top:-20px;'>Sistem Online</p>", unsafe_allow_html=True)
        
        if st.session_state.get("logged_in"):
            user_email = st.session_state.get('user_email')
            
            if is_admin():
                card_class = "profile-card admin"
                paket_str = "👑 ADMIN (Unlimited)"
                ai_str = "♾️ Unlimited"
                up_str = "♾️ Unlimited"
                hari_str = "Status: Permanen"
            else:
                paket = st.session_state.get('user_paket', 'NON-AKTIF')
                sisa_hari = st.session_state.get('sisa_hari', 0)
                
                if paket == 'NON-AKTIF':
                    card_class = "profile-card user-inactive"
                    paket_str = "NON-AKTIF"
                    ai_str = "0x"
                    up_str = "0x"
                    hari_str = "Masa Aktif: Habis"
                else:
                    ai_val = st.session_state.get('user_kuota_ai', 0)
                    up_val = st.session_state.get('user_kuota_upload', 0)
                    ai_str = f"{ai_val}x"
                    up_str = f"{up_val}x"
                    hari_str = f"⏳ Sisa: {sisa_hari} hari"
                    
                    if sisa_hari <= 3: card_class = "profile-card user-warning"
                    else: card_class = "profile-card user-active"

            profile_html = f"""<div class="{card_class}">
<div style="font-size: 11px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.8; margin-bottom: 5px;">Akses Profil</div>
<div style="font-weight: 800; font-size: 14px; margin-bottom: 15px; word-break: break-all;">{user_email}</div>
<div style="background: rgba(255,255,255,0.15); padding: 10px; border-radius: 8px; margin-bottom: 10px;">
<div style="font-size: 12px; margin-bottom: 5px;">🏷️ <b>Paket:</b> {paket_str}</div>
<div style="font-size: 12px; margin-bottom: 5px;">✨ <b>Sisa AI:</b> {ai_str}</div>
<div style="font-size: 12px;">📁 <b>Sisa Audio:</b> {up_str}</div>
</div>
<div style="font-size: 12px; font-weight: bold; text-align: center; margin-top: 10px;">
{hari_str}
</div>
</div>"""
            st.markdown(profile_html, unsafe_allow_html=True)
            
            if not is_admin() and st.session_state.get('sisa_hari', 0) <= 3 and st.session_state.get('sisa_hari', 0) > 0:
                st.warning("⚠️ Masa aktif hampir habis! Segera hubungi admin.")

    colA, colB = st.columns([8, 1])
    with colB:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.session_state["logged_in"] = False
            st.rerun()

    st.title("🎙️ TranscribX: Enterprise Transcription & AI Summarizer")

    if is_admin():
        tabs = st.tabs(["👑 Admin Panel", "🔴 Live Capture (Zoom/Youtube)", "📁 Upload Rekaman (Offline LiteLLM)", "💳 Info Paket Langganan"])
        tab_admin, tab1, tab2, tab_paket = tabs[0], tabs[1], tabs[2], tabs[3]
        
        # =====================================================================
        # TAB ADMIN PANEL 
        # =====================================================================
        with tab_admin:
            st.markdown("### 👑 Dashboard Admin: Enterprise Control Center")
            
            with st.spinner("Memuat metrik & menyegarkan data klien..."):
                users_ref = db.collection("users").stream()
                users_list = []
                
                for doc in users_ref:
                    user_info = doc.to_dict()
                    email_user = user_info.get("email", "-")
                    cek_dan_update_status_kadaluarsa(doc.id, user_info)
                    
                    doc_refresh = db.collection("users").document(doc.id).get()
                    user_info = doc_refresh.to_dict()
                    
                    if email_user in ADMIN_EMAILS_CONFIG:
                        status_user, paket_user, sisa_ai, sisa_up, sisa_hari_display = "admin", "ADMIN", "∞", "∞", "∞"
                        last_login, login_count = user_info.get("last_login", "Tidak diketahui"), user_info.get("login_count", 0)
                    else:
                        status_user = user_info.get("status_subscription", "non-aktif")
                        paket_user = user_info.get("paket", "BASIC" if status_user == "aktif" else "-")
                        sisa_ai, sisa_up = user_info.get("kuota_ai", 0), user_info.get("kuota_upload", 0)
                        last_login, login_count = user_info.get("last_login", "Belum pernah login"), user_info.get("login_count", 0)
                        
                        tanggal_berakhir = user_info.get("tanggal_berakhir")
                        if status_user == "aktif" and tanggal_berakhir:
                            sisa_hari = hitung_sisa_hari(tanggal_berakhir)
                            sisa_hari_display = "Kadaluarsa" if sisa_hari <= 0 else (f"⚠️ {sisa_hari} hari" if sisa_hari <= 3 else f"{sisa_hari} hari")
                            if sisa_hari <= 0: status_user = "non-aktif ⚠️"
                        else: sisa_hari_display = "Kadaluarsa"
                    
                    last_login_display = last_login[:19] if isinstance(last_login, str) and len(last_login) > 19 and last_login not in ["Belum pernah login", "Tidak diketahui"] else last_login

                    users_list.append({
                        "Email": email_user, "Status": status_user.split()[0], "Paket": paket_user, "Sisa AI": sisa_ai, "Sisa Upload": sisa_up,
                        "Sisa Hari": sisa_hari_display, "Last Login": last_login_display, "Login Count": login_count, "UID": doc.id, "UID_Short": doc.id[:8] + "..."
                    })

            total_users = len(users_list)
            total_aktif = sum(1 for u in users_list if u['Status'] == 'aktif')
            total_nonaktif = sum(1 for u in users_list if 'non-aktif' in u['Status'])
            total_admin = sum(1 for u in users_list if u['Status'] == 'admin')
            active_now = get_active_users_count()

            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            def build_metric_card(title, value, subtext, icon, type_class):
                return f"""
                <div class="metric-card metric-{type_class}">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <p style="margin: 0; color: #64748b; font-size: 13px; font-weight: 600; text-transform: uppercase;">{title}</p>
                            <h2 style="margin: 5px 0 0 0; color: #0f172a; font-size: 28px; line-height: 1;">{value}</h2>
                            <p style="margin: 8px 0 0 0; color: #10b981; font-size: 11px; font-weight: 600; background: #d1fae5; display: inline-block; padding: 2px 8px; border-radius: 10px;">{subtext}</p>
                        </div>
                        <div style="font-size: 28px; opacity: 0.9;">{icon}</div>
                    </div>
                </div>
                """
            
            with col_m1: st.markdown(build_metric_card("Total Users", total_users, f"↑ {active_now} online", "👥", "total"), unsafe_allow_html=True)
            with col_m2: st.markdown(build_metric_card("Klien Aktif", total_aktif, "Paket Berjalan", "✅", "aktif"), unsafe_allow_html=True)
            with col_m3: st.markdown(build_metric_card("Non-Aktif", total_nonaktif, "Perlu Follow-up", "❌", "nonaktif"), unsafe_allow_html=True)
            with col_m4: st.markdown(build_metric_card("Admin", total_admin, "Superuser", "👑", "admin"), unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.expander("➕ Registrasi Akun Klien Baru", expanded=False):
                with st.form("admin_register_form", clear_on_submit=True):
                    col_reg1, col_reg2, col_reg3 = st.columns(3)
                    with col_reg1: email_reg = st.text_input("Email Klien Baru", placeholder="email@klien.com")
                    with col_reg2: pass_reg = st.text_input("Password Klien", type="password", help="Minimal 6 karakter")
                    with col_reg3: paket_reg = st.selectbox("Pilih Paket Awal", ["BASIC", "EXECUTIVE", "MASTER", "NON-AKTIF"])
                    btn_reg = st.form_submit_button("Daftarkan Klien", type="primary", use_container_width=True)
                    
                    if btn_reg:
                        if email_reg and len(pass_reg) >= 6:
                            if email_reg in ADMIN_EMAILS_CONFIG: st.error("⚠️ Email ini terdaftar sebagai Admin.")
                            else:
                                with st.spinner("Mendaftarkan..."):
                                    new_user = register_firebase(email_reg, pass_reg)
                                    if "idToken" in new_user:
                                        uid, sekarang = new_user["localId"], datetime.now()
                                        tanggal_berakhir = sekarang + timedelta(days=30)
                                        status_reg = "aktif" if paket_reg != "NON-AKTIF" else "non-aktif"
                                        kuota_ai = PAKET_LANGGANAN[paket_reg]["ai_limit"] if paket_reg != "NON-AKTIF" else 0
                                        kuota_upload = PAKET_LANGGANAN[paket_reg]["upload_limit"] if paket_reg != "NON-AKTIF" else 0
                                        db.collection("users").document(uid).set({
                                            "email": email_reg, "status_subscription": status_reg, "paket": paket_reg,
                                            "kuota_ai": kuota_ai, "kuota_upload": kuota_upload, "tanggal_mulai": sekarang.isoformat(),
                                            "tanggal_berakhir": tanggal_berakhir.isoformat(), "reset_kuota_terakhir": sekarang.isoformat(),
                                            "last_login": "Belum pernah login", "login_count": 0
                                        })
                                        st.success(f"✅ Akun {email_reg} berhasil dibuat!")
                                        st.rerun()
                                    else: st.error(f"⚠️ Gagal mendaftar: {new_user.get('error', {}).get('message', 'Gagal')}")
                        else: st.warning("Pastikan email terisi dan password minimal 6 karakter.")

            st.markdown("#### 📊 Analitik Distribusi")
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'><b>Distribusi Status Pengguna</b></p>", unsafe_allow_html=True)
                status_counts = pd.DataFrame([u['Status'] for u in users_list], columns=['Status']).value_counts().reset_index(name='Jumlah')
                st.bar_chart(status_counts, x="Status", y="Jumlah", color="#3b82f6")
            with col_chart2:
                st.markdown("<p style='text-align: center; color: #64748b; font-size: 14px;'><b>Distribusi Paket Langganan</b></p>", unsafe_allow_html=True)
                paket_list = [u['Paket'] for u in users_list if u['Paket'] != 'ADMIN']
                if paket_list:
                    paket_counts = pd.DataFrame(paket_list, columns=['Paket']).value_counts().reset_index(name='Jumlah')
                    st.bar_chart(paket_counts, x="Paket", y="Jumlah", color="#10b981")
                else: st.info("Belum ada data paket klien.")

            st.markdown("---")
            
            st.markdown("### 📋 Tabel Manajemen Klien")
            col_search1, col_search2, col_search3 = st.columns([3, 2, 2])
            with col_search1: search_query = st.text_input("🔍 Cari email atau paket...", placeholder="Ketik untuk filter...")
            with col_search2: filter_status = st.selectbox("📊 Filter Status", ["Semua", "Aktif", "Non-Aktif", "Admin"])
            with col_search3: filter_paket = st.selectbox("📦 Filter Paket", ["Semua", "BASIC", "EXECUTIVE", "MASTER", "NON-AKTIF"])
            
            filtered_users = users_list.copy()
            if search_query: filtered_users = [u for u in filtered_users if search_query.lower() in u['Email'].lower() or search_query.lower() in u['Paket'].lower()]
            if filter_status != "Semua": filtered_users = [u for u in filtered_users if filter_status.lower() in str(u['Status']).lower()]
            if filter_paket != "Semua": filtered_users = [u for u in filtered_users if u['Paket'] == filter_paket]

            if filtered_users:
                df_display = pd.DataFrame([{ "📧 Email": u['Email'], "📊 Status": u['Status'].upper(), "📦 Paket": u['Paket'], "💎 AI": u['Sisa AI'], "📤 Upload": u['Sisa Upload'], "⏳ Sisa Hari": u['Sisa Hari'], "🕒 Last Login": u['Last Login'], "🔑 ID": u['UID_Short'] } for u in filtered_users])
                def color_status(val):
                    if val == "ADMIN": return 'background-color: #dbeafe; color: #1e40af; font-weight: bold'
                    elif val == "AKTIF": return 'background-color: #d1fae5; color: #065f46; font-weight: bold'
                    elif "NON-AKTIF" in str(val): return 'background-color: #fee2e2; color: #991b1b; font-weight: bold'
                    return ''
                def color_sisa_hari(val):
                    if val == "∞": return 'background-color: #dbeafe; color: #1e40af; font-weight: bold'
                    elif "Kadaluarsa" in str(val): return 'background-color: #fee2e2; color: #991b1b; font-weight: bold'
                    elif "⚠️" in str(val): return 'background-color: #fef3c7; color: #92400e; font-weight: bold'
                    elif "hari" in str(val):
                        try:
                            if int(''.join(filter(str.isdigit, str(val)))) > 7: return 'background-color: #d1fae5; color: #065f46'
                        except: pass
                    return ''
                
                try: styled_df = df_display.style.map(color_status, subset=['📊 Status']).map(color_sisa_hari, subset=['⏳ Sisa Hari'])
                except: styled_df = df_display.style.applymap(color_status, subset=['📊 Status']).applymap(color_sisa_hari, subset=['⏳ Sisa Hari'])
                st.dataframe(styled_df, use_container_width=True, hide_index=True, height=350)
            else: st.info("🔍 Tidak ada user yang sesuai dengan filter.")

            st.markdown("---")
            
            st.markdown("### 🛠️ Action Center (Kelola & Edit Klien)")
            
            user_options = [u['Email'] for u in filtered_users if u['Status'] != 'admin']
            if user_options:
                with st.container(border=True):
                    selected_email = st.selectbox("🎯 Pilih Akun Klien yang Ingin Dikelola:", user_options, key="action_center_select")
                    selected_user = next((u for u in filtered_users if u['Email'] == selected_email), None)
                    
                    if selected_user:
                        st.markdown(f"""
                        <div style='background: #f8fafc; padding: 15px 20px; border-radius: 10px; border-left: 5px solid #3b82f6; margin-bottom: 20px;'>
                            <h4 style='margin: 0; color: #1e293b;'>Pengaturan: <b>{selected_user['Email']}</b></h4>
                            <div style='display: flex; gap: 20px; margin-top: 10px; font-size: 14px; color: #475569;'>
                                <span>📦 Paket: <b>{selected_user['Paket']}</b></span>
                                <span>💎 AI: <b>{selected_user['Sisa AI']}</b></span>
                                <span>📤 Upload: <b>{selected_user['Sisa Upload']}</b></span>
                                <span>⏳ Masa Aktif: <b>{selected_user['Sisa Hari']}</b></span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        tab_edit, tab_extend, tab_history, tab_danger = st.tabs(["✏️ Ubah Paket", "📅 Perpanjang Masa Aktif", "🔍 Riwayat & Reset", "❌ Hapus Akun"])
                        
                        with tab_edit:
                            st.caption("Mengubah paket akan mengatur ulang kuota sesuai paket baru dan mereset masa aktif menjadi 30 hari dari sekarang.")
                            with st.form("form_edit_paket"):
                                col_e1, col_e2 = st.columns([3, 1])
                                with col_e1:
                                    new_paket = st.selectbox("Pilih Paket Baru", ["BASIC", "EXECUTIVE", "MASTER", "NON-AKTIF"], 
                                                             index=["BASIC", "EXECUTIVE", "MASTER", "NON-AKTIF"].index(selected_user['Paket']) if selected_user['Paket'] in ["BASIC", "EXECUTIVE", "MASTER", "NON-AKTIF"] else 0, label_visibility="collapsed")
                                with col_e2:
                                    btn_update_paket = st.form_submit_button("💾 Simpan", type="primary", use_container_width=True)
                                
                                if btn_update_paket:
                                    uid, sekarang = selected_user['UID'], datetime.now()
                                    if new_paket != "NON-AKTIF":
                                        db.collection("users").document(uid).update({
                                            "status_subscription": "aktif", "paket": new_paket, "kuota_ai": PAKET_LANGGANAN[new_paket]["ai_limit"],
                                            "kuota_upload": PAKET_LANGGANAN[new_paket]["upload_limit"], "tanggal_mulai": sekarang.isoformat(),
                                            "tanggal_berakhir": (sekarang + timedelta(days=30)).isoformat(), "reset_kuota_terakhir": sekarang.isoformat()
                                        })
                                    else:
                                        db.collection("users").document(uid).update({
                                            "status_subscription": "non-aktif", "paket": "NON-AKTIF", "kuota_ai": 0, "kuota_upload": 0, "tanggal_berakhir": sekarang.isoformat()
                                        })
                                    st.success(f"✅ Paket untuk {selected_email} diubah ke {new_paket}.")
                                    time.sleep(1)
                                    st.rerun()
                        
                        with tab_extend:
                            st.caption("Menambah masa aktif hari tanpa mengubah/mereset sisa kuota saat ini.")
                            with st.form("form_extend_hari"):
                                col_x1, col_x2 = st.columns([3, 1])
                                with col_x1:
                                    hari_tambahan = st.number_input("Tambah Masa Aktif (Hari)", min_value=1, max_value=365, value=30, label_visibility="collapsed")
                                with col_x2:
                                    btn_extend = st.form_submit_button("⏳ Tambah Hari", type="primary", use_container_width=True)
                                
                                if btn_extend:
                                    uid = selected_user['UID']
                                    user_doc = db.collection("users").document(uid).get().to_dict()
                                    sekarang, tgl_lama = datetime.now(), user_doc.get("tanggal_berakhir")
                                    if tgl_lama:
                                        try:
                                            t_akhir = datetime.fromisoformat(tgl_lama) if isinstance(tgl_lama, str) else tgl_lama.replace(tzinfo=None)
                                            t_baru = max(t_akhir, sekarang) + timedelta(days=hari_tambahan)
                                        except: t_baru = sekarang + timedelta(days=hari_tambahan)
                                    else: t_baru = sekarang + timedelta(days=hari_tambahan)
                                        
                                    db.collection("users").document(uid).update({"status_subscription": "aktif", "tanggal_berakhir": t_baru.isoformat()})
                                    st.success(f"✅ Masa aktif {selected_email} ditambah {hari_tambahan} hari!")
                                    time.sleep(1)
                                    st.rerun()
                                    
                        with tab_history:
                            col_h1, col_h2 = st.columns([1, 1.5], gap="large")
                            with col_h1:
                                st.markdown("<h5 style='color:#334155; margin-bottom:10px;'>🔄 Reset Kuota Manual</h5>", unsafe_allow_html=True)
                                st.caption("Kembalikan kuota AI dan Upload ke kondisi penuh sesuai paket saat ini.")
                                if st.button("🔄 Reset Kuota Sekarang", use_container_width=True):
                                    if selected_user['Paket'] in PAKET_LANGGANAN:
                                        reset_user_kuota(selected_user['UID'], selected_user['Paket'])
                                        st.success("✅ Kuota berhasil direset!")
                                        time.sleep(1)
                                        st.rerun()
                                    else: st.error("Paket tidak valid untuk direset.")
                                
                                st.markdown("<br>", unsafe_allow_html=True)
                                st.markdown("<h5 style='color:#334155; margin-bottom:10px;'>▶️ Status Akses</h5>", unsafe_allow_html=True)
                                if selected_user['Status'] == 'non-aktif' and selected_user['Paket'] != 'NON-AKTIF':
                                    st.caption("Akun ini memiliki paket tapi statusnya non-aktif.")
                                    if st.button("Aktifkan Kembali Akses", type="primary", use_container_width=True):
                                        sekarang = datetime.now()
                                        db.collection("users").document(selected_user['UID']).update({"status_subscription": "aktif", "tanggal_berakhir": (sekarang + timedelta(days=30)).isoformat(), "tanggal_mulai": sekarang.isoformat()})
                                        st.success("✅ Akun diaktifkan kembali!")
                                        time.sleep(1)
                                        st.rerun()
                                else:
                                    st.info("Akun sedang berjalan normal (Aktif).")

                            with col_h2:
                                st.markdown("<h5 style='color:#334155; margin-bottom:10px;'>📜 Riwayat Login</h5>", unsafe_allow_html=True)
                                if st.button("Tampilkan Riwayat", use_container_width=True):
                                    history = get_user_login_history(selected_user['UID'])
                                    if history:
                                        st.dataframe(pd.DataFrame([{"Waktu": h.get('timestamp', '')[:19], "Platform": h.get('platform', '-')} for h in history[:10]]), use_container_width=True, hide_index=True)
                                    else: st.info("Belum ada riwayat login.")
                        
                        with tab_danger:
                            st.markdown("<h5 style='color:#ef4444; margin-bottom:10px;'>❌ Hapus Akun Klien Permanen</h5>", unsafe_allow_html=True)
                            st.warning("Tindakan ini tidak dapat dibatalkan. Semua data terkait akun ini akan hilang dari database.")
                            if st.button("Hapus Permanen User Ini", type="secondary", use_container_width=True):
                                if st.session_state.get('confirm_delete') != selected_user['UID']:
                                    st.session_state['confirm_delete'] = selected_user['UID']
                                    st.error(f"⚠️ KLIK SEKALI LAGI UNTUK KONFIRMASI MENGHAPUS **{selected_user['Email']}**!")
                                else:
                                    success, msg = delete_user(selected_user['UID'], selected_user['Email'])
                                    if success:
                                        st.success(msg)
                                        st.session_state.pop('confirm_delete', None)
                                        time.sleep(1)
                                        st.rerun()
                                    else: st.error(msg)
            else: st.info("Tidak ada klien yang terdaftar atau sesuai filter untuk dikelola.")

    else:
        tabs = st.tabs(["🔴 Live Capture (Zoom/Youtube)", "📁 Upload Rekaman (Offline LiteLLM)", "💳 Info Paket Langganan"])
        tab1, tab2, tab_paket = tabs[0], tabs[1], tabs[2]

    # =====================================================================
    # TAB INFO PAKET LANGGANAN
    # =====================================================================
    with tab_paket:
        st.markdown("### 📊 Pilihan Paket Langganan TranscribX")
        st.write("Tingkatkan produktivitas rapat Anda dengan memilih paket yang sesuai. Hubungi admin untuk upgrade.")
        st.write("")
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("""
            <div style='background-color:#ffffff; padding:20px; border-radius:15px; border:1px solid #e2e8f0; height:100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s;' onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <h3 style='color:#334155; margin-top:0;'>1. Paket BASIC</h3>
                <h4 style='color:#3b82f6;'>Rp 29.000 <span style='font-size:14px; color:#94a3b8;'>/ 30 hari</span></h4>
                <p style='font-size:14px; color:#64748b; margin-bottom:20px;'>Cocok untuk mahasiswa, asisten peneliti, atau staf admin.</p>
                <hr style='border-color:#f1f5f9; margin-bottom:20px;'>
                <ul style='font-size:14px; color:#334155; padding-left:20px; line-height:1.8;'>
                    <li>✅ <b>Unlimited</b> Live Transcribe</li>
                    <li>✅ <b>5x</b> Premium AI Summary & Mindmap</li>
                    <li>✅ <b>1x</b> Upload File Audio (Max 30 menit)</li>
                    <li>⏳ <b>30 Hari</b> Masa Aktif</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with col_p2:
            st.markdown("""
            <div style='background-color:#eff6ff; padding:20px; border-radius:15px; border:2px solid #3b82f6; height:100%; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); position:relative; transition: transform 0.2s;' onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style='position:absolute; top:-12px; right:20px; background:#ef4444; color:white; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:bold;'>🔥 Best Seller</div>
                <h3 style='color:#1e3a8a; margin-top:0;'>2. Paket EXECUTIVE</h3>
                <h4 style='color:#2563eb;'>Rp 49.000 <span style='font-size:14px; color:#94a3b8;'>/ 30 hari</span></h4>
                <p style='font-size:14px; color:#475569; margin-bottom:20px;'>Cocok untuk ketua komite, manajer, atau profesional.</p>
                <hr style='border-color:#bfdbfe; margin-bottom:20px;'>
                <ul style='font-size:14px; color:#1e3a8a; padding-left:20px; line-height:1.8;'>
                    <li>✅ <b>Unlimited</b> Live Transcribe</li>
                    <li>✅ <b>10x</b> Premium AI Summary & Mindmap</li>
                    <li>✅ <b>3x</b> Upload File Audio (Max 30 menit)</li>
                    <li>⏳ <b>30 Hari</b> Masa Aktif</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with col_p3:
            st.markdown("""
            <div style='background-color:#fff1f2; padding:20px; border-radius:15px; border:1px solid #fecdd3; height:100%; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); transition: transform 0.2s;' onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <h3 style='color:#881337; margin-top:0;'>3. Paket MASTER / VIP</h3>
                <h4 style='color:#e11d48;'>Rp 129.000 <span style='font-size:14px; color:#94a3b8;'>/ 30 hari</span></h4>
                <p style='font-size:14px; color:#64748b; margin-bottom:20px;'>Cocok untuk panitia masterclass atau institusi.</p>
                <hr style='border-color:#ffe4e6; margin-bottom:20px;'>
                <ul style='font-size:14px; color:#881337; padding-left:20px; line-height:1.8;'>
                    <li>✅ <b>Unlimited</b> Live Transcribe</li>
                    <li>✅ <b>30x</b> Premium AI Summary & Mindmap</li>
                    <li>✅ <b>10x</b> Upload File Audio (Max 30 menit)</li>
                    <li>🌟 <b>Prioritas Support</b> via WhatsApp</li>
                    <li>⏳ <b>30 Hari</b> Masa Aktif</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

    # =====================================================================
    # TAB 1: LIVE CAPTURE - SCREEN CAPTURE (FIXED)
    # =====================================================================
    with tab1:
        st.markdown("### 🎙️ Live Transcribe - Screen Capture (Zoom / YouTube)")
        st.info("💡 **TIPS:** Klik Start Capture → Pilih tab/window yang menjalankan Zoom atau YouTube → Centang **'Share tab audio'** → Klik Share.")
        st.warning("⚠️ **PENTING:** Saat dialog share muncul, pastikan kamu memilih tab/window Zoom/YouTube dan **CENTANG 'Share tab audio'**!")
        
        html_code = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.tailwindcss.com"></script>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.15.4/dist/browser/index.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.15.4/dist/browser/index.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
            <style>
                * { box-sizing: border-box; }
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: transparent; margin: 0; padding: 10px; color: #1e293b; }
                
                .controls-wrapper { 
                    background: #ffffff; border-radius: 20px; padding: 24px; 
                    box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05), 0 8px 10px -6px rgba(0,0,0,0.01); 
                    border: 1px solid #e2e8f0; margin-bottom: 24px;
                    display: flex; flex-direction: column; gap: 16px;
                }
                
                .controls-row { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
                
                .visualizer-container { 
                    width: 100%; height: 80px; border-radius: 16px; overflow: hidden; 
                    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%); 
                    position: relative; box-shadow: inset 0 4px 6px rgba(0,0,0,0.3);
                }
                #visualizer { width: 100%; height: 100%; display: block; }
                
                .transcript-box { 
                    background: #f8fafc; border: 1px solid #cbd5e1; padding: 16px 20px; 
                    border-radius: 20px; height: 300px; overflow-y: auto; 
                    box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 16px; 
                }
                
                .line-final { 
                    margin-bottom: 12px; padding: 12px 16px; background: #ffffff; 
                    border-radius: 12px; border-left: 5px solid #3b82f6; 
                    font-size: 14px; line-height: 1.6; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
                }
                .line-interim { 
                    margin-bottom: 12px; padding: 12px 16px; background: rgba(255,255,255,0.5); 
                    border-radius: 12px; border-left: 5px solid #94a3b8; 
                    font-size: 14px; opacity: 0.6; font-style: italic; 
                }
                .timestamp { font-weight: 700; color: #3b82f6; margin-right: 10px; font-size: 12px; background: #eff6ff; padding: 2px 8px; border-radius: 6px; display: inline-block; }
                
                .btn-custom { 
                    font-family: inherit; color: white; padding: 10px 20px; border: none; 
                    border-radius: 10px; cursor: pointer; font-weight: 600; 
                    transition: all 0.2s ease; display: inline-flex; align-items: center; gap: 8px; font-size: 14px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .btn-custom:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
                .btn-custom:active { transform: translateY(0); }
                .btn-custom:disabled { background: #cbd5e1 !important; cursor: not-allowed; transform: none; box-shadow: none; color: #64748b; }
                
                .btn-start { background: #3b82f6; }
                .btn-start:hover { background: #2563eb; }
                .btn-stop { background: #ef4444; }
                .btn-stop:hover { background: #dc2626; }
                .btn-ai { background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); }
                .btn-ai:hover { background: linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%); }
                .btn-secondary { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; box-shadow: none; } 
                .btn-secondary:hover { background: #e2e8f0; color: #1e293b; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
                .btn-green { background: #10b981; }
                .btn-green:hover { background: #059669; }
                
                select.btn-secondary, input.api-input { 
                    outline: none; border: 1px solid #cbd5e1; padding: 10px 14px; 
                    border-radius: 10px; font-family: inherit; font-size: 14px; background: white;
                }
                select.btn-secondary:focus, input.api-input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
                input.api-input { flex: 1; min-width: 200px; }
                
                .status-badge { display: flex; align-items: center; gap: 10px; background: #f8fafc; padding: 6px 16px; border-radius: 20px; border: 1px solid #e2e8f0; font-weight: 600; font-size: 13px; }
                .indicator-dot { width: 12px; height: 12px; border-radius: 50%; background: #cbd5e1; transition: all 0.3s; flex-shrink: 0; }
                .indicator-dot.recording { background: #ef4444; box-shadow: 0 0 10px #ef4444; animation: blink 1s infinite; }
                @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
                
                .ai-section { background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px 20px; border-radius: 16px; display: flex; flex-direction: column; gap: 12px; margin-top: 8px; }
                .ai-section .ai-row { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
                
                #audioContainer { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
                .audio-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); flex-wrap: wrap; }
                .audio-item audio { height: 36px; flex: 1; min-width: 200px; }
                
                .cy-container { width: 100%; height: 400px; border-radius: 16px; background: #ffffff; border: 1px solid #e2e8f0; position: relative; }
                .btn-export { cursor: pointer; background: #10b981; color: white; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 600; border: none; box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: background 0.2s; }
                .btn-export:hover { background: #059669; }
                
                .fade-in { animation: fadeIn 0.5s ease; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                
                .instruction-box {
                    background: #fffbeb; border: 2px solid #f59e0b; padding: 16px; border-radius: 12px;
                    margin-bottom: 16px; font-size: 13px; color: #92400e;
                }
                
                .debug-box {
                    background: #f0fdf4; border: 1px solid #86efac; padding: 10px; border-radius: 8px;
                    margin-top: 10px; font-size: 11px; color: #166534; font-family: monospace;
                    max-height: 150px; overflow-y: auto;
                }
                
                @media (max-width: 640px) {
                    .controls-row { flex-direction: column; align-items: stretch; }
                    .controls-row > * { width: 100%; }
                    .status-badge { justify-content: center; }
                    .ai-section .ai-row { flex-direction: column; }
                    .ai-section .ai-row > * { width: 100%; }
                }
            </style>
        </head>
        <body>
            <!-- INSTRUCTION BOX -->
            <div class="instruction-box">
                <strong>📺 CARA SCREEN CAPTURE:</strong><br>
                1. Buka <b>Zoom/YouTube</b> di tab browser <b>TERPISAH</b>.<br>
                2. Pastikan <b>VOLUME SPEAKER LAPTOP ANDA NYALA</b> (Tidak di-Mute). Karena fitur ini "mendengar" suara dari speaker Anda.<br>
                3. Klik <b>"Start Capture"</b>, izinkan akses Microphone jika diminta.<br>
                4. Pilih tab/window <b>Zoom</b> atau <b>YouTube</b>.<br>
                5. <b>CENTANG "Share tab audio"</b> lalu klik Share.
            </div>
        
            <!-- MAIN CONTROLS -->
            <div class="controls-wrapper">
                <div class="controls-row">
                    <select id="langSelect" class="btn-custom btn-secondary" style="min-width:120px;">
                        <option value="id-ID">🇮🇩 Indonesia</option>
                        <option value="en-US">🇬🇧 English</option>
                        <option value="ja-JP">🇯🇵 Japanese</option>
                    </select>
                    <button id="startBtn" class="btn-custom btn-start">▶️ Start Capture</button>
                    <button id="stopBtn" class="btn-custom btn-stop" disabled>⏹️ Stop & Simpan Rekaman</button>
                    <div class="status-badge" style="margin-left:auto;">
                        <div id="indicator" class="indicator-dot"></div>
                        <span id="status" style="color: #64748b;">Standby</span>
                    </div>
                </div>
                
                <div class="visualizer-container">
                    <canvas id="visualizer"></canvas>
                </div>
                
                <!-- DEBUG INFO -->
                <div id="debugInfo" class="debug-box" style="display:none;">
                    <strong>🔍 Debug Log:</strong>
                </div>
                
                <div class="ai-section">
                    <div class="ai-row">
                        <span style="font-size: 13px; font-weight: 700; color: #475569; white-space:nowrap;">🔑 API Key:</span>
                        <input type="password" id="apiKeyInput" class="api-input" placeholder="Masukkan API Key LiteLLM / Gemini..." style="flex:1; min-width:150px;">
                        <button id="aiBtn" class="btn-custom btn-ai" style="white-space:nowrap;">✨ Generate AI Summary</button>
                    </div>
                </div>
            </div>

            <!-- TRANSCRIPT CONTROLS -->
            <div style="display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; margin-bottom: 12px;">
                <button id="copyBtn" class="btn-custom btn-secondary" style="padding: 6px 14px; font-size: 13px;">📋 Copy</button>
                <button id="clearBtn" class="btn-custom btn-secondary" style="padding: 6px 14px; font-size: 13px;">🗑️ Clear</button>
                <button id="downloadTxtBtn" class="btn-custom btn-green" style="padding: 6px 14px; font-size: 13px;">📝 Save TXT</button>
            </div>

            <!-- TRANSCRIPT BOX -->
            <div id="transcriptBox" class="transcript-box">
                <div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px; font-weight: 600;">
                    🎤 Klik "Start Capture" → Pilih tab Zoom/YouTube → Centang "Share audio" → Share
                </div>
            </div>

            <!-- AI CONTENT AREA -->
            <div id="aiContent" class="w-full"></div>
            
            <!-- AUDIO ARCHIVE -->
            <div style="margin-top: 24px; background: #ffffff; padding: 16px 20px; border-radius: 16px; border: 1px solid #e2e8f0;">
                <h3 style="margin: 0 0 12px 0; font-size: 15px; color: #1e293b; font-weight: 700;">🎧 Arsip Rekaman Screen Capture</h3>
                <div id="audioContainer">
                    <p style="color:#94a3b8; font-size:13px; text-align:center;" id="audioPlaceholder">Rekaman akan muncul di sini setelah Stop</p>
                </div>
            </div>

            <script>
                (function() {
                    'use strict';

                    // ======== DOM REFS ========
                    const startBtn = document.getElementById('startBtn');
                    const stopBtn = document.getElementById('stopBtn');
                    const copyBtn = document.getElementById('copyBtn');
                    const clearBtn = document.getElementById('clearBtn');
                    const downloadTxtBtn = document.getElementById('downloadTxtBtn');
                    const aiBtn = document.getElementById('aiBtn');
                    const apiKeyInput = document.getElementById('apiKeyInput');
                    const aiContent = document.getElementById('aiContent');
                    const langSelect = document.getElementById('langSelect');
                    const status = document.getElementById('status');
                    const indicator = document.getElementById('indicator');
                    const transcriptBox = document.getElementById('transcriptBox');
                    const audioContainer = document.getElementById('audioContainer');
                    const visualizer = document.getElementById('visualizer');
                    const canvasCtx = visualizer.getContext('2d');
                    const debugInfo = document.getElementById('debugInfo');

                    // ======== STATE ========
                    let isRecording = false;
                    let isVisualizerActive = false; // Memisahkan flag visualizer agar tidak nyangkut
                    let recognition = null;
                    let mediaRecorder = null;
                    let audioChunks = [];
                    let displayStream = null;
                    let globalAudioCtx = null; // Audio context global
                    let analyser = null;
                    let dataArray = null;
                    let drawVisual = null;
                    let currentInterimDiv = null;
                    let lastFinalText = "";

                    function updateDebug(msg) {
                        debugInfo.style.display = 'block';
                        const time = new Date().toLocaleTimeString();
                        debugInfo.innerHTML += '<br><span style="color:#64748b;">' + time + '</span> ' + msg;
                        debugInfo.scrollTop = debugInfo.scrollHeight;
                    }

                    // ======== INIT SPEECH RECOGNITION ========
                    function initSpeechRecognition() {
                        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                        if (!SpeechRecognition) {
                            status.innerText = "❌ Browser tidak mendukung Speech API";
                            updateDebug('ERROR: Speech API not supported');
                            return null;
                        }
                        const rec = new SpeechRecognition();
                        rec.continuous = true;
                        rec.interimResults = true;
                        rec.lang = langSelect.value;

                        rec.onstart = function() {
                            isRecording = true;
                            status.innerText = "🎤 Menangkap audio... (Pastikan volume speaker nyala!)";
                            indicator.className = 'indicator-dot recording';
                            startBtn.disabled = true;
                            stopBtn.disabled = false;
                            langSelect.disabled = true;
                            const placeholder = document.getElementById('placeholder');
                            if (placeholder) placeholder.style.display = 'none';
                            updateDebug('Speech recognition STARTED');
                        };

                        rec.onerror = function(event) {
                            updateDebug('Speech error: ' + event.error);
                            if (event.error === 'no-speech') return;
                            if (event.error === 'aborted') return;
                            if (event.error === 'not-allowed') {
                                status.innerText = "❌ Izin Mic ditolak! Transkrip tidak akan muncul.";
                            } else {
                                status.innerText = "⚠️ Speech Error: " + event.error;
                            }
                        };

                        rec.onend = function() {
                            updateDebug('Speech ended. isRecording=' + isRecording);
                            if (isRecording) {
                                setTimeout(() => {
                                    try { rec.start(); updateDebug('Speech restarted'); } 
                                    catch(e) { updateDebug('Restart failed: ' + e.message); }
                                }, 200);
                            }
                        };

                        rec.onresult = function(event) {
                            let interimTranscript = '';
                            let finalTranscript = '';
                            
                            for (let i = event.resultIndex; i < event.results.length; i++) {
                                const result = event.results[i];
                                if (result.isFinal) {
                                    finalTranscript += result[0].transcript + ' ';
                                } else {
                                    interimTranscript += result[0].transcript;
                                }
                            }

                            if (finalTranscript.trim()) {
                                const cleanFinal = finalTranscript.trim();
                                if (cleanFinal === lastFinalText.trim()) return;
                                lastFinalText = cleanFinal;
                                
                                const now = new Date();
                                const timeStr = '[' + 
                                    String(now.getHours()).padStart(2,'0') + ':' + 
                                    String(now.getMinutes()).padStart(2,'0') + ':' + 
                                    String(now.getSeconds()).padStart(2,'0') + ']';
                                
                                if (currentInterimDiv) {
                                    currentInterimDiv.className = 'line-final';
                                    currentInterimDiv.innerHTML = '<span class="timestamp">' + timeStr + '</span> ' + cleanFinal;
                                    currentInterimDiv = null;
                                } else {
                                    const line = document.createElement('div');
                                    line.className = 'line-final';
                                    line.innerHTML = '<span class="timestamp">' + timeStr + '</span> ' + cleanFinal;
                                    transcriptBox.appendChild(line);
                                }
                                transcriptBox.scrollTop = transcriptBox.scrollHeight;
                            } else if (interimTranscript.trim()) {
                                if (!currentInterimDiv) {
                                    currentInterimDiv = document.createElement('div');
                                    currentInterimDiv.className = 'line-interim';
                                    transcriptBox.appendChild(currentInterimDiv);
                                }
                                currentInterimDiv.textContent = '💬 ' + interimTranscript;
                                transcriptBox.scrollTop = transcriptBox.scrollHeight;
                            }
                        };

                        return rec;
                    }

                    // ======== VISUALIZER ========
                    function setupVisualizer(stream) {
                        try {
                            const audioTracks = stream.getAudioTracks();
                            if (audioTracks.length === 0) {
                                updateDebug('WARNING: No audio tracks for visualizer');
                                return;
                            }
                            const audioOnlyStream = new MediaStream(audioTracks);
                            const source = globalAudioCtx.createMediaStreamSource(audioOnlyStream);
                            analyser = globalAudioCtx.createAnalyser();
                            analyser.fftSize = 256;
                            dataArray = new Uint8Array(analyser.frequencyBinCount);
                            source.connect(analyser);
                            updateDebug('Visualizer OK.');
                        } catch(e) {
                            updateDebug('Visualizer error: ' + e.message);
                        }
                    }

                    function drawVisualizer() {
                        // Jika visualizer tidak aktif, hentikan loop
                        if (!isVisualizerActive) return;
                        
                        const width = visualizer.width;
                        const height = visualizer.height;
                        canvasCtx.clearRect(0, 0, width, height);
                        
                        if (analyser && dataArray) {
                            analyser.getByteFrequencyData(dataArray);
                            const bufferLength = analyser.frequencyBinCount;
                            const barWidth = (width / bufferLength) * 2.5;
                            let x = 0;
                            
                            for (let i = 0; i < bufferLength; i++) {
                                const barHeight = dataArray[i] / 2;
                                const r = Math.min(barHeight + 100, 255);
                                const g = Math.min(barHeight / 2 + 50, 255);
                                const b = Math.min(barHeight + 150, 255);
                                canvasCtx.fillStyle = 'rgb(' + r + ',' + g + ',' + b + ')';
                                canvasCtx.shadowBlur = 10;
                                canvasCtx.shadowColor = '#f59e0b';
                                const y = (height / 2) - (barHeight / 2);
                                canvasCtx.fillRect(x, y, Math.max(barWidth, 1), Math.max(barHeight, 2));
                                x += barWidth + 1;
                            }
                        }
                        
                        // Lanjutkan animasi terus menerus selama flag isVisualizerActive true
                        if (isVisualizerActive) {
                            drawVisual = requestAnimationFrame(drawVisualizer);
                        }
                    }

                    // ======== SETUP MEDIA RECORDER ========
                    function setupMediaRecorder(stream) {
                        audioChunks = [];
                        
                        const options = { mimeType: 'video/webm;codecs=vp9,opus' };
                        if (!MediaRecorder.isTypeSupported(options.mimeType)) options.mimeType = 'video/webm;codecs=vp8,opus';
                        if (!MediaRecorder.isTypeSupported(options.mimeType)) options.mimeType = 'video/webm';
                        if (!MediaRecorder.isTypeSupported(options.mimeType)) options.mimeType = '';
                        
                        updateDebug('MediaRecorder mimeType: ' + (options.mimeType || 'browser default'));
                        
                        try {
                            mediaRecorder = new MediaRecorder(stream, options.mimeType ? options : undefined);
                        } catch(e) {
                            updateDebug('MediaRecorder with options failed, trying default');
                            mediaRecorder = new MediaRecorder(stream);
                        }
                        
                        mediaRecorder.ondataavailable = function(e) {
                            if (e.data && e.data.size > 0) {
                                audioChunks.push(e.data);
                                updateDebug('Chunk: ' + (e.data.size / 1024).toFixed(1) + ' KB');
                            }
                        };
                        
                        mediaRecorder.onstart = function() {
                            updateDebug('MediaRecorder STARTED recording');
                        };
                        
                        mediaRecorder.onstop = function() {
                            updateDebug('MediaRecorder STOPPED. Total chunks: ' + audioChunks.length);
                            
                            if (audioChunks.length > 0) {
                                const mimeType = mediaRecorder.mimeType || 'video/webm';
                                const blob = new Blob(audioChunks, { type: mimeType });
                                const blobSizeKB = (blob.size / 1024).toFixed(1);
                                updateDebug('BLOB created: ' + blobSizeKB + ' KB, type: ' + blob.type);
                                
                                const audioUrl = URL.createObjectURL(blob);
                                const timestamp = Date.now();
                                const ext = mimeType.includes('mp4') ? 'mp4' : 'webm';
                                const fileName = 'ScreenCapture_' + timestamp + '.' + ext;
                                
                                const placeholder = document.getElementById('audioPlaceholder');
                                if (placeholder) {
                                    placeholder.remove();
                                }
                                
                                const audioItem = document.createElement('div');
                                audioItem.className = 'audio-item fade-in';
                                audioItem.innerHTML = `
                                    <audio controls src="${audioUrl}" preload="auto" style="flex:1; min-width:200px;"></audio>
                                    <a href="${audioUrl}" download="${fileName}" class="btn-custom btn-green" style="padding:6px 14px; font-size:12px; white-space:nowrap; text-decoration:none;">💾 Download</a>
                                    <small style="color:#94a3b8; white-space:nowrap;">${blobSizeKB} KB</small>
                                `;
                                audioContainer.appendChild(audioItem);
                                updateDebug('✅ Audio player ADDED to container');
                            } else {
                                const errorItem = document.createElement('p');
                                errorItem.style.color = '#ef4444';
                                errorItem.style.textAlign = 'center';
                                errorItem.style.padding = '10px';
                                errorItem.innerText = '⚠️ Tidak ada data audio. Pastikan "Share tab audio" DICENTANG saat capture!';
                                audioContainer.appendChild(errorItem);
                                updateDebug('❌ NO audio chunks recorded!');
                            }
                            
                            audioChunks = [];
                        };
                        
                        mediaRecorder.onerror = function(e) {
                            updateDebug('MediaRecorder ERROR: ' + (e.error?.message || 'unknown'));
                        };
                    }

                    // ======== START ========
                    startBtn.onclick = async function() {
                        try {
                            lastFinalText = "";
                            currentInterimDiv = null;
                            audioChunks = [];
                            debugInfo.innerHTML = '<strong>🔍 Debug Log:</strong>';
                            debugInfo.style.display = 'block';
                            transcriptBox.innerHTML = '<div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px; font-weight: 600;">🎤 Menangkap audio... Bicara atau putar audio di tab yang dipilih.</div>';
                            
                            updateDebug('=== START CAPTURE ===');
                            
                            // Minta Izin Mic secara eksplisit dulu untuk memastikan fitur transkrip diizinkan
                            try {
                                await navigator.mediaDevices.getUserMedia({ audio: true });
                            } catch (micErr) {
                                alert("PENTING: Izin Microphone diperlukan agar Transkrip teks muncul. Mohon klik allow/izinkan!");
                                updateDebug('Mic permission denied: ' + micErr.message);
                            }

                            // Inisialisasi AudioContext secara sinkron setelah klik tombol 
                            if (!globalAudioCtx) {
                                globalAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
                            }
                            if (globalAudioCtx.state === 'suspended') {
                                globalAudioCtx.resume();
                            }
                            
                            displayStream = await navigator.mediaDevices.getDisplayMedia({ 
                                video: {
                                    width: { ideal: 640 },
                                    height: { ideal: 480 },
                                    frameRate: { ideal: 1 }
                                },
                                audio: {
                                    echoCancellation: false,
                                    noiseSuppression: false,
                                    autoGainControl: false
                                }
                            });
                            
                            updateDebug('Display stream obtained');
                            
                            const videoTracks = displayStream.getVideoTracks();
                            const audioTracks = displayStream.getAudioTracks();
                            updateDebug('Video tracks: ' + videoTracks.length);
                            updateDebug('Audio tracks: ' + audioTracks.length);
                            
                            if (audioTracks.length === 0) {
                                status.innerText = "⚠️ TIDAK ADA AUDIO! Centang 'Share tab audio'";
                                updateDebug('ERROR: No audio tracks in stream!');
                                videoTracks.forEach(t => t.stop());
                                startBtn.disabled = false;
                                stopBtn.disabled = true;
                                return;
                            }
                            
                            setupMediaRecorder(displayStream);
                            mediaRecorder.start(1000);
                            
                            setupVisualizer(displayStream);
                            
                            // Nyalakan visualizer loop
                            isVisualizerActive = true;
                            drawVisualizer();
                            
                            recognition = initSpeechRecognition();
                            if (recognition) {
                                recognition.start();
                            }
                            
                            videoTracks[0]?.addEventListener('ended', () => {
                                updateDebug('Video track ended (user stopped sharing from browser)');
                                if (isRecording) {
                                    updateDebug('Auto-stopping...');
                                    stopBtn.click();
                                }
                            });
                            
                            audioTracks[0]?.addEventListener('ended', () => {
                                updateDebug('Audio track ended');
                            });
                            
                            resizeVisualizer();
                            updateDebug('=== CAPTURE STARTED SUCCESSFULLY ===');
                            
                        } catch(err) {
                            updateDebug('ERROR: ' + err.name + ' - ' + err.message);
                            status.innerText = "❌ Gagal: " + (err.name === 'NotAllowedError' ? 'Screen capture dibatalkan' : err.message);
                            startBtn.disabled = false;
                            stopBtn.disabled = true;
                        }
                    };

                    // ======== STOP ========
                    stopBtn.onclick = function() {
                        updateDebug('=== STOP BUTTON CLICKED ===');
                        isRecording = false;
                        
                        // Matikan visualizer loop
                        isVisualizerActive = false;
                        if (drawVisual) cancelAnimationFrame(drawVisual);
                        
                        if (recognition) {
                            try { recognition.stop(); } catch(e) {}
                            recognition = null;
                            updateDebug('Speech recognition stopped');
                        }
                        
                        if (mediaRecorder && mediaRecorder.state === 'recording') {
                            updateDebug('Requesting MediaRecorder stop... Current state: ' + mediaRecorder.state);
                            mediaRecorder.stop();
                        }
                        
                        if (displayStream) {
                            displayStream.getTracks().forEach(track => {
                                updateDebug('Stopping track: ' + track.kind + ' - ' + track.label);
                                track.stop();
                            });
                            displayStream = null;
                        }
                        
                        if (globalAudioCtx && globalAudioCtx.state === 'running') {
                            globalAudioCtx.suspend(); 
                        }
                        analyser = null;
                        dataArray = null;
                        
                        canvasCtx.clearRect(0, 0, visualizer.width, visualizer.height);
                        status.innerText = "⏸️ Stopped - Cek Arsip Rekaman ↓";
                        indicator.className = 'indicator-dot';
                        startBtn.disabled = false;
                        stopBtn.disabled = true;
                        langSelect.disabled = false;
                        
                        if (currentInterimDiv) {
                            currentInterimDiv.className = 'line-final';
                            const now = new Date();
                            const timeStr = '[' + 
                                String(now.getHours()).padStart(2,'0') + ':' + 
                                String(now.getMinutes()).padStart(2,'0') + ':' + 
                                String(now.getSeconds()).padStart(2,'0') + ']';
                            const text = currentInterimDiv.textContent.replace('💬 ', '');
                            currentInterimDiv.innerHTML = '<span class="timestamp">' + timeStr + '</span> ' + text;
                            currentInterimDiv = null;
                        }
                        
                        updateDebug('=== STOP COMPLETE ===');
                    };

                    // ======== RESIZE VISUALIZER ========
                    function resizeVisualizer() {
                        visualizer.width = visualizer.parentElement.clientWidth || 600;
                        visualizer.height = 80;
                    }
                    window.addEventListener('resize', resizeVisualizer);
                    setTimeout(resizeVisualizer, 100);

                    // ======== COPY ========
                    copyBtn.onclick = function() {
                        const lines = transcriptBox.querySelectorAll('.line-final');
                        if (lines.length === 0) { alert('Belum ada teks!'); return; }
                        const text = Array.from(lines).map(line => line.innerText).join('\\n');
                        navigator.clipboard.writeText(text).then(() => {
                            copyBtn.innerText = '✅ Copied!';
                            setTimeout(() => copyBtn.innerText = '📋 Copy', 2000);
                        }).catch(() => {
                            const ta = document.createElement('textarea');
                            ta.value = text; document.body.appendChild(ta);
                            ta.select(); document.execCommand('copy'); ta.remove();
                            copyBtn.innerText = '✅ Copied!';
                            setTimeout(() => copyBtn.innerText = '📋 Copy', 2000);
                        });
                    };

                    // ======== DOWNLOAD TXT ========
                    downloadTxtBtn.onclick = function() {
                        const lines = transcriptBox.querySelectorAll('.line-final');
                        if (lines.length === 0) { alert('Belum ada teks!'); return; }
                        const text = Array.from(lines).map(line => line.innerText).join('\\n');
                        const blob = new Blob([text], { type: 'text/plain' });
                        const a = document.createElement('a');
                        a.href = URL.createObjectURL(blob);
                        a.download = 'Transkrip_Capture_' + Date.now() + '.txt';
                        a.click();
                    };

                    // ======== CLEAR ========
                    clearBtn.onclick = function() {
                        transcriptBox.innerHTML = `
                            <div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px; font-weight: 600;">
                                🎤 Klik "Start Capture" → Pilih tab Zoom/YouTube → Centang "Share audio" → Share
                            </div>
                        `;
                        lastFinalText = "";
                        currentInterimDiv = null;
                        aiContent.innerHTML = "";
                    };

                    // ======== GET TRANSCRIPT ========
                    function getTranscriptText() {
                        return Array.from(transcriptBox.querySelectorAll('.line-final')).map(line => line.innerText).join('\\n');
                    }

                    // ======== FUNGSI DOWNLOAD VISUALISASI LIVE ========
                    window.dlCyLive = function() {
                        if (window.cyInstance) {
                            const a = document.createElement('a'); 
                            a.href = window.cyInstance.png({full: true, scale: 4, bg: 'white'}); 
                            a.download = 'Cytoscape_Live.png'; 
                            a.click();
                        }
                    };

                    window.dlMermaidLive = function() {
                        const container = document.getElementById('mermaidLiveWrapper');
                        const originalOverflow = container.style.overflow;
                        container.style.overflow = 'visible'; 
                        setTimeout(() => {
                            html2canvas(container, { scale: 2, useCORS: true, backgroundColor: '#ffffff' })
                            .then(canvas => {
                                container.style.overflow = originalOverflow;
                                const link = document.createElement('a'); 
                                link.download = 'Mermaid_Live.png'; 
                                link.href = canvas.toDataURL('image/png', 1.0); 
                                link.click();
                            });
                        }, 500);
                    };

                    window.dlMarkmapLive = function() {
                        const container = document.getElementById('markmapLiveWrapper');
                        const svgEl = container.querySelector('svg');
                        if (!svgEl) return;
                        
                        const g = svgEl.querySelector('g');
                        if (!g) return;
                        
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
                        svgEl.setAttribute('viewBox', (bbox.x - padding) + ' ' + (bbox.y - padding) + ' ' + trueWidth + ' ' + trueHeight);
                        svgEl.style.width = '100%'; svgEl.style.height = '100%';
                        
                        setTimeout(() => {
                            html2canvas(container, { scale: 2, useCORS: true, backgroundColor: '#ffffff', width: trueWidth, height: trueHeight })
                            .then(canvas => {
                                container.style.width = originalWidth; container.style.height = originalHeight; container.style.overflow = originalOverflow;
                                g.setAttribute('transform', originalTransform || '');
                                if (originalViewBox) svgEl.setAttribute('viewBox', originalViewBox); else svgEl.removeAttribute('viewBox');
                                const link = document.createElement('a'); 
                                link.download = 'Markmap_Live.png';
                                link.href = canvas.toDataURL('image/png', 1.0); 
                                link.click();
                            });
                        }, 600);
                    };

                    // ======== AI SUMMARY ========
                    aiBtn.onclick = async function() {
                        const transcript = getTranscriptText();
                        const apiKey = apiKeyInput.value.trim();
                        if (!apiKey) { alert('Masukkan API Key!'); return; }
                        if (!transcript) { alert('Transkrip kosong!'); return; }
                        
                        aiBtn.innerHTML = '⏳ Memproses...';
                        aiBtn.disabled = true;
                        aiContent.innerHTML = '<div class="p-6 bg-purple-50 rounded-2xl text-center mt-4"><p class="text-purple-600 font-bold">🔄 AI memproses Notulensi & Visual...</p></div>';

                        const prompt = `Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                        ATURAN JSON NOTULENSI:
                        - ringkasan_eksekutif: Buat array of strings (poin-poin padat).
                        - jalannya_diskusi: Buat array of strings. WAJIB NARASI DETAIL, PANJANG, dan LENGKAP.
                        - keputusan: Array of strings. Kesimpulan utama.
                        - rencana_tindak_lanjut: Ekstrak tabel penugasan. JIKA TIDAK ADA TUGAS spesifik, WAJIB BUAT 1 TUGAS DEFAULT.
                        - hubungan_topik (CYTOSCAPE): Ekstrak 5-15 entitas penting dan hubungannya.
                        ATURAN MARKMAP (PENTING!): Gunakan kode murni markdown dengan struktur lengkap.
                        ATURAN MERMAID: WAJIB format 'graph LR'.
                        Transkrip Rapat: "${transcript}"`;

                        const payload = {
                            model: "gemini/gemini-2.5-flash", 
                            messages: [{ role: "user", content: prompt }], 
                            temperature: 0.2,
                            response_format: {
                                type: "json_schema",
                                json_schema: {
                                    name: "meeting_summary", strict: true,
                                    schema: {
                                        type: "object",
                                        properties: {
                                            ringkasan_eksekutif: { type: "array", items: { type: "string" } },
                                            notulensi_rapat: {
                                                type: "object",
                                                properties: {
                                                    agenda: { type: "string" }, peserta: { type: "array", items: { type: "string" } },
                                                    jalannya_diskusi: { type: "array", items: { type: "string" } }, keputusan: { type: "array", items: { type: "string" } },
                                                    rencana_tindak_lanjut: { type: "array", items: { type: "object", properties: { tugas: { type: "string" }, pic: { type: "string" }, deadline: { type: "string" }, prioritas: { type: "string" } }, required: ["tugas", "pic", "deadline", "prioritas"], additionalProperties: false } },
                                                    hubungan_topik: { type: "array", items: { type: "object", properties: { sumber: { type: "string" }, target: { type: "string" }, relasi: { type: "string" } }, required: ["sumber", "target", "relasi"], additionalProperties: false } }
                                                }, required: ["agenda", "peserta", "jalannya_diskusi", "keputusan", "rencana_tindak_lanjut", "hubungan_topik"], additionalProperties: false
                                            },
                                            visual_mindmap: { type: "string" }, markmap_code: { type: "string" }
                                        }, required: ["ringkasan_eksekutif", "notulensi_rapat", "visual_mindmap", "markmap_code"], additionalProperties: false
                                    }
                                }
                            }
                        };

                        try {
                            const response = await fetch("https://litellm.koboi2026.biz.id/v1/chat/completions", {
                                method: "POST",
                                headers: { "Authorization": "Bearer " + apiKey, "Content-Type": "application/json" },
                                body: JSON.stringify(payload)
                            });
                            
                            const textResponse = await response.text();
                            
                            let resJson;
                            try {
                                resJson = JSON.parse(textResponse);
                            } catch (e) {
                                throw new Error("Server API tidak merespon dengan format JSON.");
                            }

                            if (!response.ok) {
                                throw new Error(resJson.error?.message || "HTTP Error " + response.status);
                            }

                            if (resJson.choices) {
                                const data = JSON.parse(resJson.choices[0].message.content);
                                
                                let taskRows = (data.notulensi_rapat.rencana_tindak_lanjut || []).map(t => 
                                    `<tr class="text-xs border-b"><td class="p-2 border-r">${t.tugas}</td><td class="p-2 border-r">${t.pic}</td><td class="p-2 border-r">${t.deadline}</td><td class="p-2 font-bold">${t.prioritas}</td></tr>`
                                ).join('');
                                
                                aiContent.innerHTML = `
                                    <div class="fade-in mt-6 mb-10">
                                        <!-- RINGKASAN EKSEKUTIF -->
                                        <div class="mb-4">
                                            <p class="font-bold text-sm mb-2">🌟 RINGKASAN EKSEKUTIF:</p>
                                            <div class="bg-blue-50 p-4 rounded-xl text-blue-900 font-bold text-sm">
                                                <ul class="list-disc ml-5 leading-relaxed">${(data.ringkasan_eksekutif || []).map(r => '<li>' + r + '</li>').join('')}</ul>
                                            </div>
                                        </div>

                                        <!-- AGENDA & PESERTA -->
                                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                                            <div>
                                                <p class="font-bold text-sm">📌 AGENDA / TOPIK:</p>
                                                <p class="text-sm mt-1">${data.notulensi_rapat.agenda || '-'}</p>
                                            </div>
                                            <div>
                                                <p class="font-bold text-sm">👥 PESERTA:</p>
                                                <p class="text-sm mt-1">${(data.notulensi_rapat.peserta || []).join(', ') || '-'}</p>
                                            </div>
                                        </div>

                                        <!-- JALANNYA DISKUSI -->
                                        <div class="mb-4">
                                            <p class="font-bold text-sm mb-2">🗣️ JALANNYA DISKUSI:</p>
                                            <div class="bg-white p-4 rounded-xl border shadow-sm text-sm">
                                                <ul class="list-disc ml-5 leading-relaxed">${(data.notulensi_rapat.jalannya_diskusi || []).map(d => '<li class="mb-2">' + d + '</li>').join('')}</ul>
                                            </div>
                                        </div>

                                        <!-- KEPUTUSAN UTAMA -->
                                        <div class="mb-4">
                                            <p class="font-bold text-sm mb-2">✅ KEPUTUSAN / KESIMPULAN UTAMA:</p>
                                            <ul class="list-disc ml-5 text-sm">${(data.notulensi_rapat.keputusan || []).map(k => '<li>' + k + '</li>').join('')}</ul>
                                        </div>

                                        <!-- TINDAK LANJUT -->
                                        <div class="mb-8">
                                            <p class="font-bold text-sm mb-2">📅 RENCANA TINDAK LANJUT (ACTION ITEMS):</p>
                                            <div class="overflow-x-auto">
                                                <table class="w-full text-sm text-left border rounded-lg">
                                                    <thead class="bg-gray-100"><tr class="border-b"><th class="p-2 border-r">Tugas</th><th class="p-2 border-r">PIC</th><th class="p-2 border-r">Deadline</th><th class="p-2">Prioritas</th></tr></thead>
                                                    <tbody>${taskRows}</tbody>
                                                </table>
                                            </div>
                                        </div>

                                        <!-- AREA VISUALISASI -->
                                        <h3 class="font-bold text-lg mb-4 text-slate-800 border-b pb-2">🕸️ Visualisasi</h3>
                                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                                            <!-- Cytoscape -->
                                            <div>
                                                <p class="font-bold text-sm mb-2">Cytoscape.js</p>
                                                <div class="relative bg-white border border-slate-200 rounded-xl overflow-hidden p-2">
                                                    <button onclick="dlCyLive()" class="absolute top-2 right-2 z-10 bg-emerald-500 text-white font-bold px-3 py-1 rounded shadow cursor-pointer text-xs">📸 PNG Full</button>
                                                    <div id="cyLiveContainer" style="width:100%; height:400px; background:#ffffff; border-radius:8px;"></div>
                                                </div>
                                            </div>

                                            <!-- Mermaid -->
                                            <div>
                                                <p class="font-bold text-sm mb-2">Mermaid (Mindmap)</p>
                                                <div class="relative bg-white border border-slate-200 rounded-xl p-4">
                                                    <button onclick="dlMermaidLive()" class="absolute top-2 right-2 z-10 bg-emerald-500 text-white font-bold px-3 py-1 rounded shadow cursor-pointer text-xs">📸 PNG</button>
                                                    <div id="mermaidLiveWrapper" style="width:100%; height:380px; overflow-x:auto; background:#ffffff;">
                                                        <div id="mermaidLive" class="mermaid"></div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Markmap -->
                                        <div class="mt-4">
                                            <p class="font-bold text-sm mb-2">🌿 Visualisasi Markmap (Peta Konsep Rapat)</p>
                                            <div class="relative bg-white border border-slate-200 rounded-xl overflow-hidden">
                                                <button onclick="dlMarkmapLive()" class="absolute top-4 right-4 z-10 bg-emerald-500 text-white font-bold px-3 py-1 rounded shadow cursor-pointer text-xs">📸 PNG HD</button>
                                                <div id="markmapLiveWrapper" style="width:100%; height:400px; background:#ffffff;">
                                                    <svg id="markmapLive" style="width:100%; height:100%;"></svg>
                                                </div>
                                            </div>
                                        </div>
                                    </div>`;

                                setTimeout(() => {
                                    const cyData = data.notulensi_rapat.hubungan_topik || [];
                                    const cyElements = [];
                                    const nodesSet = new Set();
                                    cyData.forEach(rel => {
                                        if (!nodesSet.has(rel.sumber)) { nodesSet.add(rel.sumber); cyElements.push({ data: { id: rel.sumber, label: rel.sumber } }); }
                                        if (!nodesSet.has(rel.target)) { nodesSet.add(rel.target); cyElements.push({ data: { id: rel.target, label: rel.target } }); }
                                        cyElements.push({ data: { source: rel.sumber, target: rel.target, label: rel.relasi } });
                                    });
                                    
                                    window.cyInstance = cytoscape({
                                        container: document.getElementById('cyLiveContainer'),
                                        elements: cyElements,
                                        style: [
                                            { selector: 'node', style: { 'background-color': '#f43f5e', 'label': 'data(label)', 'color': '#1e293b', 'font-size': '12px', 'text-valign': 'top', 'text-halign': 'center', 'text-margin-y': -5, 'width': 30, 'height': 30 } },
                                            { selector: 'edge', style: { 'width': 2, 'line-color': '#cbd5e1', 'target-arrow-color': '#cbd5e1', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'label': 'data(label)', 'font-size': '10px', 'color': '#64748b', 'text-rotation': 'autorotate', 'text-background-opacity': 1, 'text-background-color': '#ffffff', 'text-background-padding': 3 } }
                                        ],
                                        layout: { name: 'cose', padding: 20 }
                                    });
                                }, 100);

                                setTimeout(() => {
                                    let rawMer = (data.visual_mindmap || "").replace(/```mermaid/gi, "").replace(/```/g, "").trim();
                                    if (!rawMer.toLowerCase().startsWith('graph') && !rawMer.toLowerCase().startsWith('mindmap')) { 
                                        rawMer = "graph LR\\n" + rawMer; 
                                    }
                                    const mermaidDiv = document.getElementById('mermaidLive');
                                    mermaidDiv.innerHTML = rawMer;
                                    mermaid.init(undefined, mermaidDiv);
                                }, 100);

                                setTimeout(() => {
                                    let rawMarkmap = (data.markmap_code || "").replace(/```markdown/gi, "").replace(/```/g, "").trim();
                                    const { Transformer, Markmap } = window.markmap;
                                    const transformer = new Transformer();
                                    const { root } = transformer.transform(rawMarkmap);
                                    Markmap.create('#markmapLive', null, root);
                                }, 100);

                            } else {
                                aiContent.innerHTML = '<div class="p-4 bg-red-50 rounded-xl mt-4 text-red-600">Error: ' + (resJson.error?.message || 'Unknown') + '</div>';
                            }
                        } catch(err) {
                            aiContent.innerHTML = '<div class="p-4 bg-red-50 rounded-xl mt-4 text-red-600" style="word-wrap: break-word;">Koneksi Gagal: ' + err.message + '</div>';
                        } finally {
                            aiBtn.innerHTML = '✨ Generate AI Summary';
                            aiBtn.disabled = false;
                        }
                    };

                })();
            </script>
        </body>
        </html>
        """
        components.html(html_code, height=1500, scrolling=True)

    # =====================================================================
    # TAB 2: FITUR OFFLINE TRANSCRIPTION
    # =====================================================================
    with tab2:
        st.markdown("### 📁 Transkripsi File Rekaman (Offline)")
        st.info("💡 Sistem ini menggunakan **LiteLLM Proxy** untuk proses Transkripsi (Whisper) sekaligus Summarization (Gemini).")

        llm_key = st.text_input("🔑 API Key LiteLLM (All-in-One)", type="password", placeholder="sk-...", help="API Key untuk proxy LiteLLM Anda")
        uploaded_file = st.file_uploader("Upload File Rekaman Anda", type=["mp3", "wav", "m4a", "mp4"])

        if uploaded_file is not None:
            if uploaded_file.size > 26214400: 
                st.error("⚠️ Ukuran file melebihi 25MB. Silakan kompres audio Anda terlebih dahulu.")
            else:
                st.audio(uploaded_file)
                
                if not is_admin():
                    kuota_upload_sekarang = st.session_state.get("user_kuota_upload", 0)
                    if kuota_upload_sekarang <= 0:
                        st.error("❌ Kuota Upload Anda telah habis. Silakan hubungi Admin untuk upgrade paket.")
                    else:
                        if st.button("🎙️ Mulai Transkripsi (via LiteLLM Whisper)", use_container_width=True, type="primary"):
                            if not llm_key: 
                                st.warning("⚠️ Masukkan API Key LiteLLM terlebih dahulu!")
                            else:
                                with st.spinner("⏳ Sedang mentranskripsi audio..."):
                                    try:
                                        url = "https://litellm.koboi2026.biz.id/v1/audio/transcriptions"
                                        headers = {"Authorization": f"Bearer {llm_key}"}
                                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                                        data = {"model": "whisper-1", "response_format": "json"}
                                        response = requests.post(url, headers=headers, files=files, data=data)

                                        if response.status_code == 200:
                                            st.session_state["offline_transcript"] = response.json().get("text", "")
                                            st.session_state["user_kuota_upload"] -= 1
                                            db.collection("users").document(st.session_state["user_uid"]).update({
                                                "kuota_upload": st.session_state["user_kuota_upload"]
                                            })
                                            st.success(f"✅ Transkripsi berhasil! Sisa Kuota Upload: {st.session_state['user_kuota_upload']}x")
                                        else: 
                                            st.error(f"❌ Error dari API LiteLLM: {response.text}")
                                    except Exception as e: 
                                        st.error(f"Terjadi kesalahan saat menghubungi API: {str(e)}")
                else:
                    if st.button("🎙️ Mulai Transkripsi (via LiteLLM Whisper)", use_container_width=True, type="primary"):
                        if not llm_key: 
                            st.warning("⚠️ Masukkan API Key LiteLLM terlebih dahulu!")
                        else:
                            with st.spinner("⏳ Sedang mentranskripsi audio..."):
                                try:
                                    url = "https://litellm.koboi2026.biz.id/v1/audio/transcriptions"
                                    headers = {"Authorization": f"Bearer {llm_key}"}
                                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                                    data = {"model": "whisper-1", "response_format": "json"}
                                    response = requests.post(url, headers=headers, files=files, data=data)

                                    if response.status_code == 200:
                                        st.session_state["offline_transcript"] = response.json().get("text", "")
                                        st.success(f"✅ Transkripsi berhasil! (Admin Mode: Unlimited Access)")
                                    else: 
                                        st.error(f"❌ Error dari API LiteLLM: {response.text}")
                                except Exception as e: 
                                    st.error(f"Terjadi kesalahan saat menghubungi API: {str(e)}")

        if st.session_state["offline_transcript"]:
            st.markdown("#### 📝 Hasil Transkripsi")
            transcript_area = st.text_area("Edit jika perlu sebelum di-Summary:", value=st.session_state["offline_transcript"], height=250)
            st.session_state["offline_transcript"] = transcript_area 

            if not is_admin():
                kuota_ai_sekarang = st.session_state.get("user_kuota_ai", 0)
                if kuota_ai_sekarang <= 0:
                    st.error("❌ Kuota AI Summary Anda telah habis. Silakan hubungi Admin untuk upgrade.")
                else:
                    if st.button("✨ Generate AI Summary dari Teks Ini", use_container_width=True, type="secondary"):
                        if not llm_key: 
                            st.warning("⚠️ Masukkan API Key LiteLLM terlebih dahulu!")
                        else:
                            with st.spinner("⏳ AI sedang memproses JSON Notulensi & Visual..."):
                                prompt = f"""Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                                ATURAN JSON NOTULENSI:
                                - ringkasan_eksekutif: Buat array of strings (poin-poin padat).
                                - jalannya_diskusi: Buat array of strings. WAJIB NARASI DETAIL, PANJANG, dan LENGKAP.
                                - keputusan: Array of strings. Kesimpulan utama.
                                - rencana_tindak_lanjut: Ekstrak tabel penugasan. JIKA TIDAK ADA TUGAS spesifik, WAJIB BUAT 1 TUGAS DEFAULT.
                                - hubungan_topik (CYTOSCAPE): Ekstrak 5-15 entitas penting dan hubungannya.
                                ATURAN MARKMAP (PENTING!): Gunakan kode murni markdown dengan struktur lengkap.
                                ATURAN MERMAID: WAJIB format 'graph LR'.
                                Transkrip Rapat: "{st.session_state['offline_transcript']}" """

                                payload = {
                                    "model": "gemini/gemini-2.5-flash", "messages": [{ "role": "user", "content": prompt }], "temperature": 0.2,
                                    "response_format": {
                                        "type": "json_schema",
                                        "json_schema": {
                                            "name": "meeting_summary", "strict": False,
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
                                        st.session_state["offline_summary"] = json.loads(res.json()["choices"][0]["message"]["content"])
                                        st.session_state["user_kuota_ai"] -= 1
                                        db.collection("users").document(st.session_state["user_uid"]).update({
                                            "kuota_ai": st.session_state["user_kuota_ai"]
                                        })
                                        st.success(f"✅ AI Summary berhasil digenerate! Sisa Kuota AI: {st.session_state['user_kuota_ai']}x")
                                    else: 
                                        st.error(f"Error AI: {res.text}")
                                except Exception as e: 
                                    st.error(f"Koneksi LLM Gagal: {str(e)}")
            else:
                if st.button("✨ Generate AI Summary dari Teks Ini", use_container_width=True, type="secondary"):
                    if not llm_key: 
                        st.warning("⚠️ Masukkan API Key LiteLLM terlebih dahulu!")
                    else:
                        with st.spinner("⏳ AI sedang memproses JSON Notulensi & Visual..."):
                            prompt = f"""Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                            ATURAN JSON NOTULENSI:
                            - ringkasan_eksekutif: Buat array of strings (poin-poin padat).
                            - jalannya_diskusi: Buat array of strings. WAJIB NARASI DETAIL, PANJANG, dan LENGKAP.
                            - keputusan: Array of strings. Kesimpulan utama.
                            - rencana_tindak_lanjut: Ekstrak tabel penugasan. JIKA TIDAK ADA TUGAS spesifik, WAJIB BUAT 1 TUGAS DEFAULT.
                            - hubungan_topik (CYTOSCAPE): Ekstrak 5-15 entitas penting dan hubungannya.
                            ATURAN MARKMAP (PENTING!): Gunakan kode murni markdown dengan struktur lengkap.
                            ATURAN MERMAID: WAJIB format 'graph LR'.
                            Transkrip Rapat: "{st.session_state['offline_transcript']}" """

                            payload = {
                                "model": "gemini/gemini-2.5-flash", "messages": [{ "role": "user", "content": prompt }], "temperature": 0.2,
                                "response_format": {
                                    "type": "json_schema",
                                    "json_schema": {
                                        "name": "meeting_summary", "strict": False,
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
                                    st.session_state["offline_summary"] = json.loads(res.json()["choices"][0]["message"]["content"])
                                    st.success(f"✅ AI Summary berhasil digenerate! (Admin Mode: Unlimited Access)")
                                else: 
                                    st.error(f"Error AI: {res.text}")
                            except Exception as e: 
                                st.error(f"Koneksi LLM Gagal: {str(e)}")

        if st.session_state.get("offline_summary"):
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

            st.markdown("### 🕸️ Visualisasi")

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
                    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
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
                                    const link = document.createElement('a'); link.download = 'Mermaid_' + title + '.png'; link.href = canvas.toDataURL('image/png', 1.0); link.click();
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
            raw_markmap = data.get('markmap_code', '').replace("```markdown", "").replace("```", "").strip()

            markmap_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/markmap-lib@0.15.4/dist/browser/index.js"></script>
                <script src="https://cdn.jsdelivr.net/npm/markmap-view@0.15.4/dist/browser/index.js"></script>
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
                            svgEl.setAttribute('viewBox', (bbox.x - padding) + ' ' + (bbox.y - padding) + ' ' + trueWidth + ' ' + trueHeight);
                            svgEl.style.width = '100%'; svgEl.style.height = '100%';
                            setTimeout(() => {{
                                html2canvas(container, {{ scale: 2, useCORS: true, backgroundColor: '#ffffff', width: trueWidth, height: trueHeight }})
                                .then(canvas => {{
                                    container.style.width = originalWidth; container.style.height = originalHeight; container.style.overflow = originalOverflow;
                                    g.setAttribute('transform', originalTransform || '');
                                    if (originalViewBox) svgEl.setAttribute('viewBox', originalViewBox); else svgEl.removeAttribute('viewBox');
                                    const link = document.createElement('a'); link.download = 'MindMap_' + title + '.png';
                                    link.href = canvas.toDataURL('image/png', 1.0); link.click();
                                    btn.innerHTML = originalText; btn.disabled = false;
                                }}).catch(err => {{
                                    container.style.width = originalWidth; container.style.height = originalHeight; container.style.overflow = originalOverflow;
                                    g.setAttribute('transform', originalTransform || '');
                                    if (originalViewBox) svgEl.setAttribute('viewBox', originalViewBox); else svgEl.removeAttribute('viewBox');
                                    btn.innerHTML = "❌ GAGAL"; setTimeout(() => {{ btn.innerHTML = originalText; btn.disabled = false; }}, 2000);
                                }});
                            }}, 600);
                        }} catch (err) {{
                            btn.innerHTML = "❌ GAGAL"; setTimeout(() => {{ btn.innerHTML = originalText; btn.disabled = false; }}, 2000);
                        }}
                    }};
                </script>
            </body>
            </html>
            """
            components.html(markmap_html, height=450)

            with st.expander("Lihat Source Code Markdown"):
                st.code(raw_markmap, language="markdown")
