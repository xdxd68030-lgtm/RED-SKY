# Discord Tracker Bot

Bu proje belirli bir kullanıcının Discord üzerinden size ne zamandır mesaj atmadığını takip eder ve eğer belirlenen süreyi aşarsa bir Webhook aracılığıyla bildirim gönderir.

## Render Üzerinde Kurulum

1. Bu projeyi kendi GitHub hesabınıza yükleyin (Fork veya yeni repo açarak).
2. [Render.com](https://render.com/) adresine girin ve yeni bir **Web Service** oluşturun.
3. GitHub reponuzu Render'a bağlayın.
4. Ayarları şu şekilde yapılandırın:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
5. Sayfayı aşağı kaydırıp **Environment Variables (Çevre Değişkenleri)** bölümüne gelin ve şu 4 değeri ekleyin:
   - `TOKEN` : Kendi hesabınızın Discord token'ı (Self token)
   - `TARGET_ID` : Mesajlarını dinlemek istediğiniz kişinin Discord ID'si (Örn: 123456789012345678)
   - `WEBHOOK` : Bildirimin düşeceği Discord kanalının webhook URL'si
   - `BEKLEME_SURE` : Hedefin ne kadar süre mesaj atmadığında bildirim geleceği. (Örn: `1` yazarsanız 1 dakika mesaj atmazsa webhook gönderilir.)

## Uyarı
Self-bot kullanmak Discord Hizmet Şartlarına (ToS) aykırıdır ve hesabınızın kapatılmasına yol açabilir. Sorumluluk tamamen size aittir.
