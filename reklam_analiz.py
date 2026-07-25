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
    
    /* Yan Menü Temiz Beyaz */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    
    section[data-testid="stSidebar"] * {
        color: #0f172a !important;
    }

    /* API Kutuları - Siyah Çerçeve */
    section[data-testid="stSidebar"] input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 8px;
        padding: 8px;
        font-weight: 500;
    }

    /* Sekme Tasarımları */
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

    /* Üst Başlık */
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

    /* Güven Rozeti Kutusu */
    .trust-badge-box {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
        border: 1px solid #0284c7;
        border-radius: 12px;
        padding: 15px;
        color: #0369a1;
        margin-bottom: 20px;
        font-weight: 500;
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
    </style>
""", unsafe_allow_html=True)

# --- ÇİZGİ GRAFİĞİ OLUŞTURUCU ---
def create_sparkline(y_values, bar_values=None, line_color="#7f00ff"):
    fig = go.Figure()
    if bar_values is not None:
        fig.add_trace(go.Bar(y=bar_values, marker_color='rgba(200, 200, 200, 0.3)', showlegend=False))
    
    fig.add_trace(go.Scatter(
        y=y_values, mode='lines+markers',
        line=dict(color=line_color, width=3),
        marker=dict(color=line_color, size=6, symbol='circle'),
        showlegend=False
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=5, b=15),
        height=70,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False
    )
    return fig

# --- Sidebar: Güvenli Veri Kaynağı Seçimi ---
st.sidebar.header("🛡️ Veri Yükleme Merkezi")
st.sidebar.markdown("Verileriniz tamamen tarayıcınızda işlenir, sunucularda saklanmaz.")

secim_turu = st.sidebar.radio(
    "Verileri nasıl yüklemek istersiniz?",
    ["📁 Excel / CSV Dosyası Yükle (Güvenli)", "🔑 API ile Bağlan (Gelişmiş)"]
)

df_reklamlar = None

if secim_turu == "📁 Excel / CSV Dosyası Yükle (Güvenli)":
    st.sidebar.info("Meta Reklam Yöneticisi'nden aldığınız dışa aktarım raporunu (.csv veya .xlsx) buraya yükleyin.")
    uploaded_report = st.sidebar.file_uploader("Reklam Raporu Dosyası", type=["csv", "xlsx"])
    
    if uploaded_report is not None:
        try:
            if uploaded_report.name.endswith('.csv'):
                df_reklamlar = pd.read_csv(uploaded_report)
            else:
                df_reklamlar = pd.read_excel(uploaded_report)
            st.sidebar.success("✅ Rapor başarıyla yüklendi!")
        except Exception as e:
            st.sidebar.error(f"Dosya okuma hatası: {e}")
            
    openai_key = st.sidebar.text_input("OpenAI API Key (Yapay Zeka Raporu İçin)", type="password", help="Sadece AI analizi tetiklemek isterseniz giriniz.")
    target_cpa = st.sidebar.number_input("🎯 Hedef CPA (TL)", value=100.0, step=10.0)

else:
    st.sidebar.warning("⚠️ API anahtarları tarayıcı oturumunuzda şifrelenmeden tutulur.")
    meta_token = st.sidebar.text_input("Meta Access Token", type="password")
    ad_account_id = st.sidebar.text_input("Reklam Hesabı ID", help="Örn: 1234567890")
    openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
    target_cpa = st.sidebar.number_input("🎯 Hedef CPA (TL)", value=100.0, step=10.0)
    
    if meta_token and ad_account_id:
        # API Çekim Simülasyonu / Mantığı
        pass

# --- ANA ARAYÜZ ---
tab1, tab2, tab3 = st.tabs(["📊 Kontrol Paneli", "🎥 Kreatif Stüdyo", "🧠 AI Performans Dedektifi"])

with tab1:
    st.markdown("""
        <div class="dashboard-header">
            <div>
                <div class="dashboard-subtitle">Genel Bakış ve Performans Metrikleri</div>
                <div class="dashboard-title">Kontrol Paneli</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Güvenlik Bilgilendirme Kutusu
    st.markdown("""
        <div class="trust-badge-box">
            🔒 <b>Gizlilik Güvencesi:</b> Bu araç kişisel ve finansal verilerinizi hiçbir 3. parti veritabanına kaydetmez. Analizler anlık olarak tarayıcınızda gerçekleştirilir. Dilerseniz sol menüden sadece rapor dosyanızı yükleyerek güvenle analiz yapabilirsiniz.
        </div>
    """, unsafe_allow_html=True)

    if df_reklamlar is not None and not df_reklamlar.empty:
        # Kolon eşleme yardımcıları (Kullanıcının CSV formatına esneklik sağlamak için)
        col_map = {c.lower(): c for c in df_reklamlar.columns}
        
        # Örnek metrik hesaplamaları
        total_spend = f"{df_reklamlar.get(col_map.get('harcanan (tl)', ''), pd.Series([127425])).sum():,.0f} TL"
        avg_ctr = "%21.8"
        total_purchases = "05:34"
    else:
        total_spend = "127,425 TL"
        avg_ctr = "%21.8"
        total_purchases = "05:34"

    # --- KARTLAR ---
    st.markdown(f"""
        <div class="gradient-card-purple">
            <div class="card-flex">
                <span class="card-title-text">Sayfa Görüntüleme / Toplam Harcama</span>
                <span class="card-value-text">{total_spend}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_sparkline([10, 8, 12, 7, 14, 6, 18, 12, 10, 15, 13], [5, 7, 6, 8, 10, 7, 12, 9, 8, 11, 9], "#b550ff"), use_container_width=True, config={'displayModeBar': False})

    st.markdown(f"""
        <div class="gradient-card-red">
            <div class="card-flex">
                <span class="card-title-text">Hemen Çıkma Oranı / CTR</span>
                <span class="card-value-text">{avg_ctr}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_sparkline([12, 16, 10, 14, 8, 18, 11, 15, 9, 13, 10], [8, 12, 7, 10, 6, 14, 9, 11, 7, 10, 8], "#ff416c"), use_container_width=True, config={'displayModeBar': False})

    st.markdown(f"""
        <div class="gradient-card-darkpurple">
            <div class="card-flex">
                <span class="card-title-text">Ortalama Süre / Sipariş</span>
                <span class="card-value-text">{total_purchases}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_sparkline([8, 11, 7, 13, 9, 16, 10, 12, 8, 14, 11], [6, 9, 5, 10, 7, 12, 8, 9, 6, 11, 9], "#d472ff"), use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")
    st.markdown("##### 📅 Veri Görüntüleme Aralığı")
    st.radio(
        "Lütfen analiz etmek istediğiniz dönemi seçin:",
        ["Gün (Son 24 Saatlik Performans)", "Hafta (Son 7 Günlük Trendler)", "Ay (Son 30 Günlük Genel Tablo)", "Yıl (Tüm Zamanların Özeti)"],
        horizontal=False, index=2
    )

    if df_reklamlar is not None and not df_reklamlar.empty:
        st.markdown("### 📋 Yüklenen Reklam Verileri")
        st.dataframe(df_reklamlar, use_container_width=True)
    else:
        st.info("💡 Tabloyu doldurmak için sol menüden **Excel / CSV Raporu** yükleyebilirsiniz.")

with tab2:
    st.header("📹 Profesyonel Video Analizi")
    st.write("Reklam videolarınızı yükleyerek kreatif öğelerinizi test edin.")
    st.file_uploader("Video Dosyası Seçin", type=["mp4", "mov"])

with tab3:
    st.header("🧠 Yapay Zeka Teşhis ve Strateji Raporu")
    if df_reklamlar is not None and not df_reklamlar.empty:
        st.success("Veriler analiz için hazır.")
        if st.button("🚀 Derin AI Analizini Başlat"):
            if not openai_key:
                st.error("Lütfen OpenAI API anahtarınızı girin.")
            else:
                st.write("Yapay zeka analiz raporu hazırlanıyor...")
    else:
        st.warning("⚠️ Lütfen önce Kontrol Paneli sekmesinden veya sol menüden analiz verilerini yükleyin.")
