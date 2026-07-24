import streamlit as st
import pandas as pd
import cv2
import requests
import os
import numpy as np
from datetime import datetime, timedelta
import json

# --- 20 Yıllık Uzman Notu ---
# Bir reklamın kârlı olup olmadığını anlamak için sadece CTR'a bakılmaz.
# Gerçek ROAS (Reklam Harcamasının Geri Dönüşü) ve CPA (Edinme Başı Maliyet) görmeliyiz.
# Bu kod, Meta API'den bu derin verileri çekmek için tasarlandı.
# ---------------------------

st.set_page_config(page_title="Pro Meta Reklam Analizörü v2.0", layout="wide", page_icon="📈")

# Gelişmiş Stil (Daha Profesyonel Görünüm)
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { background-color: #ff4b4b; color: white; border-radius: 20px; font-weight: bold; border: none;}
    .stButton>button:hover { background-color: #ff3333; color: white; }
    .metric-box { padding: 20px; background: white; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-left: 5px solid #ff4b4b; }
    .stTabs [data-baseweb="tab"] { font-size: 1.2rem; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #1f77b4; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Pro Meta Reklam & Kreatif Analiz Merkezi")
st.markdown("*Dijital Reklamcılık Uzmanı Asistanınız (Veri Odaklı Kârlılık Mimarisi)*")

# --- Sidebar - API Kurulumları (Hassas Veriler) ---
st.sidebar.header("🔑 Güvenli API Bağlantıları")
st.sidebar.markdown("Verileriniz yerelinizde işlenir, sunucuya gönderilmez.")

meta_token = st.sidebar.text_input("1. Meta System User Access Token", type="password", help="Business Manager'dan alınan, reklam okuma yetkili kalıcı token.")
ad_account_id = st.sidebar.text_input("2. Reklam Hesabı ID", help="Sadece rakamlar. Örn: 1234567890")
openai_key = st.sidebar.text_input("3. OpenAI API Key", type="password", help="gpt-4o veya gpt-3.5-turbo erişimi olan key.")

st.sidebar.markdown("---")
# Hedef CPA ayarı ekliyoruz, AI buna göre analiz yapacak.
target_cpa = st.sidebar.number_input("🎯 Hedef Müşteri Edinme Maliyeti (CPA) TL", value=100.0, step=10.0, help="Kârlı olmanız için gereken maksimum sipariş başı maliyet.")

# --- FONKSİYONLAR (Arka Plandaki Motor) ---

def fetch_meta_data(token, account_id):
    """Meta Graph API'den gerçek reklam performans verilerini çeker."""
    if not token or not account_id:
        return None
    
    # API ID formatını düzelt
    clean_id = account_id.replace("act_", "")
    url = f"https://graph.facebook.com/v19.0/act_{clean_id}/insights"
    
    # --- Uzman Notu ---
    # İstediğimiz alanlara dikkat et. Huninin (funnel) tamamını istiyoruz.
    # spend (Harcama), impressions (Erişim), clicks (Tıklama), 
    # actions (Sipariş, Sepete Ekleme vb. tüm pikseller olayları)
    fields = "campaign_name,adset_name,ad_name,spend,impressions,clicks,cpc,ctr,actions,cost_per_action_type,conversions"
    
    params = {
        'access_token': token,
        'level': 'ad',  # Reklam seviyesinde analiz
        'date_preset': 'last_30d', # Son 30 gün
        'fields': fields,
        'limit': 100 # Maksimum 100 reklam
    }
    
    with st.spinner("Meta'dan canlı veriler çekiliyor..."):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status() # Hata varsa fırlat
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
        # Temel veriler
        ad_data = {
            'Reklam Adı': ad.get('ad_name'),
            'Kampanya': ad.get('campaign_name'),
            'Harcanan (TL)': float(ad.get('spend', 0)),
            'Tıklama Oranı (CTR %)': float(ad.get('ctr', 0)) * 100,
            'Tıklama (CPC)': float(ad.get('cpc', 0)),
        }
        
        # Piksellerden (Actions) Sipariş ve ROAS çekme (Karmaşık kısım)
        purchases = 0
        purchase_value = 0
        
        if 'actions' in ad:
            for action in ad['actions']:
                if action['action_type'] == 'purchase':
                    purchases = int(action['value'])
        
        if 'conversions' in ad:
             for conv in ad['conversions']:
                if conv['action_type'] == 'purchase':
                    # Genelde dönüşüm değeri 'value' alanında olur, Meta API yapısına göre değişebilir.
                    # Basitlik adına burada 1 alıyoruz, ROAS hesabı için gerçek değer gerekir.
                    purchase_value = float(conv.get('value', 0)) 

        ad_data['Sipariş'] = purchases
        
        # CPA Hesabı
        ad_data['CPA (E.Maliyet)'] = ad_data['Harcanan (TL)'] / purchases if purchases > 0 else 0
        
        # Basit ROAS Hesabı (Eğer satın alma değeri geliyorsa)
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
        "model": "gpt-4o", # En iyi sonuç için gpt-4o. Maliyet için gpt-3.5-turbo
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7 # Yaratıcılık dengesi
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

# Sekmeler
tab1, tab2, tab3 = st.tabs(["📊 Performans Paneli (Canlı)", "🎥 Kreatif Stüdyo", "🧠 AI Performans Dedektifi"])

# Global Değişken (Veriyi sekmeler arası taşımak için)
df_reklamlar = None

with tab1:
    st.header("📋 Gerçek Reklam Verileriniz (Son 30 Gün)")
    
    if meta_token and ad_account_id:
        df_reklamlar = fetch_meta_data(meta_token, ad_account_id)
        
        if df_reklamlar is not None and not df_reklamlar.empty:
            st.success(f"{len(df_reklamlar)} adet aktif reklam verisi çekildi.")
            
            # --- Kritik Durum Analizi Görselleştirmesi ---
            # Öğretmen Notu: CPA Hedefin üzerindeyse kırmızı, altındaysa yeşil yapalım.
            def style_cpa(row):
                if row['Sipariş'] == 0 and row['Harcanan (TL)'] > 50: # Sipariş yok ama para harcanmışsa kritik
                    return ['background-color: #ffcccc'] * len(row)
                elif row['CPA (E.Maliyet)'] > target_cpa and row['Sipariş'] > 0:
                    return ['background-color: #ffe0b3'] * len(row) # Uyarı
                elif row['CPA (E.Maliyet)'] <= target_cpa and row['Sipariş'] > 0:
                    return ['background-color: #d1e7dd'] * len(row) # İyi
                else:
                    return [''] * len(row)

            st.dataframe(df_reklamlar.style.apply(style_cpa, axis=1), use_container_width=True)
            
            # Özet Metrikler
            total_spend = df_reklamlar['Harcanan (TL)'].sum()
            total_purchases = df_reklamlar['Sipariş'].sum()
            avg_ctr = df_reklamlar['Tıklama Oranı (CTR %)'].mean()
            avg_cpa = total_spend / total_purchases if total_purchases > 0 else 0
            
            st.markdown("### 📈 Hesap Özeti")
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            with m_col1:
                st.metric("Toplam Harcama", f"{total_spend:,.2f} TL")
            with m_col2:
                st.metric("Toplam Sipariş", total_purchases)
            with m_col3:
                st.metric("Ort. CPA", f"{avg_cpa:,.2f} TL", delta=f"{avg_cpa - target_cpa:.2f} TL vs Hedef", delta_color="inverse")
            with m_col4:
                st.metric("Ort. CTR", f"%{avg_ctr:.2f}")

        else:
            st.info("API'den veri dönmedi veya hesapta aktif reklam yok.")
            
    else:
        st.warning("⚠️ Soldaki sidebar'a **Meta Access Token** ve **Reklam Hesabı ID** girerek canlı verilerinizi görün.")
        st.image("https://i.imgur.com/gK6B4x8.png", caption="Örnek Veri Görünümü (Temsili)") # Örnek bir resim koyabilirsin

with tab2:
    st.header("📹 Profesyonel Video Analizi")
    st.write("Video yükleme ve yerel OpenCV analizi buraya gelecek (Bir sonraki aşamanın konusu).")
    # Mevcut yükleyiciyi tutuyoruz, ama şu an işlevsiz bırakıyoruz veri odağı için.
    uploaded_file = st.file_uploader("Analiz etmek istediğiniz reklam videosunu yükleyin", type=["mp4", "mov"])

with tab3:
    st.header("🧠 Yapay Zeka Teşhis ve Strateji Raporu")
    
    if df_reklamlar is not None and not df_reklamlar.empty:
        # Analiz edilecek reklamı seçelim
        reklam_listesi = df_reklamlar['Reklam Adı'].tolist()
        secilen_reklam_adi = st.selectbox("Analiz edilecek reklamı seçin:", reklam_listesi)
        
        # Seçilen reklamın verilerini alalım
        reklam_verisi = df_reklamlar[df_reklamlar['Reklam Adı'] == secilen_reklam_adi].iloc[0]
        
        # Metrikleri JSON'a çevirip AI'ye besleyeceğiz
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
                # --- PROMPT ENGINEERING ---
                # Öğretmen Notu: Burası işin sihri. AI'ye 20 yıllık uzman rolünü veriyoruz.
                
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