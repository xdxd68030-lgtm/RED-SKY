import discord
import os
import asyncio
import time
import requests
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

# Environment (Ortam) Degiskenlerini Cekiyoruz
TOKEN = os.environ.get("TOKEN")
BEKLEME_SURE = os.environ.get("BEKLEME_SURE")  # dakika cinsinden, ornek: "1"
WEBHOOK = os.environ.get("WEBHOOK")

# Birden fazla kullanici ID'si virgullerle ayrilarak yazilir
# Ornek: TARGET_IDS=123456789,987654321,111222333
TARGET_IDS_RAW = os.environ.get("TARGET_IDS", "")
TARGET_IDS = [uid.strip() for uid in TARGET_IDS_RAW.split(",") if uid.strip()]

# Istanbul saat dilimi (UTC+3)
ISTANBUL_TZ = timezone(timedelta(hours=3))


class TrackerClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.bekleme_saniye = int(BEKLEME_SURE) * 60 if BEKLEME_SURE else 60
        except ValueError:
            print("HATA: BEKLEME_SURE sadece sayilardan olusmali! Standart olarak 1 dakika uygulaniyor.")
            self.bekleme_saniye = 60

        # None = henuz mesaj gormemisiz, bildirim ATMA
        # time.time() = mesaj goruldu, susarsa bildirim AT
        self.last_message_time = {uid: None for uid in TARGET_IDS}
        self.notified = {uid: False for uid in TARGET_IDS}
        self.last_message_info = {uid: None for uid in TARGET_IDS}

    async def on_ready(self):
        print('-----------------------------------------')
        print(f'Giris Yapildi: {self.user}')
        print(f"Takip Edilen ID'ler: {TARGET_IDS}")
        print(f'Bekleme Suresi: {self.bekleme_saniye / 60} dakika')
        print('-----------------------------------------')
        # Background task'i sadece bir kez baslat
        if not hasattr(self, '_bg_task_started'):
            self._bg_task_started = True
            asyncio.ensure_future(self.check_activity())

    async def on_message(self, message):
        uid = str(message.author.id)
        if uid in TARGET_IDS:
            self.last_message_time[uid] = time.time()

            if message.guild:
                link = f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}"
            else:
                link = f"https://discord.com/channels/@me/{message.channel.id}/{message.id}"

            # discord.py-self 2.x'te created_at zaten timezone-aware (UTC)
            try:
                istanbul_time = message.created_at.astimezone(ISTANBUL_TZ)
            except Exception:
                istanbul_time = message.created_at.replace(tzinfo=timezone.utc).astimezone(ISTANBUL_TZ)

            self.last_message_info[uid] = {
                "content": message.content if message.content else "(Metin icerigi yok - Dosya/Embed vb.)",
                "link": link,
                "timestamp": istanbul_time
            }

            if self.notified[uid]:
                print(f"[{uid}] Kullanici tekrar mesaj gonderdi. Sayac sifirlandi.")
            self.notified[uid] = False

    async def check_activity(self):
        await self.wait_until_ready()
        while not self.is_closed():
            current_time = time.time()
            for uid in TARGET_IDS:
                # Sadece en az 1 mesaj gorduysek kontrol et
                if self.last_message_time[uid] is None:
                    continue

                time_passed = current_time - self.last_message_time[uid]
                if time_passed >= self.bekleme_saniye and not self.notified[uid]:
                    print(f"[BILDIRIM] {uid} icin webhook tetikleniyor...")
                    self.send_webhook(uid)
                    self.notified[uid] = True
            await asyncio.sleep(5)

    def send_webhook(self, uid):
        if not WEBHOOK:
            return

        info = self.last_message_info.get(uid)
        bekleme_dk = self.bekleme_saniye // 60

        if info:
            son_mesaj_saati = info["timestamp"].strftime("%H:%M")
            son_mesaj = info["content"]
            git_link = info["link"]
        else:
            son_mesaj_saati = "Bilinmiyor"
            son_mesaj = "Bilinmiyor"
            git_link = "Mevcut degil"

        embed = {
            "title": "KULLANICI MESAJ KESMİŞTİR XD",
            "color": 0xFF4444,
            "fields": [
                {"name": "Kullanıcı ID", "value": f"<@{uid}> (`{uid}`)", "inline": False},
                {"name": "Sure", "value": f"{bekleme_dk} dakika sessiz kaldi", "inline": False},
                {"name": "Son Mesaj Saati", "value": f"`{son_mesaj_saati}`", "inline": False},
                {"name": "Son Mesaj", "value": son_mesaj[:1024], "inline": False},
                {"name": "Git", "value": git_link, "inline": False}
            ],
            "footer": {"text": "RED SKY TARGET SYSTEM"}
        }

        data = {"username": "RED SKY TARGET SYSTEM", "embeds": [embed]}

        try:
            response = requests.post(WEBHOOK, json=data)
            if response.status_code in [200, 204]:
                print(f"[{uid}] Webhook basariyla iletildi.")
            else:
                print(f"[{uid}] Webhook hatasi: {response.status_code}")
        except Exception as e:
            print(f"[{uid}] Webhook gonderim hatasi: {e}")


keep_alive()

if not TOKEN or not TARGET_IDS or not WEBHOOK:
    print("HATA: TOKEN, TARGET_IDS, WEBHOOK degiskenlerini Environment kismina ekleyin.")
else:
    try:
        client = TrackerClient()
        client.run(TOKEN)
    except discord.LoginFailure:
        print("HATA: Hatali token!")
    except Exception as e:
        print(f"Beklenmeyen bir hata olustu: {e}")
