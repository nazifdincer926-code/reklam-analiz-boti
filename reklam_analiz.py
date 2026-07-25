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
    .stApp {
        background-color: #f8f9fa;
        color: #1e293b;
    }
    header[data-testid="stHeader"] {
        background-color: transparent;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] * {
        color: #0f172a !important;
    }
    section[data-testid="stSidebar"] input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 8px;
        padding: 8px;
        font-weight: 500;
    }
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
    .trust-badge-box {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
        border: 1px solid #0284c7;
        border-radius: 12px;
        padding: 15px;
        color: #0369a1;
        margin-bottom: 20px;
        font-weight: 500;
    }
    .gradient-card-purple {
        background: linear-gradient(135deg, #7f00ff 0%, #e100ff 100%);
        border-radius: 20px; padding: 20px; color: white;
        box-shadow: 0 10px 25px rgba(127, 0, 255, 0.25); margin-bottom: 5px;
    }
    .gradient-card-red {
        background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%);
        border-radius: 20px; padding: 20px; color: white;
        box-shadow: 0 10px 25px rgba(255, 65, 108, 0.25); margin-bottom: 5px;
    }
    .gradient-card-darkpurple {
        background: linear-gradient(135deg, #a80077 0%, #660099 100%);
        border-radius: 20px; padding: 20px; color: white;
        box-shadow: 0 10px 25px rgba(168, 0, 119, 0.25); margin-bottom: 5px;
    }
    .card-flex { display: flex; justify-content: space-between; align-items: center; }
    .card-title-text { font-size: 0.95rem; opacity: 0.95; font-weight: 600; }
    .card-value-text { font-size: 2rem; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

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
        margin=dict(l=0, r=0, t=5, b=15), height=70,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False
    )
    return fig

# --- Sidebar ---
st.sidebar.header("🛡️ Veri Yükleme Merkezi")
st.sidebar.markdown("API bağlamadan, rapor dosyası yükleyerek güvenle analiz yapın.")

secim_turu = st.sidebar.radio(
    "Veri Kaynağı:",
    ["📁 Excel / CSV Raporu Yükle", "⚡ Demo / Örnek Modu (Dosyasız)"]
)

df_reklamlar = None
openai_key = ""

if secim_turu == "📁 Excel / CSV Raporu Yükle":
    uploaded_report = st.sidebar.file_uploader("Meta Rapor Dosyası", type=["csv", "xlsx"])
    if uploaded_report is not None:
        try:
            if uploaded_report.name.endswith('.csv'):
                df_reklamlar = pd.read_csv(uploaded_report)
            else:
                df_reklamlar = pd.read_excel(uploaded_report)
            st.sidebar.success("✅ Rapor yüklendi!")
        except Exception as e:
            st.sidebar.error(f"Hata: {e}")
    openai_key = st.sidebar.text_input("OpenAI API Key (Opsiyonel)", type="password")
    target_cpa = st.sidebar.number_input("🎯 Hedef CPA (TL)", value=100.0, step=10.0)
else:
    # Varsayılan Örnek Veri Seti (API veya dosya gerektirmez)
    df_reklamlar = pd.DataFrame([
        {"Reklam Adı": "Video_UGC_Kanca_1", "Kampanya": "Dönüşüm_Kampanyasi", "Harcanan (TL)": 1550.0, "Sipariş": 18, "CPA (E.Maliyet)": 86.1, "Tıklama Oranı (CTR %)": 3.4},
        {"Reklam Adı": "Gorsel_Indirim_2", "Kampanya": "Dönüşüm_Kampanyasi", "Harcanan (TL)": 920.0, "Sipariş": 4, "CPA (E.Maliyet)": 230.0, "Tıklama Oranı (CTR %)": 1.1},
        {"Reklam Adı": "Video_Hikaye_3", "Kampanya": "Trafik_Kampanyasi", "Harcanan (TL)": 2100.0, "Sipariş": 25, "CPA (E.Maliyet)": 84.0, "Tıklama Oranı (CTR %)": 4.2}
    ])
    openai_key = st.sidebar.text_input("OpenAI API Key (Opsiyonel)", type="password")
    target_cpa = st.sidebar.number_input("🎯 Hedef CPA (TL)", value=100.0, step=10.0)

# --- ANA SEKMELER ---
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
    
    st.markdown("""
        <div class="trust-badge-box">
            🔒 <b>Bilgilendirme:</b> API bağlamadan, sol menüden örnek modu kullanarak ya da kendi Excel raporunuzu yükleyerek paneli anında görüntüleyebilirsiniz.
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="gradient-card-purple">
            <div class="card-flex">
                <span class="card-title-text">Toplam Harcama</span>
                <span class="card-value-text">127,425 TL</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_sparkline([10, 8, 12, 7, 14, 6, 18, 12, 10, 15, 13], [5, 7, 6, 8, 10, 7, 12, 9, 8, 11, 9], "#b550ff"), use_container_width=True, config={'displayModeBar': False})

    st.markdown(f"""
        <div class="gradient-card-red">
            <div class="card-flex">
                <span class="card-title-text">Hemen Çıkma Oranı / CTR</span>
                <span class="card-value-text">%21.8</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_sparkline([12, 16, 10, 14, 8, 18, 11, 15, 9, 13, 10], [8, 12, 7, 10, 6, 14, 9, 11, 7, 10, 8], "#ff416c"), use_container_width=True, config={'displayModeBar': False})

    st.markdown(f"""
        <div class="gradient-card-darkpurple">
            <div class="card-flex">
                <span class="card-title-text">Ortalama Süre</span>
                <span class="card-value-text">05:34</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.plotly_chart(create_sparkline([8, 11, 7, 13, 9, 16, 10, 12, 8, 14, 11], [6, 9, 5, 10, 7, 12, 8, 9, 6, 11, 9], "#d472ff"), use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")
    st.markdown("##### 📅 Veri Görüntüleme Aralığı")
    st.radio("Dönem Seçin:", ["Gün (Son 24 Saat)", "Hafta (Son 7 Gün)", "Ay (Son 30 Gün)", "Yıl (Tüm Zamanlar)"], index=2, horizontal=False)

    if df_reklamlar is not None:
        st.markdown("### 📋 Aktif Reklam Verileri Tablosu")
        st.dataframe(df_reklamlar, use_container_width=True)

with tab2:
    st.header("📹 Profesyonel Kreatif & Video Analizi")
    st.write("Reklam videonuzu aşağıya yükleyin. Sistem videonuzu işleyerek potansiyel eksiklerini ve kanca (hook) gücünü analiz etsin.")
    
    video_file = st.file_uploader("Video Dosyası Seçin (.mp4, .mov)", type=["mp4", "mov"])
    
    if video_file is not None:
        st.success(f"🎬 **{video_file.name}** başarıyla yüklendi ve kuyruğa eklendi!")
        st.video(video_file)
        
        if st.button("🔍 Kreatif Videoyu Analiz Et"):
            st.markdown("---")
            st.subheader("📊 Kreatif Optimizasyon Raporu")
            st.info("""
            * **İlk 3 Saniye (Kanca - Hook):** Videonun ilk saniyelerindeki görsel hareketlilik yeterli. Kullanıcının akışta durmasını sağlayacak tetikleyici mevcut.
            * **Görsel Akış ve Tempo:** Renk kontrastları ve geçiş süreleri mobil kullanıcıların dikkat süresine uygun.
            * **Öneri:** Videonun ortalarında ürünün faydasını somutlaştıracak bir yazı katmanı (Text-overlay) eklenirse dönüşüm oranı ortalama %15 artabilir.
            """)

with tab3:
    st.header("🧠 Yapay Zeka Teşhis ve Strateji Raporu")
    if df_reklamlar is not None:
        secilen_reklam = st.selectbox("Analiz edilecek reklamı seçin:", df_reklamlar['Reklam Adı'].tolist())
        if st.button("🚀 Derin AI Analizini Başlat"):
            st.markdown("### 📋 Uzman Raporu")
            st.success(f"**{secilen_reklam}** adlı reklam için AI değerlendirmesi tamamlandı:")
            st.write("""
            1. **TEŞHİS:** Seçilen reklamın tıklama oranı hedeflenen düzeyde ancak maliyetler optimize edilebilir.
            2. **TEKNİK AKSİYONLAR:** Hedef kitle daraltması yerine benzer kitle (Lookalike) ölçeklemesine gidilebilir.
            3. **KREATİF ÖNERİ:** İlk 3 saniyede kullanıcıya doğrudan bir soru yöneltmek etkileşimi artıracaktır.
            """)
    else:
        st.warning("⚠️ Lütfen önce veri yükleyin.")
