import cv2
import os
import glob
import shutil
import time
import random
import json
import numpy as np
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
    video_gecikme = config['cv_ayarlari']['video_oynatma_gecikmesi_ms']
    
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
    
    print(f"{Fore.MAGENTA}[*] HMI İnteraktif Arayüz Başlıyor...")
    print(f"    [SPACE/P] Durdur / Devam Et")
    print(f"    [A] Geri Sar")
    print(f"    [D] İleri Sar")
    print(f"    [1] Başa Sar")
    print(f"    [Q] Çıkış Yap\n")
    
    if os.path.exists(fire_klasoru):
        shutil.rmtree(fire_klasoru)
    os.makedirs(fire_klasoru, exist_ok=True)
    
    test_resimleri = glob.glob(f"{bant_klasoru}/**/*.png", recursive=True)
    
    if not test_resimleri:
        print(f"{Fore.RED}[!] Uretim bandında resim bulunamadı.")
        return

    islenen_kareler = {}
    idx = 0
    is_paused = False
    
    toplam_taranan = 0
    hatali_sayisi = 0
    
    pencere_adi = "Sut Fabrikasi - Bant 1 HMI Paneli"
    cv2.namedWindow(pencere_adi, cv2.WINDOW_NORMAL)
    
    while idx < len(test_resimleri):
        if idx < 0: 
            idx = 0
            
        dosya_yolu = test_resimleri[idx]
        dosya_adi = os.path.basename(dosya_yolu)
        
        if idx in islenen_kareler:
            img_cizilmis = islenen_kareler[idx].copy()
        else:
            baslangic_zamani = time.time()
            img = cv2.imread(dosya_yolu)
            
            if img is not None:
                toplam_taranan += 1
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, cv_thresh, 255, cv2.THRESH_BINARY)
                
                barkodlar = decode(thresh)
                okundu_mu = False
                polygon_points = None
                
                for barkod in barkodlar:
                    barkod_verisi = barkod.data.decode('utf-8')
                    if "SUT" in barkod_verisi:
                        okundu_mu = True
                        polygon_points = barkod.polygon
                        
                bitis_zamani = time.time()
                gercek_isleme_suresi_ms = (bitis_zamani - baslangic_zamani) * 1000
                isleme_suresi = round(gercek_isleme_suresi_ms + random.uniform(15.0, 45.0), 2)
                fps = int(1000 / (isleme_suresi if isleme_suresi > 0 else 1))
                
                cv2.putText(img, f"FPS: {fps}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(img, f"KAMERA: HAT-01", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

                if okundu_mu:
                    print(f"{Fore.GREEN}[+] {dosya_adi} -> BAŞARILI (Banttan geçti)")
                    guven = round(random.uniform(bas_min, bas_max), 2)
                    veritabani_motoru.log_ekle(dosya_adi, isleme_suresi, "GECTI", hata_kodu="YOK", guven_skoru=guven)
                    
                    if polygon_points:
                        pts = np.array(polygon_points, np.int32).reshape((-1, 1, 2))
                        cv2.polylines(img, [pts], True, (0, 255, 0), cv_kalinlik)
                    else:
                        cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 255, 0), cv_kalinlik)
                        
                    cv2.putText(img, "DURUM: GECTI", (img.shape[1]-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                else:
                    hatali_sayisi += 1
                    print(f"{Fore.RED}{Style.BRIGHT}[!] {dosya_adi} -> HATA TESPİT EDİLDİ (Fire ayrılıyor...)")
                    guven = round(random.uniform(hat_min, hat_max), 2)
                    veritabani_motoru.log_ekle(dosya_adi, isleme_suresi, "FIRE", hata_kodu="ERR_BARCODE_UNREADABLE", guven_skoru=guven)
                    
                    cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 0, 255), cv_kalinlik)
                    cv2.putText(img, "DURUM: FIRE (HATALI)", (img.shape[1]-250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-250, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(img, "AYRILIYOR...", (img.shape[1]//2 - 100, img.shape[0]//2), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 3)
                    
                    hata_kayit_yolu = os.path.join(fire_klasoru, f"FIRE_{dosya_adi}")
                    cv2.imwrite(hata_kayit_yolu, img)
            
            islenen_kareler[idx] = img.copy()
            img_cizilmis = islenen_kareler[idx].copy()
            
        if is_paused:
            if idx == len(test_resimleri) - 1:
                cv2.putText(img_cizilmis, "BANT SONU (BITTI)", (img_cizilmis.shape[1]//2 - 150, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            else:
                cv2.putText(img_cizilmis, "DURAKLATILDI", (img_cizilmis.shape[1]//2 - 120, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
        cv2.imshow(pencere_adi, img_cizilmis)
        
        bekleme_suresi = 50 if is_paused else video_gecikme
        key = cv2.waitKey(bekleme_suresi) & 0xFF
        
        if cv2.getWindowProperty(pencere_adi, cv2.WND_PROP_VISIBLE) < 1:
            print(f"\n{Fore.YELLOW}[!] Pencere 'X' butonundan manuel olarak kapatildi. Çıkış yapılıyor...")
            break
        
        if key == ord('q'):
            break
        elif key == ord('p') or key == ord(' '):
            is_paused = not is_paused
        elif key == ord('a'):
            idx -= 1
            is_paused = True 
        elif key == ord('d'):
            if idx < len(test_resimleri) - 1:
                idx += 1
            is_paused = True 
        elif key == ord('1'):
            idx = 0
            is_paused = True
        else:
            if not is_paused:
                if idx == len(test_resimleri) - 1:
                    is_paused = True
                else:
                    idx += 1
                
    cv2.destroyAllWindows()
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== ÜRETİM BANDI KALİTE KONTROL RAPORU ===")
    print(f"{Fore.WHITE}Toplam Taranan Kutu : {toplam_taranan}")
    print(f"{Fore.GREEN}Sağlam Geçen        : {toplam_taranan - hatali_sayisi}")
    print(f"{Fore.RED}Ayrılan Fire        : {hatali_sayisi}")
    print(f"{Fore.CYAN}{'='*42}")
    print(f"{Fore.GREEN}[*] İzleme tamamlandı. Program güvenle kapatıldı.")

if __name__ == '__main__':
    kalite_kontrol_baslat()
