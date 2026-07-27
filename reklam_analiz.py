import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import tempfile
import os
import plotly.graph_objects as go
import cv2

# ============================================================
# SAYFA YAPILANDIRMASI
# ============================================================
st.set_page_config(page_title="Pro Meta Reklam Analizörü", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1e293b; }
    header[data-testid="stHeader"] { background-color: transparent; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    section[data-testid="stSidebar"] * { color: #0f172a !important; }
    section[data-testid="stSidebar"] input {
        background-color: #ffffff !important; color: #000000 !important;
        border: 2px solid #000000 !important; border-radius: 8px; padding: 8px; font-weight: 500;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: transparent; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff; border-radius: 12px; color: #64748b;
        padding: 8px 16px; font-weight: 600; border: 1px solid #e2e8f0;
    }
    .stTabs [aria-selected="true"] { background-color: #ff416c !important; color: #ffffff !important; border: none !important; }
    .dashboard-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
    .dashboard-title { font-size: 1.8rem; font-weight: 800; color: #0f172a; }
    .dashboard-subtitle { font-size: 0.9rem; color: #64748b; font-weight: 600; }
    .trust-badge-box {
        background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); border: 1px solid #0284c7;
        border-radius: 12px; padding: 15px; color: #0369a1; margin-bottom: 20px; font-weight: 500;
    }
    .gradient-card-purple { background: linear-gradient(135deg, #7f00ff 0%, #e100ff 100%); border-radius: 20px; padding: 20px; color: white; box-shadow: 0 10px 25px rgba(127,0,255,0.25); margin-bottom: 5px; }
    .gradient-card-red { background: linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%); border-radius: 20px; padding: 20px; color: white; box-shadow: 0 10px 25px rgba(255,65,108,0.25); margin-bottom: 5px; }
    .gradient-card-darkpurple { background: linear-gradient(135deg, #a80077 0%, #660099 100%); border-radius: 20px; padding: 20px; color: white; box-shadow: 0 10px 25px rgba(168,0,119,0.25); margin-bottom: 5px; }
    .gradient-card-green { background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%); border-radius: 20px; padding: 20px; color: white; box-shadow: 0 10px 25px rgba(13,148,136,0.25); margin-bottom: 5px; }
    .card-flex { display: flex; justify-content: space-between; align-items: center; }
    .card-title-text { font-size: 0.95rem; opacity: 0.95; font-weight: 600; }
    .card-value-text { font-size: 2rem; font-weight: 800; }
    .diag-card { border-radius: 14px; padding: 16px; margin-bottom: 12px; border-left: 6px solid; }
    .diag-critical { background: #fef2f2; border-color: #dc2626; }
    .diag-warning { background: #fffbeb; border-color: #d97706; }
    .diag-good { background: #f0fdf4; border-color: #16a34a; }
    </style>
""", unsafe_allow_html=True)


# ============================================================
# 1) KOLON EŞLEME VE METRİK MOTORU
# ============================================================
COLUMN_KEYWORDS = {
    "spend": ["harcanan", "amount spent", "spend", "harcama"],
    "impressions": ["gösterim", "impressions"],
    "clicks": ["tıklama", "link click", "clicks (all)", "clicks"],
    "purchases": ["satın alma", "purchases", "sipariş", "results", "sonuç"],
    "revenue": ["dönüşüm değeri", "purchase value", "conversion value", "revenue", "gelir"],
    "reach": ["erişim", "reach"],
    "frequency": ["sıklık", "frequency"],
    "ad_name": ["reklam adı", "ad name", "ad set name", "kampanya adı", "campaign name"],
}


def find_column(df, keywords):
    """Sütun isimlerini anahtar kelimelerle eşleştirir (Türkçe/İngilizce Meta export formatlarına uyum sağlar)."""
    for col in df.columns:
        col_lower = str(col).lower().strip()
        for kw in keywords:
            if kw in col_lower:
                return col
    return None


def map_columns(df):
    mapping = {}
    for field, keywords in COLUMN_KEYWORDS.items():
        mapping[field] = find_column(df, keywords)
    return mapping


def to_numeric_safe(series):
    if series is None:
        return None
    return pd.to_numeric(
        series.astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False).str.replace("%", "", regex=False),
        errors="coerce"
    ) if series.dtype == object else pd.to_numeric(series, errors="coerce")


def compute_metrics(df, mapping):
    """Gerçek metrikleri (CTR, CPC, CPM, CPA, ROAS, dönüşüm oranı) hesaplayıp DataFrame'e ekler."""
    out = df.copy()

    spend = to_numeric_safe(out[mapping["spend"]]) if mapping["spend"] else pd.Series(np.nan, index=out.index)
    impressions = to_numeric_safe(out[mapping["impressions"]]) if mapping["impressions"] else pd.Series(np.nan, index=out.index)
    clicks = to_numeric_safe(out[mapping["clicks"]]) if mapping["clicks"] else pd.Series(np.nan, index=out.index)
    purchases = to_numeric_safe(out[mapping["purchases"]]) if mapping["purchases"] else pd.Series(np.nan, index=out.index)
    revenue = to_numeric_safe(out[mapping["revenue"]]) if mapping["revenue"] else pd.Series(np.nan, index=out.index)
    reach = to_numeric_safe(out[mapping["reach"]]) if mapping["reach"] else pd.Series(np.nan, index=out.index)
    frequency = to_numeric_safe(out[mapping["frequency"]]) if mapping["frequency"] else pd.Series(np.nan, index=out.index)

    out["_spend"] = spend
    out["_impressions"] = impressions
    out["_clicks"] = clicks
    out["_purchases"] = purchases
    out["_revenue"] = revenue
    out["_reach"] = reach
    out["_frequency"] = frequency

    out["CTR (%)"] = (clicks / impressions * 100).replace([np.inf, -np.inf], np.nan)
    out["CPC (TL)"] = (spend / clicks).replace([np.inf, -np.inf], np.nan)
    out["CPM (TL)"] = (spend / impressions * 1000).replace([np.inf, -np.inf], np.nan)
    out["CPA (TL)"] = (spend / purchases).replace([np.inf, -np.inf], np.nan)
    out["ROAS"] = (revenue / spend).replace([np.inf, -np.inf], np.nan)
    out["Dönüşüm Oranı (%)"] = (purchases / clicks * 100).replace([np.inf, -np.inf], np.nan)

    return out


def summarize(df):
    """Genel özet metrikleri döndürür (kartlarda ve AI raporunda kullanılır)."""
    total_spend = df["_spend"].sum(skipna=True)
    total_impr = df["_impressions"].sum(skipna=True)
    total_clicks = df["_clicks"].sum(skipna=True)
    total_purchases = df["_purchases"].sum(skipna=True)
    total_revenue = df["_revenue"].sum(skipna=True)

    ctr = (total_clicks / total_impr * 100) if total_impr else np.nan
    cpa = (total_spend / total_purchases) if total_purchases else np.nan
    roas = (total_revenue / total_spend) if total_spend else np.nan
    conv_rate = (total_purchases / total_clicks * 100) if total_clicks else np.nan
    avg_freq = df["_frequency"].mean(skipna=True)
    cpm = (total_spend / total_impr * 1000) if total_impr else np.nan

    return {
        "total_spend": total_spend, "total_impr": total_impr, "total_clicks": total_clicks,
        "total_purchases": total_purchases, "total_revenue": total_revenue,
        "ctr": ctr, "cpa": cpa, "roas": roas, "conv_rate": conv_rate,
        "avg_freq": avg_freq, "cpm": cpm,
    }


# ============================================================
# 2) TEŞHİS MOTORU (kural tabanlı — "neden kötü gidiyor?")
# ============================================================
def diagnose(summary, target_cpa):
    """Genel performansa göre kural tabanlı teşhisler üretir. Her teşhis; başlık, seviye ve öneri içerir."""
    findings = []

    ctr = summary["ctr"]
    cpa = summary["cpa"]
    roas = summary["roas"]
    conv_rate = summary["conv_rate"]
    freq = summary["avg_freq"]
    cpm = summary["cpm"]

    # CTR değerlendirmesi
    if pd.notna(ctr):
        if ctr < 1.0:
            findings.append({
                "level": "critical", "title": "Düşük CTR — Reklam ilgi çekmiyor",
                "detail": f"CTR %{ctr:.2f} seviyesinde, bu Meta ortalamasının (genelde %1-2) altında.",
                "recommendation": "Kreatif (görsel/video) ve başlık metnini değiştir. İlk 3 saniyede dikkat çekmeyen videolar düşük CTR'a yol açar. Hedef kitle çok geniş olabilir, daralt."
            })
        elif ctr > 3.0:
            findings.append({
                "level": "good", "title": "Güçlü CTR",
                "detail": f"CTR %{ctr:.2f} — reklam hedef kitlenin dikkatini iyi çekiyor.",
                "recommendation": "Bu kreatifi farklı varyasyonlarla çoğaltarak (creative testing) ölçekle."
            })

    # Frequency (reklam yorgunluğu)
    if pd.notna(freq):
        if freq > 4:
            findings.append({
                "level": "critical", "title": "Reklam Yorgunluğu (Ad Fatigue)",
                "detail": f"Ortalama sıklık (frequency) {freq:.1f} — aynı kişi reklamı çok fazla kez görmüş.",
                "recommendation": "Kitleyi genişlet, yeni kreatif ekle veya frequency cap uygula. Yüksek frequency CTR'ı düşürüp CPM'i artırır."
            })

    # CPM değerlendirmesi
    if pd.notna(cpm) and pd.notna(ctr):
        if cpm > 150 and ctr < 1.5:
            findings.append({
                "level": "warning", "title": "Yüksek CPM + Düşük CTR kombinasyonu",
                "detail": f"CPM {cpm:.0f} TL, CTR %{ctr:.2f} — hem gösterim maliyeti yüksek hem de ilgi düşük.",
                "recommendation": "Hedef kitle/yerleşim (placement) rekabetçi olabilir. Otomatik yerleşimleri dene, kitleyi daralt veya kreatifi yenile."
            })

    # Dönüşüm oranı (tıklayan ama satın almayan)
    if pd.notna(conv_rate) and pd.notna(ctr):
        if ctr > 1.5 and conv_rate < 1.0:
            findings.append({
                "level": "critical", "title": "Trafik var, satış yok — Landing Page / Teklif Sorunu",
                "detail": f"CTR %{ctr:.2f} iyi ama dönüşüm oranı sadece %{conv_rate:.2f}.",
                "recommendation": "Sorun kreatifte değil: açılış sayfası hızı, fiyat/teklif netliği, ödeme adımları ve mobil uyum kontrol edilmeli. Checkout'ta terk oranına bak."
            })

    # CPA / hedef karşılaştırma
    if pd.notna(cpa) and target_cpa:
        if cpa > target_cpa * 1.2:
            findings.append({
                "level": "critical", "title": "CPA hedefin üstünde",
                "detail": f"Gerçek CPA {cpa:.0f} TL, hedef {target_cpa:.0f} TL (%{((cpa/target_cpa)-1)*100:.0f} fazla).",
                "recommendation": "Bütçeyi en verimli reklam setine kaydır, düşük performanslı setleri durdur, teklif stratejisini gözden geçir (cost cap dene)."
            })
        elif cpa <= target_cpa:
            findings.append({
                "level": "good", "title": "CPA hedefin altında — kârlı çalışıyor",
                "detail": f"Gerçek CPA {cpa:.0f} TL, hedef {target_cpa:.0f} TL.",
                "recommendation": "Bütçeyi kademeli olarak artırarak (günde max %20) ölçeklendirmeyi dene."
            })

    # ROAS
    if pd.notna(roas):
        if roas < 1:
            findings.append({
                "level": "critical", "title": "ROAS 1'in altında — zarar ediliyor",
                "detail": f"Her 1 TL harcamaya karşılık {roas:.2f} TL gelir elde ediliyor.",
                "recommendation": "Ürün fiyatı/marj, hedef kitle uyumu ve teklif kalitesi acilen gözden geçirilmeli."
            })
        elif roas >= 3:
            findings.append({
                "level": "good", "title": "Yüksek ROAS",
                "detail": f"ROAS {roas:.2f} — reklam yatırımı güçlü getiri sağlıyor.",
                "recommendation": "Bu kampanyaya bütçe aktarımı yapılabilir."
            })

    if not findings:
        findings.append({
            "level": "warning", "title": "Yeterli veri yok",
            "detail": "Teşhis üretmek için CSV/Excel dosyanızda harcama, gösterim, tıklama ve satın alma sütunları gerekli.",
            "recommendation": "Meta Reklam Yöneticisi'nden dışa aktarırken bu sütunların dahil olduğundan emin olun."
        })

    return findings


# ============================================================
# 3) META GRAPH API — GERÇEK VERİ ÇEKME
# ============================================================
def fetch_meta_insights(token, account_id, date_preset="last_30d"):
    """Meta Graph API üzerinden gerçek reklam performans verisini çeker."""
    acc = account_id if str(account_id).startswith("act_") else f"act_{account_id}"
    url = f"https://graph.facebook.com/v19.0/{acc}/insights"
    fields = ",".join([
        "ad_name", "spend", "impressions", "clicks", "reach", "frequency",
        "actions", "action_values"
    ])
    params = {
        "fields": fields,
        "date_preset": date_preset,
        "level": "ad",
        "access_token": token,
        "limit": 200,
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"Meta API hatası ({resp.status_code}): {resp.text[:300]}")

    data = resp.json().get("data", [])
    if not data:
        return pd.DataFrame()

    rows = []
    for item in data:
        purchases = 0
        revenue = 0
        for a in item.get("actions", []):
            if a.get("action_type") in ("purchase", "omni_purchase"):
                purchases += float(a.get("value", 0))
        for av in item.get("action_values", []):
            if av.get("action_type") in ("purchase", "omni_purchase"):
                revenue += float(av.get("value", 0))

        rows.append({
            "Reklam Adı": item.get("ad_name", ""),
            "Harcanan (TL)": float(item.get("spend", 0)),
            "Gösterimler": int(item.get("impressions", 0)),
            "Tıklamalar": int(item.get("clicks", 0)),
            "Erişim": int(item.get("reach", 0)),
            "Sıklık": float(item.get("frequency", 0)),
            "Satın Almalar": purchases,
            "Dönüşüm Değeri": revenue,
        })

    return pd.DataFrame(rows)


# ============================================================
# 4) VİDEO / KREATİF ANALİZİ (OpenCV)
# ============================================================
def analyze_video(file_path):
    """Videodan teknik kreatif istatistikleri çıkarır: süre, çözünürlük, ortalama parlaklık,
    hareket yoğunluğu ve sahne değişim sayısı."""
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        raise Exception("Video dosyası açılamadı.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps else 0

    sample_step = max(1, int(fps // 2))  # saniyede ~2 kare örnekle
    prev_gray = None
    brightness_vals = []
    motion_vals = []
    scene_changes = 0
    first_3s_motion = []

    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % sample_step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness_vals.append(float(np.mean(gray)))
            if prev_gray is not None:
                diff = cv2.absdiff(gray, prev_gray)
                motion_score = float(np.mean(diff))
                motion_vals.append(motion_score)
                if idx / fps <= 3:
                    first_3s_motion.append(motion_score)
                if motion_score > 40:  # eşik: büyük sahne değişimi
                    scene_changes += 1
            prev_gray = gray
        idx += 1

    cap.release()

    return {
        "duration_sec": round(duration, 1),
        "resolution": f"{width}x{height}",
        "fps": round(fps, 1),
        "avg_brightness": round(float(np.mean(brightness_vals)), 1) if brightness_vals else None,
        "avg_motion": round(float(np.mean(motion_vals)), 1) if motion_vals else None,
        "scene_changes": scene_changes,
        "first_3s_motion": round(float(np.mean(first_3s_motion)), 1) if first_3s_motion else None,
        "is_vertical": height > width,
    }


# ============================================================
# 5) OPENAI İLE AI STRATEJİ VE VİDEO FİKRİ ÜRETİMİ
# ============================================================
def call_openai(api_key, system_prompt, user_prompt, model="gpt-4o-mini", max_tokens=1200):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise Exception(f"OpenAI API hatası ({resp.status_code}): {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def generate_ai_strategy(api_key, summary, findings, target_cpa, product_info=""):
    system_prompt = (
        "Sen 15 yıllık deneyimli bir performans pazarlama (Meta Ads) uzmanısın. "
        "Sana verilen gerçek kampanya verilerine dayanarak, net, uygulanabilir ve maddeler halinde "
        "bir strateji raporu hazırlıyorsun. Genel geçer tavsiyeler değil, verideki rakamlara özel "
        "somut aksiyonlar öneriyorsun. Türkçe yanıt ver."
    )
    user_prompt = f"""
Kampanya Özeti:
- Toplam Harcama: {summary['total_spend']:.0f} TL
- Toplam Gösterim: {summary['total_impr']:.0f}
- Toplam Tıklama: {summary['total_clicks']:.0f}
- Toplam Satın Alma: {summary['total_purchases']:.0f}
- Toplam Gelir: {summary['total_revenue']:.0f} TL
- CTR: %{summary['ctr']:.2f}
- CPM: {summary['cpm']:.0f} TL
- CPA: {summary['cpa']:.0f} TL (Hedef: {target_cpa:.0f} TL)
- ROAS: {summary['roas']:.2f}
- Dönüşüm Oranı: %{summary['conv_rate']:.2f}
- Ortalama Frequency: {summary['avg_freq']:.2f}

Kural Tabanlı Teşhisler:
{json.dumps(findings, ensure_ascii=False, indent=2)}

Ürün/İşletme bilgisi (varsa): {product_info or "Belirtilmedi"}

Lütfen şu 3 başlıkta yanıt ver:
1) NEDEN BÖYLE GİDİYOR — kök neden analizi
2) SİPARİŞLERİ ARTIRMAK İÇİN STRATEJİ — bu hafta uygulanabilecek somut adımlar (bütçe, hedefleme, teklif, kreatif)
3) 30 GÜNLÜK YOL HARİTASI — haftalık aksiyon planı
"""
    return call_openai(api_key, system_prompt, user_prompt)


def generate_video_ideas(api_key, video_stats, product_info=""):
    system_prompt = (
        "Sen 15 yıllık deneyimli bir reklam kreatif direktörüsün, Meta/Instagram/TikTok reklam videoları "
        "konusunda uzmansın. Sana verilen teknik video analizine bakarak videonun güçlü/zayıf yönlerini "
        "belirtiyor ve somut, çekilebilir 3 yeni video fikri öneriyorsun (sahne sahne açıklamalı). Türkçe yanıt ver."
    )
    user_prompt = f"""
Video Teknik Analizi:
- Süre: {video_stats['duration_sec']} saniye
- Çözünürlük: {video_stats['resolution']} ({'Dikey - mobil uyumlu' if video_stats['is_vertical'] else 'Yatay - mobil için ideal değil'})
- Ortalama Parlaklık: {video_stats['avg_brightness']}
- Ortalama Hareket Skoru: {video_stats['avg_motion']}
- İlk 3 Saniye Hareket Skoru: {video_stats['first_3s_motion']}
- Sahne Değişim Sayısı: {video_stats['scene_changes']}

Ürün/İşletme bilgisi (varsa): {product_info or "Belirtilmedi"}

Lütfen şunları yap:
1) Bu videonun kreatif olarak güçlü ve zayıf yönlerini analiz et (ilk 3 saniye kancası, tempo, dikey/yatay uyum gibi teknik verilere dayanarak)
2) Bu ürün/işletme için 3 farklı yeni video fikri öner. Her biri için: hook (ilk 3 saniye), ana anlatı, kapanış/CTA sahnesi ayrı ayrı yazılsın.
"""
    return call_openai(api_key, system_prompt, user_prompt)


# ============================================================
# YARDIMCI: sparkline
# ============================================================
def create_sparkline(y_values, bar_values=None, line_color="#7f00ff"):
    fig = go.Figure()
    if bar_values is not None:
        fig.add_trace(go.Bar(y=bar_values, marker_color='rgba(200,200,200,0.3)', showlegend=False))
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


# ============================================================
# SIDEBAR — VERİ YÜKLEME
# ============================================================
st.sidebar.header("🛡️ Veri Yükleme Merkezi")
st.sidebar.markdown("Verileriniz sunucularda saklanmaz, sadece bu oturumda işlenir.")

secim_turu = st.sidebar.radio(
    "Verileri nasıl yüklemek istersiniz?",
    ["📁 Excel / CSV Dosyası Yükle", "🔑 API ile Bağlan (Gerçek Zamanlı)"]
)

df_raw = None

if secim_turu == "📁 Excel / CSV Dosyası Yükle":
    st.sidebar.info("Meta Reklam Yöneticisi'nden aldığınız dışa aktarım raporunu (.csv veya .xlsx) yükleyin.")
    uploaded_report = st.sidebar.file_uploader("Reklam Raporu Dosyası", type=["csv", "xlsx"])
    if uploaded_report is not None:
        try:
            if uploaded_report.name.endswith('.csv'):
                df_raw = pd.read_csv(uploaded_report)
            else:
                df_raw = pd.read_excel(uploaded_report)
            st.sidebar.success("✅ Rapor başarıyla yüklendi!")
        except Exception as e:
            st.sidebar.error(f"Dosya okuma hatası: {e}")
else:
    st.sidebar.warning("⚠️ API anahtarınız sadece bu oturumda, tarayıcı hafızasında tutulur.")
    meta_token = st.sidebar.text_input("Meta Access Token", type="password")
    ad_account_id = st.sidebar.text_input("Reklam Hesabı ID", help="Örn: 1234567890 veya act_1234567890")
    date_preset = st.sidebar.selectbox("Tarih Aralığı", ["today", "yesterday", "last_7d", "last_30d", "last_90d"], index=3)

    if meta_token and ad_account_id:
        if st.sidebar.button("📡 Verileri Çek"):
            with st.spinner("Meta API'den veriler çekiliyor..."):
                try:
                    df_raw = fetch_meta_insights(meta_token, ad_account_id, date_preset)
                    if df_raw.empty:
                        st.sidebar.warning("Seçilen tarih aralığında veri bulunamadı.")
                    else:
                        st.session_state["df_raw"] = df_raw
                        st.sidebar.success(f"✅ {len(df_raw)} reklam verisi çekildi!")
                except Exception as e:
                    st.sidebar.error(f"❌ {e}")

    if "df_raw" in st.session_state and df_raw is None:
        df_raw = st.session_state["df_raw"]

st.sidebar.markdown("---")
openai_key = st.sidebar.text_input("🔑 OpenAI API Key (AI Analizi İçin)", type="password")
target_cpa = st.sidebar.number_input("🎯 Hedef CPA (TL)", value=100.0, step=10.0)
product_info = st.sidebar.text_area("🛍️ Ürün/İşletme Açıklaması (opsiyonel ama önerilir)",
                                     placeholder="Örn: Kadınlara yönelik el yapımı deri çanta satıyoruz, hedef kitle 25-40 yaş.")

# İşlenmiş veri
df = None
summary = None
findings = None
if df_raw is not None and not df_raw.empty:
    mapping = map_columns(df_raw)
    df = compute_metrics(df_raw, mapping)
    summary = summarize(df)
    findings = diagnose(summary, target_cpa)

# ============================================================
# ANA ARAYÜZ
# ============================================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Kontrol Paneli", "🧠 AI Performans Dedektifi", "🎥 Kreatif Stüdyo", "🚀 Strateji & Yeni Sipariş Planı"
])

# ---------------- TAB 1: KONTROL PANELİ ----------------
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
            🔒 <b>Gizlilik Güvencesi:</b> Bu araç verilerinizi 3. parti bir veritabanına kaydetmez.
            Analizler sadece bu oturum boyunca bellekte tutulur.
        </div>
    """, unsafe_allow_html=True)

    if summary is not None:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="gradient-card-purple"><div class="card-flex">
                <span class="card-title-text">Toplam Harcama</span>
                <span class="card-value-text">{summary['total_spend']:,.0f} TL</span></div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="gradient-card-red"><div class="card-flex">
                <span class="card-title-text">CTR</span>
                <span class="card-value-text">%{summary['ctr']:.2f}</span></div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="gradient-card-darkpurple"><div class="card-flex">
                <span class="card-title-text">CPA</span>
                <span class="card-value-text">{summary['cpa']:,.0f} TL</span></div></div>""", unsafe_allow_html=True)
        with c4:
            st.markdown(f"""<div class="gradient-card-green"><div class="card-flex">
                <span class="card-title-text">ROAS</span>
                <span class="card-value-text">{summary['roas']:.2f}x</span></div></div>""", unsafe_allow_html=True)

        st.markdown("###")
        c5, c6, c7 = st.columns(3)
        c5.metric("Toplam Satın Alma", f"{summary['total_purchases']:.0f}")
        c6.metric("Dönüşüm Oranı", f"%{summary['conv_rate']:.2f}")
        c7.metric("Ortalama Frequency", f"{summary['avg_freq']:.2f}")

        st.markdown("---")
        st.markdown("### 📋 Detaylı Reklam Verileri (Hesaplanmış Metriklerle)")
        display_cols = [c for c in df.columns if not c.startswith("_")]
        st.dataframe(df[display_cols], use_container_width=True)

        csv_export = df[display_cols].to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Hesaplanmış Raporu İndir (CSV)", csv_export, "reklam_analiz_raporu.csv", "text/csv")
    else:
        st.info("💡 Sol menüden bir Excel/CSV raporu yükleyin ya da Meta API ile bağlanın.")

# ---------------- TAB 2: AI PERFORMANS DEDEKTİFİ ----------------
with tab2:
    st.header("🧠 Yapay Zeka Teşhis Raporu — Neden Kötü Gidiyor?")

    if findings is not None:
        for f in findings:
            css_class = {"critical": "diag-critical", "warning": "diag-warning", "good": "diag-good"}[f["level"]]
            icon = {"critical": "🔴", "warning": "🟡", "good": "🟢"}[f["level"]]
            st.markdown(f"""
                <div class="diag-card {css_class}">
                    <b>{icon} {f['title']}</b><br>
                    <span style="font-size:0.9rem;">{f['detail']}</span><br>
                    <span style="font-size:0.9rem;"><b>Öneri:</b> {f['recommendation']}</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 🤖 Derinlemesine AI Analizi (OpenAI destekli, veriye özel)")
        if st.button("🚀 Derin AI Analizini Başlat"):
            if not openai_key:
                st.error("Lütfen sol menüden OpenAI API anahtarınızı girin.")
            else:
                with st.spinner("Yapay zeka kampanya verilerinizi inceliyor..."):
                    try:
                        report = generate_ai_strategy(openai_key, summary, findings, target_cpa, product_info)
                        st.markdown(report)
                    except Exception as e:
                        st.error(f"❌ {e}")
    else:
        st.warning("⚠️ Lütfen önce sol menüden analiz verilerini yükleyin.")

# ---------------- TAB 3: KREATİF STÜDYO ----------------
with tab3:
    st.header("🎥 Kreatif Test — Video Analizi ve Yeni Fikirler")
    st.write("Reklam videonuzu yükleyin; teknik kreatif analizi + AI destekli yeni video fikirleri alın.")

    video_file = st.file_uploader("Video Dosyası Seçin", type=["mp4", "mov", "avi", "mkv"])

    if video_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.name)[1]) as tmp:
            tmp.write(video_file.read())
            tmp_path = tmp.name

        with st.spinner("Video analiz ediliyor..."):
            try:
                stats = analyze_video(tmp_path)
                st.session_state["video_stats"] = stats
            except Exception as e:
                st.error(f"❌ Video analiz hatası: {e}")
                stats = None
            finally:
                os.unlink(tmp_path)

        if stats:
            st.success("✅ Analiz tamamlandı.")
            vc1, vc2, vc3, vc4 = st.columns(4)
            vc1.metric("Süre", f"{stats['duration_sec']} sn")
            vc2.metric("Çözünürlük", stats['resolution'])
            vc3.metric("Ortalama Parlaklık", stats['avg_brightness'])
            vc4.metric("Sahne Değişimi", stats['scene_changes'])

            if not stats["is_vertical"]:
                st.warning("⚠️ Video yatay formatta. Meta/Instagram Reels/Stories için dikey (9:16) format genelde daha iyi performans gösterir.")
            if stats["first_3s_motion"] is not None and stats["first_3s_motion"] < 15:
                st.warning("⚠️ İlk 3 saniyede hareket/değişim düşük — izleyici kaydırıp geçebilir (weak hook). İlk saniyelerde güçlü bir görsel kanca kullanmayı düşünün.")

            st.markdown("---")
            if st.button("🎬 AI ile Video Fikirleri ve Kreatif Değerlendirme Üret"):
                if not openai_key:
                    st.error("Lütfen sol menüden OpenAI API anahtarınızı girin.")
                else:
                    with st.spinner("Yeni video fikirleri üretiliyor..."):
                        try:
                            ideas = generate_video_ideas(openai_key, stats, product_info)
                            st.markdown(ideas)
                        except Exception as e:
                            st.error(f"❌ {e}")

# ---------------- TAB 4: STRATEJİ & YENİ SİPARİŞ PLANI ----------------
with tab4:
    st.header("🚀 Daha Çok Sipariş Almak İçin Strateji")
    if summary is not None:
        st.write("Aşağıdaki buton, kampanya verilerinize ve (varsa) video analizinize dayanarak "
                  "sipariş artırmaya yönelik somut bir 30 günlük aksiyon planı üretir.")
        if st.button("📈 Sipariş Artırma Stratejisini Oluştur"):
            if not openai_key:
                st.error("Lütfen sol menüden OpenAI API anahtarınızı girin.")
            else:
                with st.spinner("Strateji hazırlanıyor..."):
                    try:
                        report = generate_ai_strategy(openai_key, summary, findings, target_cpa, product_info)
                        st.markdown(report)
                    except Exception as e:
                        st.error(f"❌ {e}")
    else:
        st.info("💡 Önce sol menüden reklam verilerinizi yükleyin.")
