import streamlit as st
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="Pro Meta Reklam Analizörü", layout="wide", page_icon="📈")

# --- ARAYÜZ VE TEMA ÖZELLEŞTİRMELERİ ---
st.markdown("""
    <style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #f8f9fa;
        color: #1e293b;
    }
    
    header[data-testid="stHeader"] {
        background-color: transparent;
    }
    
    /* Yan Menü (Sidebar) Temiz Beyaz Tema */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Yan menü yazıları */
    section[data-testid="stSidebar"] * {
        color: #0f172a !important;
    }

    /* API Giriş Kutuları - Belirgin Siyah Çerçeve */
    section[data-testid="stSidebar"] input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important; /* Siyah köşeler/çerçeve */
        border-radius: 8px;
        padding: 8px;
        font-weight: 500;
    }
    
    /* Focus (Tıklanınca) Durumu */
    section[data-testid="stSidebar"] input:focus {
        border: 2px solid #ff416c !important;
        box-shadow: none !important;
    }

    /* Sekme (Tab) Tasarımları */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 12px;
        color: #64748b;
        padding: 8px 16px;
        font-weight: 600;
        border: 1px solid #e2e8f0;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff416c !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* Üst Başlık Stili */
    .dashboard-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    .dashboard-title {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0f172a;
    }
    .dashboard-subtitle {
        font-size: 0.9rem;
        color: #64748b;
        font-weight: 600;
    }

    /* Kart Tasarımları */
    .gradient-card-purple {
        background: linear-gradient(135deg, #7f00ff 0%, #e100ff 100%);
        border-radius: 20px;
        padding: 20px;
        color: white;
        box-shadow: 0 10px 25px rgba(127, 0, 255, 0.25);
        margin-bottom: 5px;
    }

    .gradient-card-red {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        border-radius: 20px;
        padding: 20px;
        color: white;
        box-shadow: 0 10px 25px rgba(255, 65, 108, 0.25);
        margin-bottom: 5px;
    }

    .gradient-card-darkpurple {
        background: linear-gradient(135deg, #a80077 0%, #660099 100%);
        border-radius: 20px;
        padding: 20px;
        color: white;
        box-shadow: 0 10px 25px rgba(168, 0, 119, 0.25);
        margin-bottom: 5px;
    }

    .card-flex {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .card-title-text {
        font-size: 0.95rem;
        opacity: 0.95;
        font-weight: 600;
    }

    .card-value-text {
        font-size: 2rem;
        font-weight: 800;
    }
    
    /* Genel Buton Tasarımlarını Temizle (Kırmızı dev butonları düzeltir) */
    .stButton>button {
        border-radius: 12px;
        font-weight: 600;
        border: 1px solid #cbd5e1;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# --- İNTERAKTİF ÇİZGİ GRAFİĞİ OLUŞTURUCU (Şeffaf Arka Plan + Canlı Çizgiler) ---
def create_sparkline(y_values, bar_values=None, line_color="#7f00ff"):
    fig = go.Figure()
    
    # Arka plan sütunları (daha hafif)
    if bar_values is not None:
        fig.add_trace(go.Bar(
            y=bar_values,
            marker_color=f'rgba(200, 200, 200, 0.3)', 
            showlegend=False
        ))
        
    # Canlı renkli düğümlü çizgi
    fig.add_trace(go.Scatter(
        y=y_values,
        mode='lines+markers',
        line=dict(color=line_color, width=3),
        marker=dict(color=line_color, size=6, symbol='circle'),
        showlegend=False
    ))
    
    # Tamamen şeffaf arka plan
    fig.update_layout(
        margin=dict(l=0, r=0, t=5, b=15),
        height=70,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False
    )
    return fig

# --- Sidebar - API Kurulumları ---
st.sidebar.header("🔑 Güvenli API Bağlantıları")
st.sidebar.markdown("Lütfen erişim bilgilerinizi aşağıdaki alanlara giriniz.")

meta_token = st.sidebar.text_input("1. Meta System User Access Token", type="password", help="Business Manager'dan alınan kalıcı token.")
ad_account_id = st.sidebar.text_input("2. Reklam Hesabı ID", help="Sadece rakamlar. Örn: 1234567890")
openai_key = st.sidebar.text_input("3. OpenAI API Key", type="password", help="Yapay zeka analizleri için API anahtarınız.")

st.sidebar.markdown("---")
target_cpa = st.sidebar.number_input("🎯 Hedef Müşteri Edinme Maliyeti (CPA) TL", value=100.0, step=10.0)

# --- FONKSİYONLAR ---

def fetch_meta_data(token, account_id):
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

tab1, tab2, tab3 = st.tabs(["📊 Kontrol Paneli", "🎥 Kreatif Stüdyo", "🧠 AI Performans Dedektifi"])

df_reklamlar = None

with tab1:
    st.markdown("""
        <div class="dashboard-header">
            <div>
                <div class="dashboard-subtitle">Genel Bakış</div>
                <div class="dashboard-title">Kontrol Paneli</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if meta_token and ad_account_id:
        df_reklamlar = fetch_meta_data(meta_token, ad_account_id)

    if df_reklamlar is not None and not df_reklamlar.empty:
        total_spend = f"{df_reklamlar['Harcanan (TL)'].sum():,.0f} TL"
        avg_ctr = f"%{df_reklamlar['Tıklama Oranı (CTR %)'].mean():.1f}"
        total_purchases = f"{df_reklamlar['Sipariş'].sum()} Sipariş"
    else:
        total_spend = "127,425 TL"
        avg_ctr = "%21.8"
        total_purchases = "05:34"

    # --- KART 1: Sayfa Görüntüleme ---
    st.markdown(f"""
        <div class="gradient-card-purple">
            <div class="card-flex">
                <span class="card-title-text">Sayfa Görüntüleme</span>
                <span class="card-value-text">{total_spend}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # Şeffaf arka plan, mor karta uygun eflatun çizgi rengi (#b550ff)
    st.plotly_chart(create_sparkline([10, 8, 12, 7, 14, 6, 18, 12, 10, 15, 13], [5, 7, 6, 8, 10, 7, 12, 9, 8, 11, 9], "#b550ff"), use_container_width=True, config={'displayModeBar': False})

    # --- KART 2: Hemen Çıkma Oranı ---
    st.markdown(f"""
        <div class="gradient-card-red">
            <div class="card-flex">
                <span class="card-title-text">Hemen Çıkma Oranı</span>
                <span class="card-value-text">{avg_ctr}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # Şeffaf arka plan, kırmızı karta uygun canlı kırmızı/pembe çizgi (#ff416c)
    st.plotly_chart(create_sparkline([12, 16, 10, 14, 8, 18, 11, 15, 9, 13, 10], [8, 12, 7, 10, 6, 14, 9, 11, 7, 10, 8], "#ff416c"), use_container_width=True, config={'displayModeBar': False})

    # --- KART 3: Ortalama Süre ---
    st.markdown(f"""
        <div class="gradient-card-darkpurple">
            <div class="card-flex">
                <span class="card-title-text">Ortalama Süre</span>
                <span class="card-value-text">{total_purchases}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    # Şeffaf arka plan, koyu mor karta uygun lila çizgi (#d472ff)
    st.plotly_chart(create_sparkline([8, 11, 7, 13, 9, 16, 10, 12, 8, 14, 11], [6, 9, 5, 10, 7, 12, 8, 9, 6, 11, 9], "#d472ff"), use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")
    
    # YENİ ZAMAN FİLTRESİ (Kurumsal ve Göz Yormayan Tasarım)
    st.markdown("##### 📅 Veri Görüntüleme Aralığı")
    zaman_araligi = st.radio(
        "Lütfen analiz etmek istediğiniz dönemi seçin:",
        options=[
            "Gün (Son 24 Saatlik Performans)", 
            "Hafta (Son 7 Günlük Trendler)", 
            "Ay (Son 30 Günlük Genel Tablo)", 
            "Yıl (Tüm Zamanların Özeti)"
        ],
        horizontal=False,
        index=2 # Varsayılan olarak "Ay" seçili gelsin
    )

    if df_reklamlar is not None and not df_reklamlar.empty:
        st.markdown(f"### 📋 Canlı Reklam Tablosu")
        def style_cpa(row):
            if row['Sipariş'] == 0 and row['Harcanan (TL)'] > 50:
                return ['background-color: #ffe6e6; color: #990000'] * len(row)
            elif row['CPA (E.Maliyet)'] > target_cpa and row['Sipariş'] > 0:
                return ['background-color: #fff3e0; color: #b78103'] * len(row)
            elif row['CPA (E.Maliyet)'] <= target_cpa and row['Sipariş'] > 0:
                return ['background-color: #e6f4ea; color: #137333'] * len(row)
            else:
                return [''] * len(row)

        st.dataframe(df_reklamlar.style.apply(style_cpa, axis=1), use_container_width=True)

with tab2:
    st.header("📹 Profesyonel Video Analizi")
    st.write("Video yükleme ve yerel OpenCV analizi buraya gelecek.")
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

        # Yapay Zeka Butonu için özel stil uyguluyoruz
        st.markdown("""
            <style>
            .ai-button button {
                background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%) !important;
                color: white !important;
                border: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="ai-button">', unsafe_allow_html=True)
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
        st.markdown('</div>', unsafe_allow_html=True)
                
    else:
        st.warning("⚠️ Lütfen önce 'Kontrol Paneli' sekmesinde Meta verilerini yükleyin.")
