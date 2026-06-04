import streamlit as st
import simpy
import random
import pandas as pd
import numpy as np
import plotly.express as px

# Web Sayfası Ayarları (إعدادات واجهة المستخدم)
st.set_page_config(page_title="Banka Simülasyon Sistemi", layout="wide")

st.title("🏛️ Gelişmiş Banka Kuyruk Simülasyonu Yönetim Paneli")
st.markdown("Haftalık gün profillerine, saatlik yoğunluklara ve müşteri türlerine göre dinamik simülasyon ve teslimat sistemi.")

# --- Sol Panel: Kullanıcı Girdileri (التحكم بالمدخلات) ---
st.sidebar.header("🔧 Simülasyon Parametreleri")
secilen_gun = st.sidebar.selectbox("Simülasyon Günü Seçin", ["Pazartesi (Çok Yoğun)", "Çarşamba (Sakin)", "Cuma (Orta Yoğunluk)"])
num_vezne = st.sidebar.slider("Vezne Gişe Sayısı (Kasa)", 1, 5, 1)
num_temsilci = st.sidebar.slider("Müşteri Temsilcisi Sayısı", 1, 5, 2)
sim_time = st.sidebar.slider("Simülasyon Süresi (Dakika)", 60, 480, 480) # 8 Saat

# Günlük Yoğunluk Katsayıları (طلبات الأستاذ بخصوص أيام الأسبوع)
gun_katsayilari = {"Pazartesi (Çok Yoğun)": 0.6, "Çarşamba (Sakin)": 1.3, "Cuma (Orta Yoğunluk)": 1.0}

def get_arrival_interval(current_time, gun_turu):
    """Günün saatine göre geliş yoğunluğunu ayarlar (Sabah/Öğle farkı)"""
    base_interval = 2.5
    charpan = gun_katsayilari[gun_turu]
    if current_time < 120:  # İlk 2 saat (Sabah Yoğunluğu)
        return base_interval * 0.5 * charpan
    elif 120 <= current_time < 180: # Öğle Arası (Sakin)
        return base_interval * 1.5 * charpan
    else: # Öğleden Sonra (Orta Yoğunluk)
        return base_interval * 0.8 * charpan

# --- SimPy Simülasyon Mantığı (محرك المحاكاة الخلفي) ---
def customer(env, name, musteri_turu, islem_turu, vezne_kaynak, temsilci_kaynak, data):
    arrival_time = env.now
    if islem_turu == "Vezne":
        gişe_adı = "Vezne Gişesi"
        kaynak = vezne_kaynak
        servis_süresi = max(1, np.random.normal(3, 1)) # Ortalama 3 dk
    else:
        gişe_adı = "Müşteri Temsilcisi"
        kaynak = temsilci_kaynak
        servis_süresi = max(5, np.random.normal(12, 3)) # Ortalama 12 dk (Kredi vb.)

    with kaynak.request() as request:
        yield request
        wait_time = env.now - arrival_time
        yield env.timeout(servis_süresi)
        
        data.append({
            "Müşteri": name,
            "Tür": musteri_turu,
            "Gittiği Gişe": gişe_adı,
            "Geliş Anı (dk)": round(arrival_time, 2),
            "Bekleme Süresi (dk)": round(wait_time, 2),
            "Servis Süresi (dk)": round(servis_süresi, 2)
        })

def bank_setup(env, num_v, num_t, data, gun_turu):
    vezne_kaynak = simpy.Resource(env, capacity=num_v)
    temsilci_kaynak = simpy.Resource(env, capacity=num_t)
    i = 1
    while True:
        yield env.timeout(random.expovariate(1.0 / get_arrival_interval(env.now, gun_turu)))
        
        # Müşteri Türü Dağılımı (%60 Bireysel, %25 Kurumsal, %15 Yabancı)
        tür_şansı = random.random()
        if tür_şansı < 0.60:
            musteri_turu, islem_turu = "Bireysel Müşteri", random.choice(["Vezne", "Temsilci"])
        elif tür_şansı < 0.85:
            musteri_turu, islem_turu = "Kurumsal Müşteri", "Temsilci"
        else:
            musteri_turu, islem_turu = "Yabancı Uyruklu", random.choice(["Vezne", "Temsilci"])

        env.process(customer(env, f"Müşteri {i}", musteri_turu, islem_turu, vezne_kaynak, temsilci_kaynak, data))
        i += 1

# --- Simülasyonu Çalıştır ve Veri Çek ---
simulation_data = []
env = simpy.Environment()
env.process(bank_setup(env, num_vezne, num_temsilci, simulation_data, secilen_gun))
env.run(until=sim_time)

df = pd.DataFrame(simulation_data)

# --- Görsel Dashboard Ekranı (عرض النتائج الحقيقية) ---
if not df.empty:
    v_df = df[df["Gittiği Gişe"] == "Vezne Gişesi"]
    t_df = df[df["Gittiği Gişe"] == "Müşteri Temsilcisi"]
    
    avg_v_wait = v_df["Bekleme Süresi (dk)"].mean() if not v_df.empty else 0
    avg_t_wait = t_df["Bekleme Süresi (dk)"].mean() if not t_df.empty else 0

    # Üst Bilgi Kartları (Cards)
    col1, col2, col3 = st.columns(3)
    col1.metric("Vezne Ort. Bekleme Süresi", f"{avg_v_wait:.2f} dk")
    col2.metric("Müşteri Temsilcisi Ort. Bekleme", f"{avg_t_wait:.2f} dk")
    col3.metric("Toplam Hizmet Alan Müşteri", f"{len(df)} Kişi")

    st.markdown("---")

    # Grafikler
    col4, col5 = st.columns(2)
    
    with col4:
        st.subheader("📊 Gişelere Göre Ortalama Bekleme Süreleri")
        fig_bar = px.bar(df.groupby("Gittiği Gişe")["Bekleme Süresi (dk)"].mean().reset_index(), 
                         x="Gittiği Gişe", y="Bekleme Süresi (dk)", color="Gittiği Gişe",
                         color_discrete_map={"Vezne Gişesi": "#2980b9", "Müşteri Temsilcisi": "#8e44ad"})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col5:
        st.subheader("🍕 Banka Müşteri Türleri Dağılımı")
        fig_pie = px.pie(df, names="Tür", color="Tür", 
                         color_discrete_map={"Bireysel Müşteri": "#3498db", "Kurumsal Müşteri": "#9b59b6", "Yabancı Uyruklu": "#e67e22"})
        st.plotly_chart(fig_pie, use_container_width=True)

    # Veri Tablosu
    st.subheader("📋 Detaylı Simülasyon Çıktı Verisi (Pandas Tablosu)")
    st.dataframe(df)
else:
    st.error("Simülasyon verisi hesaplanamadı.")