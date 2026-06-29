import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import pandas as pd

# Konfigurasi Halaman (Hanya boleh dipanggil sekali di paling atas)
st.set_page_config(page_title="TranscribX - Enterprise AI", layout="wide")

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
    <script>
        const face = document.getElementById('germic-face');
        function trackMouse(clientX, clientY, screenWidth) {
            if (!face) return;
            const robotX = screenWidth * 0.2; const robotY = 125;
            const mouseX = clientX - robotX; const mouseY = clientY - robotY;
            const limit = 8;
            const moveX = Math.max(Math.min(mouseX / 50, limit), -limit);
            const moveY = Math.max(Math.min(mouseY / 50, limit), -limit);
            face.style.transform = `translate(${moveX}px, ${moveY}px)`;
            face.style.transition = "transform 0.1s ease-out";
        }
        document.addEventListener('mousemove', (e) => trackMouse(e.clientX, e.clientY, window.innerWidth));
        try { window.parent.document.addEventListener('mousemove', (e) => trackMouse(e.clientX, e.clientY, window.parent.innerWidth)); } catch (err) { }
    </script>
    """
    components.html(germic_html, height=250)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 13px; font-weight: bold;'>GERMIC System Online</p>", unsafe_allow_html=True)
    st.markdown("---")

# 1. INISIALISASI SESSION STATE
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "offline_transcript" not in st.session_state:
    st.session_state["offline_transcript"] = ""
if "offline_summary" not in st.session_state:
    st.session_state["offline_summary"] = None

# 2. LOGIN
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("")
        st.write("")
        st.markdown("<h2 style='text-align: center;'>🔒 Login TranscribX Enterprise</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b;'>Silakan masukkan kredensial untuk mengakses sistem Notulensi AI.</p>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Ketik username Anda di sini...")
            password = st.text_input("Password", type="password", placeholder="Ketik password Anda di sini...")
            submit_button = st.form_submit_button("🚀 Masuk ke Sistem", use_container_width=True)
            if submit_button:
                if username == "admin" and password == "12345":
                    st.session_state["logged_in"] = True
                    st.success("Login berhasil! Memuat sistem...")
                    st.rerun()
                else:
                    st.error("⚠️ Username atau password salah!")
else:
    colA, colB = st.columns([8, 1])
    with colB:
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.session_state["logged_in"] = False
            st.rerun()

    st.title("🎙️ TranscribX: Enterprise Transcription & AI Summarizer")
    tab1, tab2 = st.tabs(["🔴 Live Zoom (Web API)", "📁 Upload Rekaman (Offline LiteLLM)"])

    # =====================================================================
    # TAB 1: LIVE CAPTURE (HTML/JS)
    # =====================================================================
    with tab1:
        st.markdown("Mesin **Web Speech API** + **AI LiteLLM Summary** untuk Notulensi Otomatis dengan UI Enterprise.")
        st.info("💡 **TIPS ZOOM:** Agar web ini bisa mendengar Zoom, pastikan mikrofon browser menggunakan **Stereo Mix** atau **VB-Cable**.")

        html_code = """
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.tailwindcss.com"></script>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
            <script src="https://cdn.jsdelivr.net/npm/markmap-lib"></script>
            <script src="https://cdn.jsdelivr.net/npm/markmap-view"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/cytoscape/3.26.0/cytoscape.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
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
                .btn-ai { background: #8b5cf6; } .btn-ai:hover { background: #7c3aed; }
                .btn-custom:disabled { background: #94a3b8; cursor: not-allowed; }
                .btn-secondary { background: #e2e8f0; color: #334155; } .btn-secondary:hover { background: #cbd5e1; }
                select.btn-secondary, input.api-input { outline: none; border: 1px solid #cbd5e1; padding: 10px; border-radius: 8px; font-family: inherit; }
                input.api-input { flex-grow: 1; min-width: 250px; }
                .line-final { margin-bottom: 12px; padding: 12px; background: #f1f5f9; border-radius: 8px; border-left: 4px solid #3b82f6; font-size: 14px; line-height: 1.5; }
                .line-interim { margin-bottom: 12px; padding: 12px; background: #f8fafc; border-radius: 8px; border-left: 4px solid #cbd5e1; font-size: 14px; opacity: 0.7; font-style: italic; }
                .timestamp { font-weight: bold; color: #64748b; margin-right: 8px; font-size: 12px; }
                .reconnecting { color: #ef4444; font-size: 12px; margin-left: 8px; font-style: italic; }
                #audioContainer { display: flex; flex-direction: column; gap: 10px; }
                .audio-item { display: flex; align-items: center; gap: 15px; padding: 15px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; }
                .fade-in { animation: fadeIn 0.5s ease-in-out; }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
                .cy-container { width: 100%; height: 400px; border-radius: 16px; background: #f8fafc; border: 1px solid #e2e8f0; position: relative; }
                .btn-export { cursor:pointer; background:#10b981; color:white; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:bold; border:none; box-shadow:0 2px 4px rgba(0,0,0,0.1); transition: background 0.2s; }
                .btn-export:hover { background:#059669; }
            </style>
            <script>
                // FUNGSI DOWNLOAD PNG KHUSUS MARKMAP 
                // FUNGSI DOWNLOAD PNG (PERBAIKAN ANTI-CLIPPING)
window.downloadMarkmapImage = function(wrapperId, title, event) {
    const container = document.getElementById(wrapperId);
    const svgEl = container.querySelector('svg');
    if (!svgEl) return;

    const btn = event.currentTarget;
    const originalText = btn.innerHTML;
    btn.innerHTML = "⏳ MENYIMPAN...";
    btn.disabled = true;

    try {
        // Cari elemen grup utama markmap
        const g = svgEl.querySelector('g');
        if (!g) throw new Error("G element not found");

        // 1. Dapatkan dimensi bounding box yang sesungguhnya
        const bbox = g.getBBox();
        const padding = 60;
        
        // 2. Hitung dimensi kanvas yang dibutuhkan
        const trueWidth = bbox.width + (padding * 2);
        const trueHeight = bbox.height + (padding * 2);

        // 3. Gunakan html2canvas dengan offset scrollX/scrollY 
        // Ini lebih akurat daripada mengubah viewBox secara manual
        html2canvas(container, {
            scale: 2, // Kualitas HD
            width: trueWidth,
            height: trueHeight,
            // Menggeser fokus kamera html2canvas ke area BBox
            scrollX: -bbox.x + padding,
            scrollY: -bbox.y + padding,
            backgroundColor: '#ffffff',
            useCORS: true,
            onclone: (clonedDoc) => {
                const el = clonedDoc.getElementById(wrapperId);
                el.style.width = trueWidth + 'px';
                el.style.height = trueHeight + 'px';
                el.style.overflow = 'visible';
            }
        }).then(canvas => {
            const link = document.createElement('a');
            link.download = `MindMap_${title.replace(/[^a-zA-Z0-9]/g, "_")}.png`;
            link.href = canvas.toDataURL('image/png', 1.0);
            link.click();

            btn.innerHTML = originalText;
            btn.disabled = false;
        }).catch(err => {
            console.error("html2canvas error:", err);
            btn.innerHTML = "❌ GAGAL";
            setTimeout(() => { btn.innerHTML = originalText; btn.disabled = false; }, 2000);
        });

    } catch (err) {
        console.error("Error saving markmap:", err);
        btn.innerHTML = "❌ GAGAL";
        setTimeout(() => { btn.innerHTML = originalText; btn.disabled = false; }, 2000);
    }
};
                // FUNGSI DOWNLOAD MERMAID ASLI
                window.downloadMermaidImage = function(wrapperId, title, event) {
                    const container = document.getElementById(wrapperId);
                    const btn = event.currentTarget;
                    const originalText = btn.innerHTML;
                    btn.innerHTML = "⏳ MENYIMPAN..."; btn.disabled = true;

                    const originalOverflow = container.style.overflow;
                    container.style.overflow = 'visible'; 
                    
                    setTimeout(() => {
                        html2canvas(container, { scale: 2, useCORS: true, backgroundColor: '#ffffff' })
                        .then(canvas => {
                            container.style.overflow = originalOverflow;
                            const link = document.createElement('a'); link.download = `Mermaid_${title}.png`; link.href = canvas.toDataURL('image/png', 1.0); link.click();
                            btn.innerHTML = originalText; btn.disabled = false;
                        }).catch(err => {
                            container.style.overflow = originalOverflow; btn.innerHTML = "❌ GAGAL"; setTimeout(() => { btn.innerHTML = originalText; btn.disabled = false; }, 2000);
                        });
                    }, 500);
                };

                // FUNGSI EXPORT CYTOSCAPE FULL GRAPH
                window.myCyInstance = null;
                function exportCyToPng() {
                    if(!window.myCyInstance) return alert("Cytoscape belum siap!");
                    const b64 = window.myCyInstance.png({ full: true, scale: 4, bg: 'white' });
                    const a = document.createElement('a'); a.href = b64; a.download = 'Cytoscape_Map_HighRes.png'; a.click();
                }

                // FUNGSI EXPORT NOTULENSI KE TXT
                window.lastAiData = null;
                function exportNotulensiTxt() {
                    if(!window.lastAiData) return alert("Data Notulensi belum ada!");
                    const root = window.lastAiData;
                    const data = root.notulensi_rapat;
                    let txt = `NOTULENSI RAPAT\\n========================\\n\\n`;
                    txt += `RINGKASAN EKSEKUTIF:\\n`;
                    if(root.ringkasan_eksekutif) root.ringkasan_eksekutif.forEach(r => txt += `- ${r}\\n`);
                    txt += `\\nAgenda: ${data.agenda || '-'}\\nPeserta: ${data.peserta ? data.peserta.join(', ') : '-'}\\n\\n`;
                    txt += `Jalannya Diskusi:\\n`;
                    if(data.jalannya_diskusi) data.jalannya_diskusi.forEach(d => txt += `- ${d}\\n`);
                    txt += `\\nKeputusan Utama:\\n`;
                    if(data.keputusan) data.keputusan.forEach(k => txt += `- ${k}\\n`);
                    if(data.rencana_tindak_lanjut && data.rencana_tindak_lanjut.length > 0) {
                        txt += `\\nRencana Tindak Lanjut:\\n`; data.rencana_tindak_lanjut.forEach(t => txt += `- [${t.prioritas}] ${t.tugas} (PIC: ${t.pic}, Deadline: ${t.deadline})\\n`);
                    }
                    const blob = new Blob([txt], { type: 'text/plain' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'Notulensi_Resmi.txt'; a.click();
                }
            </script>
        </head>
        <body>
            <div class="controls-wrapper">
                <div class="controls-line">
                    <select id="langSelect" class="btn-custom btn-secondary"><option value="id-ID">🇮🇩 ID (Indonesia)</option><option value="en-US">🇬🇧 EN (English)</option></select>
                    <button id="startBtn" class="btn-custom">🚀 START CAPTURE</button>
                    <button id="stopBtn" class="btn-custom btn-stop" disabled>⏹️ STOP</button>
                    <div style="display: flex; align-items: center; gap: 8px; margin-left: auto;">
                        <div id="indicator" style="width: 12px; height: 12px; border-radius: 50%; background: #cbd5e1;"></div>
                        <span id="status" style="font-weight: bold; font-size: 14px; color: #64748b;">Standby...</span>
                    </div>
                </div>
                <div class="visualizer-container"><canvas id="visualizer"></canvas></div>
                <div class="controls-line" style="background: #e2e8f0; padding: 10px; border-radius: 10px;">
                    <span style="font-size: 14px; font-weight: bold;">🔑 LiteLLM API Key:</span>
                    <input type="password" id="apiKeyInput" class="api-input" placeholder="sk-...">
                    <button id="aiBtn" class="btn-custom btn-ai">✨ Generate AI Summary & Mindmap</button>
                </div>
                <div class="controls-line" style="justify-content: flex-end;">
                    <button id="copyBtn" class="btn-custom btn-secondary">📋 Copy Text</button>
                    <button id="clearBtn" class="btn-custom btn-secondary">🗑️ Clear</button>
                    <button id="downloadTxtBtn" class="btn-custom" style="background: #10b981;">📝 Save TXT</button>
                </div>
            </div>

            <div id="transcriptBox" class="transcript-box">
                <div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px;">Suara yang ditangkap akan muncul di sini...</div>
            </div>

            <div id="aiContent" class="w-full"></div>
            <h3 style="margin-bottom: 10px; font-size: 16px; margin-top: 20px;">🎧 Arsip Rekaman Suara</h3>
            <div id="audioContainer"></div>

            <script>
                mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose', flowchart: { htmlLabels: true, curve: 'basis' } });

                const startBtn = document.getElementById('startBtn'); const stopBtn = document.getElementById('stopBtn');
                const copyBtn = document.getElementById('copyBtn'); const clearBtn = document.getElementById('clearBtn');
                const downloadTxtBtn = document.getElementById('downloadTxtBtn'); const aiBtn = document.getElementById('aiBtn');
                const apiKeyInput = document.getElementById('apiKeyInput'); const aiContent = document.getElementById('aiContent');
                const langSelect = document.getElementById('langSelect'); const status = document.getElementById('status');
                const indicator = document.getElementById('indicator'); const transcriptBox = document.getElementById('transcriptBox');
                const audioContainer = document.getElementById('audioContainer'); const visualizer = document.getElementById('visualizer');
                const canvasCtx = visualizer.getContext('2d');

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
                            audioChunks = []; mediaRecorder = new MediaRecorder(audioStream);
                            mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
                            mediaRecorder.onstop = () => {
                                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                                const audioUrl = URL.createObjectURL(blob); const fileName = 'Rekaman_TranscribX_' + new Date().getTime() + '.webm';
                                const audioItem = document.createElement('div'); audioItem.className = 'audio-item';
                                audioItem.innerHTML = `<audio controls src="${audioUrl}"></audio> <a href="${audioUrl}" download="${fileName}" class="btn-custom" style="background:#10b981;">💾 Download Audio</a>`;
                                audioContainer.prepend(audioItem);
                            };
                            setupVisualizer(audioStream); mediaRecorder.start(); recognition.start(); drawVisualizer(); isRecording = true;
                            status.innerText = "Merekam (" + (langSelect.value === 'id-ID' ? 'ID' : 'EN') + ")..."; indicator.style.background = "#ef4444"; indicator.style.boxShadow = "0 0 10px #ef4444";
                            startBtn.disabled = true; stopBtn.disabled = false; langSelect.disabled = true;
                            if(document.getElementById('placeholder')) document.getElementById('placeholder').style.display = 'none';
                        } catch(err) { console.error("Gagal akses mic:", err); status.innerText = "Izin Mic Ditolak!"; }
                    };

                    stopBtn.onclick = () => {
                        isRecording = false; recognition.stop();
                        if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
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
                        const blob = new Blob([text], { type: 'text/plain' }); const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'Transkrip_Raw_' + new Date().getTime() + '.txt'; a.click();
                    };

                    clearBtn.onclick = () => {
                        if(confirm("Yakin ingin menghapus semua teks di layar?")) {
                            transcriptBox.innerHTML = '<div id="placeholder" style="text-align: center; color: #94a3b8; margin-top: 100px;">Suara yang ditangkap akan muncul di sini...</div>';
                            lastFinalText = ""; aiContent.innerHTML = "";
                        }
                    };

                    aiBtn.onclick = async () => {
                        const transcript = getTranscriptText(); const apiKey = apiKeyInput.value.trim();
                        if (!apiKey) { alert("⚠️ Masukkan API Key LiteLLM/Gemini terlebih dahulu."); apiKeyInput.focus(); return; }
                        if (!transcript) { alert("⚠️ Transkrip masih kosong."); return; }

                        const originalText = aiBtn.innerHTML; aiBtn.innerHTML = "⏳ AI sedang memproses JSON..."; aiBtn.disabled = true;
                        aiContent.innerHTML = `<div class="p-8 bg-purple-50 rounded-[2.5rem] border border-purple-200 shadow-sm text-center fade-in mt-6"><p class="text-purple-600 font-bold animate-pulse">Memproses Notulensi, Cytoscape, Markmap & Mermaid... Mohon tunggu (±15 detik).</p></div>`;

                        const prompt = `Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                        ATURAN RINGKASAN EKSEKUTIF: Buat ringkasan padat dalam bentuk array of strings (poin-poin) dari keseluruhan rapat.
                        ATURAN JALANNYA DISKUSI: Buat jalannya diskusi dalam bentuk array of strings (poin-poin kronologis).
                        ATURAN KEPUTUSAN PENTING: WAJIB merumuskan poin-poin kesimpulan utama ke dalam array "keputusan".
                        ATURAN RENCANA TINDAK LANJUT: Ekstrak juga rencana tindak lanjut (Tugas, PIC, Deadline, Prioritas).
                        ATURAN HUBUNGAN TOPIK (CYTOSCAPE): Ekstrak 5-15 kata kunci/entitas penting dan hubungannya.
                        ATURAN MERMAID: WAJIB gunakan format 'graph LR'. Format node HARUS menggunakan tanda kutip ganda. Root/Pangkal utama diagram WAJIB berisi Judul Topik Rapat/Agenda, contoh: A["Topik Rapat X"] --> B["Ringkasan Eksekutif"].
                        ATURAN MARKMAP: Gunakan kode murni markdown. Baris paling pertama/utama WAJIB berisi judul utama: "# [Judul/Topik Utama Rapat]". Di bawahnya, buat sub-header (##) untuk "Ringkasan Eksekutif", "Agenda", "Diskusi", dll. Pastikan isi dari ringkasan eksekutif dan diskusi di-breakdown menjadi list/bullet points (- poin 1\\n- poin 2).
                        Transkrip Rapat: "${transcript}"`;

                        const payload = {
                            "model": "gemini/gemini-2.5-flash", "messages": [{ "role": "user", "content": prompt }], "temperature": 0.2,
                            "response_format": {
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "meeting_summary", "strict": true,
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
                        };

                        try {
                            const response = await fetch("https://litellm.koboi2026.biz.id/v1/chat/completions", { method: "POST", headers: { "Authorization": "Bearer " + apiKey, "Content-Type": "application/json" }, body: JSON.stringify(payload) });
                            const resJson = await response.json();

                            if (resJson.choices && resJson.choices[0].message.content) {
                                const data = JSON.parse(resJson.choices[0].message.content);
                                window.lastAiData = data;
                                const reportDiv = document.createElement('div'); reportDiv.className = "fade-in space-y-6 mt-6 mb-10";
                                
                                let taskListHtml = '';
                                if (data.notulensi_rapat.rencana_tindak_lanjut.length > 0) {
                                    taskListHtml = `<div class="mt-4 pt-4 border-t border-slate-100"><p class="font-black text-blue-600 uppercase text-[10px] mb-2">📋 Rencana Tindak Lanjut:</p><div class="overflow-x-auto rounded-lg border border-slate-200"><table class="w-full text-left border-collapse"><tr class="bg-blue-50 text-blue-800 text-[11px]"><th class="p-2 border-b border-r">Tugas</th><th class="p-2 border-b border-r">PIC</th><th class="p-2 border-b border-r">Deadline</th><th class="p-2 border-b">Prioritas</th></tr>
                                    ${data.notulensi_rapat.rencana_tindak_lanjut.map(t => `<tr class="text-[12px] border-b bg-white"><td class="p-2 border-r font-medium">${t.tugas}</td><td class="p-2 border-r text-slate-600">${t.pic}</td><td class="p-2 border-r text-slate-600">${t.deadline}</td><td class="p-2 font-bold">${t.prioritas}</td></tr>`).join('')}</table></div></div>`;
                                }

                                let notulensiHtml = `
                                    <div class="p-8 bg-slate-50 rounded-[2.5rem] border border-slate-200 shadow-sm relative overflow-hidden mb-6">
                                        <div class="flex justify-between items-center mb-4">
                                            <h5 class="text-[14px] font-black text-slate-500 uppercase tracking-widest">NOTULENSI RESMI RAPAT</h5>
                                            <button onclick="exportNotulensiTxt()" class="btn-export">📝 Download TXT</button>
                                        </div>
                                        <div class="space-y-4 text-sm text-slate-700 leading-relaxed">
                                            <div>
                                                <p class="font-black text-blue-600 uppercase text-[11px] mb-1">RINGKASAN EKSEKUTIF:</p>
                                                <div class="bg-blue-50 p-4 rounded-xl border border-blue-100">
                                                    <ul class="list-disc ml-5 space-y-1 font-semibold text-slate-800">${data.ringkasan_eksekutif.map(r => `<li>${r}</li>`).join('')}</ul>
                                                </div>
                                            </div>
                                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                                <div><p class="font-black text-blue-600 uppercase text-[11px] mb-1">AGENDA / TOPIK:</p><p class="font-medium">${data.notulensi_rapat.agenda || '-'}</p></div>
                                                <div><p class="font-black text-blue-600 uppercase text-[11px] mb-1">PESERTA:</p><p class="font-medium">${data.notulensi_rapat.peserta.join(', ') || '-'}</p></div>
                                            </div>
                                            <div>
                                                <p class="font-black text-blue-600 uppercase text-[11px] mb-1">JALANNYA DISKUSI:</p>
                                                <div class="bg-white/50 p-3 rounded-xl border border-slate-100">
                                                    <ul class="list-disc ml-5 space-y-1">${data.notulensi_rapat.jalannya_diskusi.map(d => `<li>${d}</li>`).join('')}</ul>
                                                </div>
                                            </div>
                                            <div>
                                                <p class="font-black text-blue-600 uppercase text-[11px] mb-1">KEPUTUSAN / KESIMPULAN UTAMA:</p>
                                                <ul class="list-disc ml-5 space-y-1 font-bold text-slate-800">${data.notulensi_rapat.keputusan.map(k => `<li>${k}</li>`).join('')}</ul>
                                            </div>
                                            ${taskListHtml}
                                        </div>
                                    </div>
                                `;

                                let rawMermaid = data.visual_mindmap.replace(/```mermaid/gi, '').replace(/```/g, '').trim();
                                if (!rawMermaid.toLowerCase().includes('graph') && !rawMermaid.toLowerCase().includes('mindmap')) {
                                    rawMermaid = "graph LR\\n" + rawMermaid;
                                }

                                let rawMarkmap = data.markmap_code.replace(/```markdown/gi, '').replace(/```/g, '').trim();

                                let visualizationHtml = `
                                    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                                        <div class="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm flex flex-col">
                                            <div class="flex justify-between items-center mb-4"><h5 class="text-[10px] font-black text-emerald-600 uppercase tracking-widest flex items-center gap-2"><span>🌿</span> Markmap (Markdown)</h5><button onclick="downloadMarkmapImage('markmap-capture-area', 'Markmap', event)" class="btn-export">📸 PNG</button></div>
                                            <div id="markmap-capture-area" class="flex-grow bg-slate-50 border border-slate-100 rounded-2xl overflow-hidden markmap-svg-container relative p-2" style="min-height: 400px;"></div>
                                        </div>
                                        
                                        <div class="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm flex flex-col">
                                            <div class="flex justify-between items-center mb-4"><h5 class="text-[10px] font-black text-indigo-600 uppercase tracking-widest flex items-center gap-2"><span>🌊</span> Mermaid.js (Mindmap)</h5><button onclick="downloadMermaidImage('mermaid-capture-area', 'Mermaid', event)" class="btn-export">📸 PNG</button></div>
                                            <div id="mermaid-capture-area" class="flex-grow bg-slate-50 border border-slate-100 rounded-2xl overflow-x-auto p-4 mermaid-container">
                                                <div class="mermaid">${rawMermaid}</div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="p-6 bg-white rounded-3xl border border-slate-200 shadow-sm flex flex-col mb-6">
                                        <div class="flex justify-between items-center mb-4"><h5 class="text-[10px] font-black text-rose-600 uppercase tracking-widest flex items-center gap-2"><span>🕸️</span> Cytoscape.js (Jejaring Topik)</h5><button onclick="exportCyToPng()" class="btn-export">📸 PNG (Full Scale)</button></div>
                                        <div id="cy" class="cy-container"></div>
                                    </div>
                                `;

                                reportDiv.innerHTML = notulensiHtml + visualizationHtml;
                                aiContent.innerHTML = ""; aiContent.appendChild(reportDiv);

                                // 1. Render Markmap
                                try {
                                    if (!window.markmap) throw new Error("Library Markmap gagal dimuat.");
                                    const { Transformer, Markmap } = window.markmap; const { root } = new Transformer().transform(rawMarkmap);
                                    const svgContainer = document.getElementById('markmap-capture-area'); svgContainer.innerHTML = '<svg id="markmap-svg" style="width:100%; height:400px; min-height:400px;"></svg>';
                                    Markmap.create(document.getElementById('markmap-svg'), null, root);
                                } catch (e) { console.error("Markmap Render Error:", e); document.getElementById('markmap-capture-area').innerHTML = `<p class="text-red-500 font-bold p-4 text-xs">Error merender Markmap: ${e.message}</p>`; }

                                // 2. Render Mermaid 
                                setTimeout(() => {
                                    try { mermaid.run({ querySelector: '.mermaid' }); }
                                    catch (e) { document.querySelector('.mermaid').innerHTML = `<p class="text-red-500 text-xs font-bold">⚠️ Error sintaks dari AI. Coba generate ulang.</p>`; }
                                }, 500);

                                // 3. Render Cytoscape
                                setTimeout(() => {
                                    try {
                                        const cyElements = []; const nodesSet = new Set();
                                        data.notulensi_rapat.hubungan_topik.forEach(rel => {
                                            if (!nodesSet.has(rel.sumber)) { nodesSet.add(rel.sumber); cyElements.push({ data: { id: rel.sumber, label: rel.sumber } }); }
                                            if (!nodesSet.has(rel.target)) { nodesSet.add(rel.target); cyElements.push({ data: { id: rel.target, label: rel.target } }); }
                                            cyElements.push({ data: { source: rel.sumber, target: rel.target, label: rel.relasi } });
                                        });
                                        window.myCyInstance = cytoscape({
                                            container: document.getElementById('cy'), elements: cyElements,
                                            style: [{ selector: 'node', style: { 'background-color': '#f43f5e', 'label': 'data(label)', 'color': '#1e293b', 'font-size': '12px', 'text-valign': 'top', 'text-halign': 'center', 'text-margin-y': -5, 'width': 30, 'height': 30 } }, { selector: 'edge', style: { 'width': 2, 'line-color': '#cbd5e1', 'target-arrow-color': '#cbd5e1', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'label': 'data(label)', 'font-size': '10px', 'color': '#64748b', 'text-rotation': 'autorotate', 'text-background-opacity': 1, 'text-background-color': '#ffffff', 'text-background-padding': 3 } }],
                                            layout: { name: 'cose', padding: 20 }
                                        });
                                    } catch (e) { console.error("Cytoscape Error:", e); document.getElementById('cy').innerHTML = `<p class="text-red-500 font-bold p-4 text-xs">Error merender Cytoscape: ${e.message}</p>`; }
                                }, 600);

                            } else if (resJson.error) { aiContent.innerHTML = `<p class="text-red-500 font-bold p-4 bg-red-50 rounded-xl mt-6">Error: ${resJson.error.message}</p>`; }
                        } catch (err) { aiContent.innerHTML = `<p class="text-red-500 font-bold p-4 bg-red-50 rounded-xl mt-6">Koneksi Gagal: Cek API Key. Detail: ${err.message}</p>`; }
                        finally { aiBtn.innerHTML = originalText; aiBtn.disabled = false; aiContent.scrollIntoView({ behavior: 'smooth' }); }
                    };
                }
            </script>
        </body>
        </html>
        """
        components.html(html_code, height=1350, scrolling=True)

    # =====================================================================
    # TAB 2: FITUR OFFLINE TRANSCRIPTION (PYTHON/STREAMLIT NATIVE)
    # =====================================================================
    with tab2:
        st.markdown("### 📁 Transkripsi File Rekaman (Offline)")
        st.info("💡 Sistem ini menggunakan **LiteLLM Proxy** untuk proses Transkripsi (Whisper) sekaligus Summarization (Gemini). Pastikan server LiteLLM Anda sudah siap.")

        llm_key = st.text_input("🔑 API Key LiteLLM (All-in-One)", type="password", placeholder="sk-...", help="API Key untuk proxy LiteLLM Anda")
        uploaded_file = st.file_uploader("Upload File Rekaman Anda", type=["mp3", "wav", "m4a", "mp4"])

        if uploaded_file is not None:
            if uploaded_file.size > 26214400: st.error("⚠️ Ukuran file melebihi 25MB. Silakan kompres audio Anda terlebih dahulu.")
            else:
                st.audio(uploaded_file)
                if st.button("🎙️ Mulai Transkripsi (via LiteLLM Whisper)", use_container_width=True, type="primary"):
                    if not llm_key: st.warning("⚠️ Masukkan API Key LiteLLM terlebih dahulu!")
                    else:
                        with st.spinner("⏳ Sedang mentranskripsi audio... Proses ini memakan waktu tergantung durasi file."):
                            try:
                                url = "https://litellm.koboi2026.biz.id/v1/audio/transcriptions"
                                headers = {"Authorization": f"Bearer {llm_key}"}
                                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                                data = {"model": "whisper-1", "response_format": "json"}
                                response = requests.post(url, headers=headers, files=files, data=data)

                                if response.status_code == 200:
                                    st.session_state["offline_transcript"] = response.json().get("text", "")
                                    st.success("✅ Transkripsi berhasil!")
                                else: st.error(f"❌ Error dari API LiteLLM: {response.text}")
                            except Exception as e: st.error(f"Terjadi kesalahan saat menghubungi API: {str(e)}")

        if st.session_state["offline_transcript"]:
            st.markdown("#### 📝 Hasil Transkripsi")
            transcript_area = st.text_area("Edit jika perlu sebelum di-Summary:", value=st.session_state["offline_transcript"], height=250)
            st.session_state["offline_transcript"] = transcript_area 

            if st.button("✨ Generate AI Summary dari Teks Ini", use_container_width=True, type="secondary"):
                if not llm_key: st.warning("⚠️ Masukkan API Key LiteLLM terlebih dahulu!")
                else:
                    with st.spinner("⏳ AI sedang memproses JSON Notulensi & Visual..."):
                        
                        prompt = f"""Anda adalah Ahli Pembuat Notulensi dan Visual Mapping. Analisis transkrip rapat berikut dan hasilkan JSON.
                        ATURAN RINGKASAN EKSEKUTIF: Buat ringkasan padat dalam bentuk array of strings (poin-poin) dari keseluruhan rapat.
                        ATURAN JALANNYA DISKUSI: Buat jalannya diskusi dalam bentuk array of strings (poin-poin kronologis).
                        ATURAN KEPUTUSAN PENTING (CRITICAL): WAJIB merumuskan poin-poin kesimpulan utama ke dalam array "keputusan".
                        ATURAN RENCANA TINDAK LANJUT: Ekstrak juga rencana tindak lanjut (Tugas, PIC, Deadline, Prioritas).
                        ATURAN HUBUNGAN TOPIK (CYTOSCAPE): Ekstrak 5-15 kata kunci/entitas penting dan hubungannya (sumber -> relasi -> target).
                        ATURAN MERMAID: WAJIB gunakan format 'graph LR'. Format node HARUS menggunakan tanda kutip ganda. Root/Pangkal utama diagram WAJIB berisi Judul Topik Rapat/Agenda, contoh: A["Topik Rapat X"] --> B["Ringkasan Eksekutif"].
                        ATURAN MARKMAP: Gunakan kode murni markdown. Baris paling pertama/utama WAJIB berisi judul utama: "# [Judul/Topik Utama Rapat]". Di bawahnya, buat sub-header (##) untuk "Ringkasan Eksekutif", "Agenda", "Diskusi", dll. Pastikan isi dari ringkasan eksekutif dan diskusi di-breakdown menjadi list/bullet points (- poin 1\\n- poin 2).
                        Transkrip Rapat: "{st.session_state['offline_transcript']}" """

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
                            if res.status_code == 200: st.session_state["offline_summary"] = json.loads(res.json()["choices"][0]["message"]["content"])
                            else: st.error(f"Error AI: {res.text}")
                        except Exception as e: st.error(f"Koneksi LLM Gagal: {str(e)}")

        if st.session_state["offline_summary"]:
            data = st.session_state["offline_summary"]
            st.markdown("---")
            
            col_t1, col_t2 = st.columns([3, 1])
            with col_t1: st.markdown("### 📋 Laporan Notulensi AI")
            
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
            
            with col_t2: st.download_button(label="📝 Download Notulensi (TXT)", data=txt_report, file_name="Notulensi_Offline.txt", mime="text/plain", use_container_width=True)

            with st.container(border=True):
                st.markdown("**🌟 Ringkasan Eksekutif:**")
                # Format ke dalam div dengan bullet points (UI Streamlit)
                rx_html = "<div style='background-color:#eff6ff; padding:15px; border-radius:10px; color:#1e3a8a; font-weight:bold; margin-bottom:15px;'><ul style='margin:0; padding-left:20px;'>"
                for r in data.get('ringkasan_eksekutif', []): rx_html += f"<li>{r}</li>"
                rx_html += "</ul></div>"
                st.markdown(rx_html, unsafe_allow_html=True)
                
                colA, colB = st.columns(2)
                colA.markdown(f"**📌 Agenda / Topik:**<br>{data['notulensi_rapat']['agenda']}", unsafe_allow_html=True)
                colB.markdown(f"**👥 Peserta:**<br>{', '.join(data['notulensi_rapat']['peserta'])}", unsafe_allow_html=True)
                
                st.markdown("**🗣️ Jalannya Diskusi:**")
                diskusi_html = "<div style='background-color:#f8fafc; padding:15px; border-radius:10px; border: 1px solid #e2e8f0; margin-bottom:15px;'><ul style='margin:0; padding-left:20px;'>"
                for d in data['notulensi_rapat'].get('jalannya_diskusi', []): diskusi_html += f"<li style='margin-bottom:5px;'>{d}</li>"
                diskusi_html += "</ul></div>"
                st.markdown(diskusi_html, unsafe_allow_html=True)
                
                st.markdown("**✅ Keputusan / Takeaways Utama:**")
                for kep in data['notulensi_rapat']['keputusan']: st.markdown(f"- {kep}")
                
                st.markdown("**📅 Rencana Tindak Lanjut (Action Items):**")
                if "rencana_tindak_lanjut" in data['notulensi_rapat'] and data['notulensi_rapat']['rencana_tindak_lanjut']:
                    df_tasks = pd.DataFrame(data['notulensi_rapat']['rencana_tindak_lanjut'])
                    df_tasks.columns = ["Tugas", "PIC", "Deadline", "Prioritas"]
                    st.table(df_tasks)
                else: st.warning("Tidak ada Rencana Tindak Lanjut yang terdeteksi.")

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

            st.markdown("### 🌿 Visualisasi Markmap (Mindmap)")
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
