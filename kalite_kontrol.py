import cv2
import os
import glob
import shutil
from pyzbar.pyzbar import decode
from colorama import init, Fore, Style

init(autoreset=True)

def kalite_kontrol_baslat():
    print(f"{Fore.CYAN}{Style.BRIGHT}[*] YAPAY GÖRME (COMPUTER VISION) KALİTE KONTROL MOTORU BAŞLATILDI")
    
    # Firelerin ayrılacağı klasör
    fire_klasoru = 'ayrilan_fireler'
    if os.path.exists(fire_klasoru):
        shutil.rmtree(fire_klasoru)
    os.makedirs(fire_klasoru, exist_ok=True)
    
    # Tüm üretim bandı resimlerini topla
    test_resimleri = glob.glob("uretim_bandi/**/*.png", recursive=True)
    
    if not test_resimleri:
        print(f"{Fore.RED}[!] Uretim bandında resim bulunamadı. Lütfen önce veri_uretici.py dosyasını çalıştırın.")
        return

    toplam_taranan = 0
    hatali_sayisi = 0
    
    print(f"{Fore.YELLOW}[*] {len(test_resimleri)} kutu analiz ediliyor...\n")
    
    for dosya_yolu in test_resimleri:
        img = cv2.imread(dosya_yolu)
        if img is None: continue
        
        toplam_taranan += 1
        
        # 1. Aşama: Görüntü İşleme (Preprocessing)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Keskinliği artırmak için Thresholding (Eşikleme)
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        # 2. Aşama: Barkod Çözümleme (Decoding)
        barkodlar = decode(thresh)
        
        okundu_mu = False
        for barkod in barkodlar:
            barkod_verisi = barkod.data.decode('utf-8')
            if "SUT" in barkod_verisi:
                okundu_mu = True
                
        dosya_adi = os.path.basename(dosya_yolu)
        
        if okundu_mu:
            # Sadece log basıyoruz, ürün bantta devam ediyor
            print(f"{Fore.GREEN}[+] {dosya_adi} -> BAŞARILI (Banttan geçti)")
        else:
            hatali_sayisi += 1
            print(f"{Fore.RED}{Style.BRIGHT}[!] {dosya_adi} -> HATA TESPİT EDİLDİ (Fire ayrılıyor...)")
            
            # Hatalı resmi kırmızı çerçeve ile kaydet (Delil)
            cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 0, 255), 5)
            cv2.putText(img, "HATALI KUTU - FIRE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
            
            hata_kayit_yolu = os.path.join(fire_klasoru, f"FIRE_{dosya_adi}")
            cv2.imwrite(hata_kayit_yolu, img)
            
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== ÜRETİM BANDI KALİTE KONTROL RAPORU ===")
    print(f"{Fore.WHITE}Toplam Taranan Kutu : {toplam_taranan}")
    print(f"{Fore.GREEN}Sağlam Geçen        : {toplam_taranan - hatali_sayisi}")
    print(f"{Fore.RED}Ayrılan Fire        : {hatali_sayisi}")
    print(f"{Fore.CYAN}{'='*42}")

if __name__ == '__main__':
    kalite_kontrol_baslat()
