"""Shows the running v6 training's approximate progress live in the terminal."""

import subprocess
import time


TAHMINI_TOPLAM_SANIYE = 27.5 * 60


def sureyi_saniyeye_cevir(deger: str) -> int:
    parcalar = deger.strip().split(":")
    if len(parcalar) == 2:
        dakika, saniye = map(int, parcalar)
        return dakika * 60 + saniye
    saat, dakika, saniye = map(int, parcalar[-3:])
    gun = int(parcalar[0].split("-")[0]) if "-" in parcalar[0] else 0
    return gun * 86400 + saat * 3600 + dakika * 60 + saniye


while True:
    sonuc = subprocess.run(["pgrep", "-f", "finetune_v6.py"], capture_output=True, text=True)
    pidler = [satir for satir in sonuc.stdout.splitlines() if satir.strip()]
    if not pidler:
        print("\rEğitim süreci tamamlandı veya çalışmıyor.                    ")
        break

    pid = pidler[0]
    sure = subprocess.run(["ps", "-p", pid, "-o", "etime="], capture_output=True, text=True).stdout.strip()
    gecen = sureyi_saniyeye_cevir(sure)
    oran = min(gecen / TAHMINI_TOPLAM_SANIYE, 0.99)
    dolu = round(oran * 30)
    cubuk = "█" * dolu + "░" * (30 - dolu)
    kalan = max(0, round(TAHMINI_TOPLAM_SANIYE - gecen))
    print(
        f"\r[{cubuk}] %{oran * 100:5.1f}  geçen {gecen // 60:02d}:{gecen % 60:02d}"
        f"  tahmini kalan {kalan // 60:02d}:{kalan % 60:02d}",
        end="",
        flush=True,
    )
    time.sleep(2)
