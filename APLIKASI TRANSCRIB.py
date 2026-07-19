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
                    paket_str = paket # <--- INI BARIS YANG DITAMBAHKAN
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
