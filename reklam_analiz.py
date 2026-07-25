import streamlit as st
import pandas as pd
import cv2
import requests
import os
import numpy as np
from datetime import datetime, timedelta
import json

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Pro Meta Reklam Analizörü v2.0", layout="wide", page_icon="📈")

# --- YENİ MODERN ARAYÜZ STİLİ (Görseldeki Tasarım) ---
st.markdown("""
    <style>
    /* Ana Arka Plan (Koyu Lacivert) */
    .stApp {
        background-color: #0d1117;
        color: #ffffff;
    }
    
    /* Yan Menü (Sidebar) Koyu Tema */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Sekme (Tab) Tasarımları */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 12px;
        color: #8b949e;
        padding: 10px 20px;
        font-weight: 600;
        border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background-color: #238636 !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* Görseldeki Mor/Mavi Gradyan Kart */
    .gradient-card-purple {
        background: linear-gradient(135deg, #6a11cb 0%, #2575fc 100%);
        border-radius: 20px;
        padding: 22px;
        color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }

    /* Görseldeki Kırmızı/Turuncu Gradyan Kart */
    .gradient-card-red {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        border-radius: 20px;
        padding: 22px;
        color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }

    /* Görseldeki Açık Koyu Kart */
    .dark-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 20px;
        padding: 22px;
        color: white;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        margin-bottom: 15px;
    }

    .card-title {
        font-size: 0.9rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }

    .card-value {
        font-size: 2.2rem;
        font-weight: 700;
    }

    /* Buton Tasarımları */
    .stButton>button {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        color: white;
        border-radius: 14px;
        font-weight: bold;
        border: none;
        padding: 12px 24px;
        width: 100%;
        box-shadow: 0 4px 15px rgba(255, 65, 108, 0.4);
    }
    .stButton>button:hover {
        opacity: 0.9;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Pro Meta Reklam & Kreatif Analiz Merkezi")
st.markdown("*Dijital Reklamcılık Uzmanı Asistanınız (Veri Odaklı Kârlılık Mimarisi)*")

# --- Sidebar - API Kurulumları ---
st.sidebar.header("🔑 Güvenli API Bağlantıları")
st.sidebar.markdown("Verileriniz yerelinizde işlenir, sunucuya gönderilmez.")

meta_token = st.sidebar.text_input("1. Meta System User Access Token", type="password", help="Business Manager'dan alınan, reklam okuma yetkili kalıcı token.")
ad_account_id = st.sidebar.text_input("2. Reklam Hesabı ID", help="Sadece rakamlar. Örn: 1234567890")
openai_key = st.sidebar.text_input("3. OpenAI API Key", type="password", help="gpt-4o veya gpt-3.5-turbo erişimi olan key.")

st.sidebar.markdown("---")
target_cpa = st.sidebar.number_input("🎯 Hedef Müşteri Edinme Maliyeti (CPA) TL", value=100.0, step=10.0, help="Kârlı olmanız için gereken maksimum sipariş başı maliyet.")

# --- FONKSİYONLAR (Orijinal Mantık Korundu) ---

def fetch_meta_data(token, account_id):
    """Meta Graph API'den gerçek reklam performans verilerini çeker."""
    if not token or not account_id:
        return None
    
    clean_id = account_id.replace("act_", "")
    url = f"https://graph.facebook.com/v19.0/act_{clean_id}/insights"
    fields = "campaign_name,adset_name,ad_name,spend,impressions,clicks,cpc,ctr,actions,cost_per_action_type,conversions"
    
    params = {
        'access_token': token,
        'level': 'ad',
        'date_preset': 'last_30d',
        'fields': fields,
        'limit': 100
    }
    
    with st.spinner("Meta'dan canlı veriler çekiliyor..."):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data:
                st.error(f"API Hatası: {data.get('error', {}).get('message', 'Bilinmeyen hata')}")
                return None
                
            return process_meta_data(data['data'])
            
        except Exception as e:
            st.error(f"Bağlantı Hatası: {str(e)}")
            return None

def process_meta_data(raw_data):
    """API'den gelen karmaşık JSON verisini temiz Pandas DataFrame'e çevirir."""
    processed_list = []
    for ad in raw_data:
        ad_data = {
            'Reklam Adı': ad.get('ad_name'),
            'Kampanya': ad.get('campaign_name'),
            'Harcanan (TL)': float(ad.get('spend', 0)),
            'Tıklama Oranı (CTR %)': float(ad.get('ctr', 0)) * 100,
            'Tıklama (CPC)': float(ad.get('cpc', 0)),
        }
        
        purchases = 0
        purchase_value = 0
        
        if 'actions' in ad:
            for action in ad['actions']:
                if action['action_type'] == 'purchase':
                    purchases = int(action['value'])
        
        if 'conversions' in ad:
             for conv in ad['conversions']:
                if conv['action_type'] == 'purchase':
                    purchase_value = float(conv.get('value', 0)) 

        ad_data['Sipariş'] = purchases
        ad_data['CPA (E.Maliyet)'] = ad_data['Harcanan (TL)'] / purchases if purchases > 0 else 0
        ad_data['ROAS'] = purchase_value / ad_data['Harcanan (TL)'] if ad_data['Harcanan (TL)'] > 0 and purchase_value > 0 else 0
        
        processed_list.append(ad_data)
        
    df = pd.DataFrame(processed_list)
    return df

def ask_ai(api_key, system_prompt, user_prompt):
    """OpenAI API'sini kullanarak teşhis ve senaryo üretir."""
    if not api_key:
        return "⚠️ OpenAI API Key girilmediği için analiz yapılamıyor."
        
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }
    
    with st.spinner("Yapay Zeka derinlemesine düşünüyor..."):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return f"❌ AI Analiz Hatası: {str(e)}"

# --- ANA ARAYÜZ ---

tab1, tab2, tab3 = st.tabs(["📊 Performans Paneli (Canlı)", "🎥 Kreatif Stüdyo", "🧠 AI Performans Dedektifi"])

df_reklamlar = None

with tab1:
    st.header("📋 Gerçek Reklam Verileriniz (Son 30 Gün)")
    
    if meta_token and ad_account_id:
        df_reklamlar = fetch_meta_data(meta_token, ad_account_id)
        
        if df_reklamlar is not None and not df_reklamlar.empty:
            st.success(f"{len(df_reklamlar)} adet aktif reklam verisi çekildi.")
            
            # Özet Metrikler - GÖRSELDEKİ ÖZEL KART TASARIMLARI
            total_spend = df_reklamlar['Harcanan (TL)'].sum()
            total_purchases = df_reklamlar['Sipariş'].sum()
            avg_ctr = df_reklamlar['Tıklama Oranı (CTR %)'].mean()
            avg_cpa = total_spend / total_purchases if total_purchases > 0 else 0
            
            st.markdown("### 📈 Dashboard Özeti")
            m_col1, m_col2 = st.columns(2)
            
            with m_col1:
                st.markdown(f"""
                    <div class="gradient-card-purple">
                        <div class="card-title">Toplam Harcama</div>
                        <div class="card-value">{total_spend:,.2f} TL</div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="dark-card">
                        <div class="card-title">Ortalama CTR</div>
                        <div class="card-value">%{avg_ctr:.2f}</div>
                    </div>
                """, unsafe_allow_html=True)

            with m_col2:
                st.markdown(f"""
                    <div class="gradient-card-red">
                        <div class="card-title">Ortalama CPA (Edinme Maliyeti)</div>
                        <div class="card-value">{avg_cpa:,.2f} TL</div>
                    </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                    <div class="dark-card">
                        <div class="card-title">Toplam Sipariş</div>
                        <div class="card-value">{total_purchases} Adet</div>
                    </div>
                """, unsafe_allow_html=True)

            # Tablo renklendirme
            def style_cpa(row):
                if row['Sipariş'] == 0 and row['Harcanan (TL)'] > 50:
                    return ['background-color: #4a1525; color: #ff9999'] * len(row)
                elif row['CPA (E.Maliyet)'] > target_cpa and row['Sipariş'] > 0:
                    return ['background-color: #4d3319; color: #ffcc80'] * len(row)
                elif row['CPA (E.Maliyet)'] <= target_cpa and row['Sipariş'] > 0:
                    return ['background-color: #123825; color: #a3e635'] * len(row)
                else:
                    return [''] * len(row)

            st.dataframe(df_reklamlar.style.apply(style_cpa, axis=1), use_container_width=True)

        else:
            st.info("API'den veri dönmedi veya hesapta aktif reklam yok.")
            
    else:
        st.warning("⚠️ Soldaki sidebar'a **Meta Access Token** ve **Reklam Hesabı ID** girerek canlı verilerinizi görün.")

with tab2:
    st.header("📹 Profesyonel Video Analizi")
    st.write("Video yükleme ve yerel OpenCV analizi buraya gelecek (Bir sonraki aşamanın konusu).")
    uploaded_file = st.file_uploader("Analiz etmek istediğiniz reklam videosunu yükleyin", type=["mp4", "mov"])

with tab3:
    st.header("🧠 Yapay Zeka Teşhis ve Strateji Raporu")
    
    if df_reklamlar is not None and not df_reklamlar.empty:
        reklam_listesi = df_reklamlar['Reklam Adı'].tolist()
        secilen_reklam_adi = st.selectbox("Analiz edilecek reklamı seçin:", reklam_listesi)
        
        reklam_verisi = df_reklamlar[df_reklamlar['Reklam Adı'] == secilen_reklam_adi].iloc[0]
        metrics_json = reklam_verisi.to_json(force_ascii=False)
        
        st.markdown("### 📊 Mevcut Durum Metrikleri")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Harcama", f"{reklam_verisi['Harcanan (TL)']:.2f} TL")
        c2.metric("Sipariş", reklam_verisi['Sipariş'])
        c3.metric("CPA", f"{reklam_verisi['CPA (E.Maliyet)']:.2f} TL")
        c4.metric("CTR", f"%{reklam_verisi['Tıklama Oranı (CTR %)']:.2f}")

        if st.button("🚀 Derin AI Analizini Başlat"):
            if not openai_key:
                st.error("Lütfen sidebar'a OpenAI API Key girin.")
            else:
                system_prompt = f"""
                Sen 20 yıllık deneyime sahip Kıdemli bir Medya Alım Uzmanı ve Dijital Pazarlama Stratejistisin.
                Sana bir Meta (Facebook/Instagram) reklamının performans verilerini JSON formatında vereceğim.
                Görevin; bu verileri analiz edip, reklamın neden kârlı olmadığını (veya kârlıysa nasıl ölçekleneceğini) teşhis etmek.
                Hedef CPA (Müşteri Edinme Maliyeti) {target_cpa} TL'dir. Bu hedefe göre yorum yap.
                Analizin teknik ve aksiyon odaklı olmalı.

                Yatıtını şu formatta ver:
                1. **TEŞHİS:** (Kreatif mi, Web Sitesi mi, Hedef Kitle mi sorunlu? Verilere dayanarak açıkla).
                2. **TEKNİK AKSİYONLAR:** (Medya alım tarafında ne yapılmalı? Bütçe, Teklif, Kitle ayarları).
                3. **KREATİF SENARYOLAR (3 Adet):** (Siparişi artıracak, psikolojik kancalara sahip, 3 yeni 15-30 saniyelik video senaryosu. Her senaryo için 'Kanca (İlk 3sn)', 'Gövde' ve 'CTA' kısımlarını yaz).
                """
                
                user_prompt = f"Hedef CPA: {target_cpa} TL. Reklam Verileri: {metrics_json}"
                
                analiz_sonucu = ask_ai(openai_key, system_prompt, user_prompt)
                
                st.markdown("---")
                st.subheader("📋 Uzman Raporu")
                st.markdown(analiz_sonucu)
                
    else:
        st.warning("⚠️ Lütfen önce 'Performans Paneli' sekmesinde Meta verilerini başarıyla yükleyin.")
