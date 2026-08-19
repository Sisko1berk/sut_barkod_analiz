import os
import cv2
import numpy as np
from barcode import Code128
from barcode.writer import ImageWriter
import random
import shutil
import json

def uret_ve_boz():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    hedef_klasor = config['klasor_ayarlari']['uretim_bandi_klasoru']
    toplam_urun = config['simulasyon_ayarlari']['uretilecek_toplam_kutu']
    fire_ihtimali = config['simulasyon_ayarlari']['fire_ihtimali']
    
    if os.path.exists(hedef_klasor):
        shutil.rmtree(hedef_klasor)
    os.makedirs(hedef_klasor, exist_ok=True)

    print(f"[*] Gerçekçi üretim bandı simülasyonu başlıyor...")
    print(f"[*] Tüm ürünler '{hedef_klasor}' klasörüne isimsiz (generic) olarak aktarılacak.")
    
    saglam_sayisi = 0
    hatali_sayisi = 0
    
    for i in range(1, toplam_urun + 1):
        barkod_verisi = f"SUT-2026-08-{i:04d}"
        dosya_adi = f"{hedef_klasor}/urun_{i:03d}"
        
        writer = ImageWriter()
        kutu = Code128(barkod_verisi, writer=writer)
        gecici_isim = "temp_barkod"
        kutu.save(gecici_isim)
        
        img = cv2.imread(f"{gecici_isim}.png")
        if img is None: continue
        
        is_hatali = random.random() < fire_ihtimali
        
        if is_hatali:
            hatali_sayisi += 1
            hata_tipi = random.choice(['blur', 'dark', 'scratch'])
            bozuk_img = img.copy()
            
            if hata_tipi == 'blur':
                kernel = np.zeros((15, 15))
                kernel[7, :] = np.ones(15) / 15
                bozuk_img = cv2.filter2D(bozuk_img, -1, kernel)
            elif hata_tipi == 'dark':
                bozuk_img = cv2.convertScaleAbs(bozuk_img, alpha=0.3, beta=0)
            elif hata_tipi == 'scratch':
                cv2.line(bozuk_img, (0, bozuk_img.shape[0]//2), (bozuk_img.shape[1], bozuk_img.shape[0]//2), (255, 255, 255), 15)
            
            cv2.imwrite(f"{dosya_adi}.png", bozuk_img)
        else:
            saglam_sayisi += 1
            cv2.imwrite(f"{dosya_adi}.png", img)
            
    if os.path.exists("temp_barkod.png"):
        os.remove("temp_barkod.png")
        
    print(f"[+] Üretim Bandı Simülasyonu Tamamlandı!")
    print(f"    Üretilen Toplam Kutu : {toplam_urun}")
    print(f"    Sağlam Kutu          : {saglam_sayisi}")
    print(f"    Gizli Hatalı Kutu    : {hatali_sayisi}")
    
if __name__ == '__main__':
    uret_ve_boz()
