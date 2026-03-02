import discord
import os
import asyncio
import time
import requests
from keep_alive import keep_alive

# Environment (Ortam) Degiskenlerini Cekiyoruz
TOKEN = os.environ.get("TOKEN")
BEKLEME_SURE = os.environ.get("BEKLEME_SURE") # dakika cinsinden, ornek: "1"
WEBHOOK = os.environ.get("WEBHOOK")
TARGET_ID = os.environ.get("TARGET_ID")

class TrackerClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Bot ilk basladiginda baslangic zamanini referans alir.
        # Isterseniz ilk baslangicta degil de sadece ilk mesaj atildiginda da baslatabilirsiniz.
        self.last_message_time = time.time()
        self.notified = False
        
        try:
            self.bekleme_saniye = int(BEKLEME_SURE) * 60 if BEKLEME_SURE else 60
        except ValueError:
            print("HATA: BEKLEME_SURE sadece sayilardan olusmali! Standart olarak 1 dakika uygulaniyor.")
            self.bekleme_saniye = 60

    async def setup_hook(self) -> None:
        self.bg_task = self.loop.create_task(self.check_activity())

    async def on_ready(self):
        print('-----------------------------------------')
        print(f'Giris Yapildi: {self.user}')
        print(f'Hedef ID: {TARGET_ID}')
        print(f'Bekleme Suresi: {self.bekleme_saniye / 60} dakika')
        print('-----------------------------------------')

    async def on_message(self, message):
        # Sadece hedef kullanicinin mesajlari
        if str(message.author.id) == str(TARGET_ID):
            self.last_message_time = time.time()
            if self.notified:
                print(f"Kullanici tekrar mesaj gonderdi. Sayac yeniden {self.bekleme_saniye / 60} dakika icin basladi.")
            self.notified = False

    async def check_activity(self):
        await self.wait_until_ready()
        while not self.is_closed():
            current_time = time.time()
            time_passed = current_time - self.last_message_time

            # Belirlenen sure gectiyse ve henuz bildirim atmadiysak
            if time_passed >= self.bekleme_saniye and not self.notified:
                print(f"[BILDIRIM] Kullanici {self.bekleme_saniye / 60} dakikadir mesaj atmiyor. Webhook tetikleniyor...")
                self.send_webhook()
                self.notified = True # Spami engellemek icin true yapiyoruz

            await asyncio.sleep(5) # Her 5 saniyede bir durumu kontrol et

    def send_webhook(self):
        if not WEBHOOK:
            print("Webhook URL tanimli degil!")
            return
            
        data = {
            "content": f"⚠️ <@{TARGET_ID}> kullanıcısı {self.bekleme_saniye // 60} dakikadır mesaj atmıyor!",
            "username": "Mesaj Kesintisi Bildirimi"
        }
        try:
            response = requests.post(WEBHOOK, json=data)
            if response.status_code in [200, 204]:
                print("Webhook başarıyla iletildi.")
            else:
                print(f"Webhook gönderilirken hata oluştu. Durum Kodu: {response.status_code}")
        except Exception as e:
            print(f"Webhook gönderim hatası: {e}")

# Render gibi platformlarda projenin kapanmamasi icin dummy bir web sunucusu aciyoruz
keep_alive()

if not TOKEN or not TARGET_ID or not WEBHOOK:
    print("HATA: Lutfen TOKEN, TARGET_ID, WEBHOOK ve BEKLEME_SURE degiskenlerini Environment kismina ekleyin.")
else:
    try:
        # discord.py-self kütüphanesi self botları destekler
        client = TrackerClient()
        client.run(TOKEN)
    except discord.LoginFailure:
        print("HATA: Hatali token. Lutfen hesabin self tokenini girdiginizden emin olun.")
    except Exception as e:
        print(f"Beklenmeyen bir hata olustu: {e}")
