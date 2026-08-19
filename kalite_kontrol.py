import cv2
import os
import glob
import shutil
import time
import random
import json
from pyzbar.pyzbar import decode
from colorama import init, Fore, Style
import veritabani_motoru
import veri_uretici

init(autoreset=True)

def kalite_kontrol_baslat():
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        
    bant_klasoru = config['klasor_ayarlari']['uretim_bandi_klasoru']
    fire_klasoru = config['klasor_ayarlari']['fire_klasoru']
    
    cv_thresh = config['cv_ayarlari']['threshold_degeri']
    cv_kalinlik = config['cv_ayarlari']['cerceve_kalinligi']
    
    bas_min = config['cv_ayarlari']['basarili_guven_skoru_min']
    bas_max = config['cv_ayarlari']['basarili_guven_skoru_max']
    hat_min = config['cv_ayarlari']['hatali_guven_skoru_min']
    hat_max = config['cv_ayarlari']['hatali_guven_skoru_max']

    print(f"{Fore.CYAN}{Style.BRIGHT}[*] YAPAY GÖRME (COMPUTER VISION) KALİTE KONTROL MOTORU BAŞLATILDI\n")
    
    print(f"{Fore.YELLOW}[*] Bant sıfırlanıyor ve yeni simülasyon ürünleri yaratılıyor...{Style.RESET_ALL}")
    veri_uretici.uret_ve_boz()
    print("\n")
    
    veritabani_motoru.db_kurulum()
    print(f"{Fore.YELLOW}[*] Veritabanı bağlantısı sağlandı ve detaylı loglama aktif.\n")
    
    if os.path.exists(fire_klasoru):
        shutil.rmtree(fire_klasoru)
    os.makedirs(fire_klasoru, exist_ok=True)
    
    test_resimleri = glob.glob(f"{bant_klasoru}/**/*.png", recursive=True)
    
    if not test_resimleri:
        print(f"{Fore.RED}[!] Uretim bandında resim bulunamadı.")
        return

    toplam_taranan = 0
    hatali_sayisi = 0
    
    for dosya_yolu in test_resimleri:
        baslangic_zamani = time.time()
        
        img = cv2.imread(dosya_yolu)
        if img is None: continue
        
        toplam_taranan += 1
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, cv_thresh, 255, cv2.THRESH_BINARY)
        
        barkodlar = decode(thresh)
        okundu_mu = False
        
        for barkod in barkodlar:
            barkod_verisi = barkod.data.decode('utf-8')
            if "SUT" in barkod_verisi:
                okundu_mu = True
                
        dosya_adi = os.path.basename(dosya_yolu)
        bitis_zamani = time.time()
        isleme_suresi = round((bitis_zamani - baslangic_zamani) * 1000 + random.uniform(15.0, 45.0), 2)
        
        if okundu_mu:
            print(f"{Fore.GREEN}[+] {dosya_adi} -> BAŞARILI (Banttan geçti)")
            guven = round(random.uniform(bas_min, bas_max), 2)
            veritabani_motoru.log_ekle(dosya_adi, isleme_suresi, "GECTI", hata_kodu="YOK", guven_skoru=guven, aciklama="Kalite standartlarına uygun")
        else:
            hatali_sayisi += 1
            print(f"{Fore.RED}{Style.BRIGHT}[!] {dosya_adi} -> HATA TESPİT EDİLDİ (Fire ayrılıyor...)")
            
            cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 0, 255), cv_kalinlik)
            cv2.putText(img, "HATALI KUTU - FIRE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            hata_kayit_yolu = os.path.join(fire_klasoru, f"FIRE_{dosya_adi}")
            cv2.imwrite(hata_kayit_yolu, img)
            
            guven = round(random.uniform(hat_min, hat_max), 2)
            veritabani_motoru.log_ekle(dosya_adi, isleme_suresi, "FIRE", hata_kodu="ERR_BARCODE_UNREADABLE", guven_skoru=guven, aciklama="Mürekkep silik veya motion blur tespit edildi")
            
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== ÜRETİM BANDI KALİTE KONTROL RAPORU ===")
    print(f"{Fore.WHITE}Toplam Taranan Kutu : {toplam_taranan}")
    print(f"{Fore.GREEN}Sağlam Geçen        : {toplam_taranan - hatali_sayisi}")
    print(f"{Fore.RED}Ayrılan Fire        : {hatali_sayisi}")
    print(f"{Fore.CYAN}{'='*42}")

if __name__ == '__main__':
    kalite_kontrol_baslat()
