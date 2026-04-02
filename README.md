# 🚀 Kampanya Bütçe ve CPA Optimizasyon Projesi


Bu uygulama, reklam kampanyalarınızın performans verilerini (Excel) analiz ederek, belirli kural setleri ve önceliklere göre bütçenizi en verimli şekilde dağıtmanıza yardımcı olur.

---

## 🛠️ Temel Özellikler ve Kurallar

Uygulama arka planda aşağıdaki hiyerarşiyi takip eder:

1.  **KPI Önceliği:** `New Target CPA`, verilen `Label KPI` değerine odaklanır. Bütçe harcanamadığı durumlarda %15'lik bir esneklik tanır.
2.  **Bütçe Dağıtımı:** Kalan bütçeyi, ayın geri kalan günlerine ve kampanyaların son 3 günlük performans ağırlıklarına göre paylaştırır.
3.  **Hindistan Kısıtı (%30):** Hindistan pazarı için ayrılan toplam harcama, etiketin toplam bütçesinin %30'unu aşamaz.
4.  **Ülke Çarpanları:** 
    - `PREM` (Gelişmiş) kampanyalara +%10 bütçe bonusu.
    - `DEVP` (Gelişmekte olan) kampanyalara -%10 bütçe kısıtı.
5.  **Alt Limit:** Hiçbir kampanya için günlük bütçe **5** birimin altına düşmez.
6.  **Güvenlik:** Hedef CPA değerleri asla 0 olamaz.

---

## 🚀 Kurulum ve Çalıştırma

1.  **Sanal Ortam Oluşturun:**
    ```powershell
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  **Gerekli Kütüphaneleri Kurun:**
    ```powershell
    pip install -r requirements.txt
    ```

3.  **Uygulamayı Başlatın:**
    ```powershell
    python app.py
    ```

4.  **Kullanım:**
    - Tarayıcıda açılan Gradio arayüzüne `veri.xlsx` dosyanızı yükleyin.
    - "Hesapla" butonuna basın.
    - Optimize edilmiş Excel dosyasını indirin.

---

## 📂 Proje Yapısı

- `app.py`: Ana uygulama ve algoritma mantığı.
- `requirements.txt`: Gerekli bağımlılıklar (Pandas, Gradio, OpenPyXL).
- `veri.xlsx`: Örnek veri seti.
- `README.md`: Proje dökümantasyonu.

---
**Geliştiren:** [Atike KÜÇÜKVAROL]
