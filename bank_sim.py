import simpy
import random
import pandas as pd
import numpy as np

# 1. Simülasyon Ayarları
RANDOM_SEED = 42
SIM_TIME = 480  # 8 saatlik bir iş günü (480 dakika)

# Zaman Yoğunluk Katsayıları (Pazartesi sabahı çok yoğun, hafta ortası sakin)
# Günlere göre geliş aralığı çarpanı (Küçük sayı = Daha yoğun/sık geliş)
GUN_YOGUNLUK = {"Pazartesi": 0.6, "Çarşamba": 1.2, "Cuma": 1.0}
SECILEN_GUN = "Pazartesi" # Değiştirerek test edebilirsiniz

def get_arrival_interval(current_time):
    """Günün saatine göre geliş sıklığını ayarlar (Sabah ve öğle sonu yoğun)"""
    base_interval = 2.0  # Normalde 2 dakikada bir müşteri gelir
    charpan = GUN_YOGUNLUK[SECILEN_GUN]
    
    if current_time < 120:  # İlk 2 saat (Sabah Yoğunluğu)
        return base_interval * 0.5 * charpan
    elif 120 <= current_time < 240: # Öğle arası civarı (Sakin)
        return base_interval * 1.5 * charpan
    else: # Öğleden sonra (Orta Yoğunluk)
        return base_interval * 0.8 * charpan

def customer(env, name, müşteri_türü, işlem_türü, vezne_kaynak, temsilci_kaynak, data):
    geliş_zamanı = env.now
    
    # İşlem türüne göre ilgili gişeye yönlendirme ve süre belirleme
    if işlem_türü == "Vezne İşlemi (Para Çekme/Yatırma)":
        gişe_adı = "Vezne"
        kaynak = vezne_kaynak
        servis_süresi = max(1, np.random.normal(3, 1)) # Ortalama 3 dakika
    else:
        gişe_adı = "Müşteri Temsilcisi"
        kaynak = temsilci_kaynak
        servis_süresi = max(5, np.random.normal(12, 3)) # Ortalama 12 dakika (Kredi vb.)

    # İlgili gişede sıraya girme
    with kaynak.request() as request:
        yield request
        bekleme_süresi = env.now - geliş_zamanı
        yield env.timeout(servis_süresi)
        
        data.append({
            "Müşteri": name,
            "Tür": müşteri_türü,
            "İşlem": işlem_türü,
            "Gittiği Gişe": gişe_adı,
            "Geliş Anı": round(geliş_zamanı, 2),
            "Bekleme Süresi": round(bekleme_süresi, 2),
            "Servis Süresi": round(servis_süresi, 2),
            "Çıkış Anı": round(env.now, 2)
        })

def bank_setup(env, num_vezne, num_temsilci, data):
    # Gişelerin tanımlanması (Farklı kaynaklar ve kapasiteler)
    vezne_kaynak = simpy.Resource(env, capacity=num_vezne)
    temsilci_kaynak = simpy.Resource(env, capacity=num_temsilci)
    
    i = 1
    while True:
        # Zaman profiline göre bir sonraki müşterinin geliş süresi
        yield env.timeout(random.expovariate(1.0 / get_arrival_interval(env.now)))
        
        # Müşteri türü belirleme (%60 Bireysel, %25 Kurumsal, %15 Yabancı)
        tür_şansı = random.random()
        if tür_şansı < 0.60:
            müşteri_türü = "Bireysel"
            işlem_türü = random.choice(["Vezne İşlemi (Para Çekme/Yatırma)", "Kredi Başvurusu"])
        elif tür_şansı < 0.85:
            müşteri_türü = "Kurumsal"
            işlem_türü = "Müşteri Temsilcisi İşlemleri"
        else:
            müşteri_türü = "Yabancı Uyruklu"
            işlem_türü = random.choice(["Vezne İşlemi (Para Çekme/Yatırma)", "Müşteri Temsilcisi İşlemleri"])

        env.process(customer(env, f"Müşteri {i}", müşteri_türü, işlem_türü, vezne_kaynak, temsilci_kaynak, data))
        i += 1

# Simülasyonu Çalıştırma (1 Vezne, 2 Müşteri Temsilcisi)
simulation_data = []
env = simpy.Environment()
env.process(bank_setup(env, num_vezne=1, num_temsilci=2, data=simulation_data))
env.run(until=SIM_TIME)

# Sonuçları Gösterme
df = pd.DataFrame(simulation_data)
print(f"\n=== {SECILEN_GUN} GÜNÜ SİMÜLASYON SONUÇLARI ===")
print(df.head(15)) # İlk 15 müşterinin detayları

# Gişelere göre analiz
print("\n=== GİŞE BAZLI PERFORMANS ÖZETİ ===")
özet = df.groupby("Gittiği Gişe")["Bekleme Süresi"].agg(['count', 'mean', 'max']).rename(columns={'count': 'Hizmet Alan', 'mean': 'Ort. Bekleme (dk)', 'max': 'Maks. Bekleme (dk)'})
print(özet)
