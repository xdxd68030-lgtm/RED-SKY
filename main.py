import discord
import os
import asyncio
import time
import aiohttp
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

# Environment (Ortam) Değişkenleri
TOKEN = os.environ.get("TOKEN")
BEKLEME_SURE = os.environ.get("BEKLEME_SURE")  # dakika cinsinden
WEBHOOK_URL = os.environ.get("WEBHOOK")

TARGET_IDS_RAW = os.environ.get("TARGET_IDS", "")
TARGET_IDS = [uid.strip() for uid in TARGET_IDS_RAW.split(",") if uid.strip()]

# İstanbul saat dilimi (UTC+3)
ISTANBUL_TZ = timezone(timedelta(hours=3))

class TrackerClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        try:
            self.bekleme_saniye = int(BEKLEME_SURE) * 60 if BEKLEME_SURE else 60
        except ValueError:
            print("HATA: BEKLEME_SURE sadece sayılardan oluşmalı! Varsayılan: 1 dakika.")
            self.bekleme_saniye = 60

        self.last_message_time = {uid: None for uid in TARGET_IDS}
        self.notified = {uid: False for uid in TARGET_IDS}
        self.last_message_info = {uid: None for uid in TARGET_IDS}
        self.session = None  # Asenkron HTTP oturumu

    async def setup_hook(self):
        """Bot çalışmaya başladığında yapılacak ilk işlemler."""
        self.session = aiohttp.ClientSession()
        # Arka plan kontrol görevini başlat
        self.loop.create_task(self.check_activity())

    async def on_ready(self):
        print('-----------------------------------------')
        print(f'Giriş Yapıldı: {self.user}')
        print(f"Takip Edilen ID'ler: {TARGET_IDS}")
        print(f'Bekleme Süresi: {self.bekleme_saniye / 60} dakika')
        print('-----------------------------------------')

    async def on_message(self, message):
        uid = str(message.author.id)
        if uid in TARGET_IDS:
            self.last_message_time[uid] = time.time()

            # Kanal ve Mesaj linki oluşturma
            if message.guild:
                link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            else:
                link = f"https://discord.com/channels/@me/{message.channel.id}/{message.id}"

            # UTC zamanını İstanbul zamanına çevir
            created_at = message.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            istanbul_time = created_at.astimezone(ISTANBUL_TZ)

            self.last_message_info[uid] = {
                "content": message.content if message.content else "(Görsel/Dosya/Embed içeriği)",
                "link": link,
                "timestamp": istanbul_time
            }

            if self.notified[uid]:
                print(f"[{uid}] Kullanıcı tekrar aktif oldu, sayaç sıfırlandı.")
            self.notified[uid] = False

    async def check_activity(self):
        """Kullanıcıların sessiz kalıp kalmadığını kontrol eden döngü."""
        await self.wait_until_ready()
        while not self.is_closed():
            current_time = time.time()
            for uid in TARGET_IDS:
                if self.last_message_time[uid] is None:
                    continue

                passed = current_time - self.last_message_time[uid]
                if passed >= self.bekleme_saniye and not self.notified[uid]:
                    print(f"[UYARI] {uid} sessizliğe gömüldü, bildirim gönderiliyor...")
                    await self.send_webhook(uid)
                    self.notified[uid] = True
            await asyncio.sleep(5) # 5 saniyede bir kontrol et

    async def send_webhook(self, uid):
        """Async (asenkron) olarak bildirim gönderir."""
        if not WEBHOOK_URL or not self.session:
            return

        info = self.last_message_info.get(uid)
        bekleme_dk = self.bekleme_saniye // 60

        if info:
            saat = info["timestamp"].strftime("%H:%M")
            mesaj = info["content"]
            link = info["link"]
        else:
            saat, mesaj, link = "Bilinmiyor", "Veri yok", "Mevcut değil"

        embed = {
            "title": "KULLANICI SESSİZLİĞE GÖMÜLDÜ! 🔴",
            "color": 0xFF4444,
            "fields": [
                {"name": "Hedef", "value": f"<@{uid}> (`{uid}`)", "inline": False},
                {"name": "Süre", "value": f"{bekleme_dk} dk sessiz", "inline": True},
                {"name": "Son Mesaj", "value": f"`{saat}`", "inline": True},
                {"name": "İçerik", "value": mesaj[:1024], "inline": False},
                {"name": "Kanala Git", "value": f"[Mesajı Gör]({link})", "inline": False}
            ],
            "footer": {"text": "RED SKY MONITORING SYSTEM"}
        }

        data = {"username": "RED SKY TARGET SYSTEM", "embeds": [embed]}

        try:
            async with self.session.post(WEBHOOK_URL, json=data) as resp:
                if resp.status in [200, 204]:
                    print(f"[{uid}] Webhook başarıyla gönderildi.")
                else:
                    print(f"[{uid}] Webhook hatası: {resp.status}")
        except Exception as e:
            print(f"[{uid}] Webhook gönderilemedi: {e}")

    async def close(self):
        """Bot kapandığında oturumu da kapatır."""
        if self.session:
            await self.session.close()
        await super().close()

# Flask keep_alive (Render/Replit için)
keep_alive()

if not TOKEN or not TARGET_IDS or not WEBHOOK_URL:
    print("HATA: TOKEN, TARGET_IDS veya WEBHOOK değişkenleri bulunamadı!")
else:
    # Tüm Yetkileri (Intents) tanımlıyoruz
    intents = discord.Intents.all()
    
    try:
        client = TrackerClient(intents=intents)
        client.run(TOKEN)
    except discord.LoginFailure:
        print("HATA: Token geçersiz!")
    except Exception as e:
        print(f"Beklenmeyen Hata: {e}")
