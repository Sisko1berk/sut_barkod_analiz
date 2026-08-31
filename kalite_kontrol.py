import cv2
import os
import glob
import shutil
import time
import random
import json
import numpy as np
import threading
import queue
from pyzbar.pyzbar import decode
from colorama import init, Fore, Style
from veritabani_motoru import DatabaseManager
from veri_uretici import SimulationProducer
from logger_kurulum import setup_logger

init(autoreset=True)

class QualityControlSystem:
    def __init__(self):
        self.logger = setup_logger("QualityControlSystem")
        self.config = self._get_config()
        self.db = DatabaseManager()
        
        # Klasörler
        self.bant_klasoru = self.config.get('klasor_ayarlari', {}).get('uretim_bandi_klasoru', 'uretim_bandi')
        self.fire_klasoru = self.config.get('klasor_ayarlari', {}).get('fire_klasoru', 'ayrilan_fireler')
        
        # CV Ayarları
        cv_ayarlar = self.config.get('cv_ayarlari', {})
        self.cv_thresh = cv_ayarlar.get('threshold_degeri', 100)
        self.cv_kalinlik = cv_ayarlar.get('cerceve_kalinligi', 5)
        self.video_gecikme = cv_ayarlar.get('video_oynatma_gecikmesi_ms', 200)
        
        self.bas_min = cv_ayarlar.get('basarili_guven_skoru_min', 98.5)
        self.bas_max = cv_ayarlar.get('basarili_guven_skoru_max', 99.9)
        self.hat_min = cv_ayarlar.get('hatali_guven_skoru_min', 12.0)
        self.hat_max = cv_ayarlar.get('hatali_guven_skoru_max', 45.0)
        
        self.urun_kuyrugu = queue.Queue()
        self.test_resimleri = []
        self.islenen_kareler = {}
        self.idx = 0
        self.is_paused = False
        self.bant_bitti = False
        self.toplam_taranan = 0
        self.hatali_sayisi = 0
        self.pencere_adi = "Sut Fabrikasi - Bant 1 HMI Paneli"

    def _get_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config okunamadı: {e}")
            return {}
            
    def baslat(self):
        self.logger.info("YAPAY GÖRME KALİTE KONTROL MOTORU BAŞLATILDI")
        
        print(f"{Fore.CYAN}{Style.BRIGHT}[*] YAPAY GÖRME KALİTE KONTROL MOTORU BAŞLATILDI\n")
        print(f"{Fore.YELLOW}[*] Bant sıfırlanıyor ve simülasyon arka planda başlatılıyor...{Style.RESET_ALL}")
        
        # Fire klasörünü temizle
        if os.path.exists(self.fire_klasoru):
            shutil.rmtree(self.fire_klasoru)
        os.makedirs(self.fire_klasoru, exist_ok=True)
        
        # Üretici Thread'ini Başlat
        producer = SimulationProducer(self.urun_kuyrugu)
        uretici_thread = threading.Thread(target=producer.start_production)
        uretici_thread.daemon = True
        uretici_thread.start()
        self.logger.debug("Üretici thread başlatıldı.")
        
        print(f"{Fore.MAGENTA}[*] HMI İnteraktif Arayüz Başlıyor...")
        print(f"    [SPACE/P] Durdur / Devam Et")
        print(f"    [A] Geri Sar")
        print(f"    [D] İleri Sar")
        print(f"    [1] Başa Sar")
        print(f"    [Q] Çıkış Yap\n")
        
        cv2.namedWindow(self.pencere_adi, cv2.WINDOW_NORMAL)
        
        self.ana_dongu()
        
    def ana_dongu(self):
        while True:
            # Kuyruktan gelenleri al
            while not self.urun_kuyrugu.empty():
                yeni_urun = self.urun_kuyrugu.get()
                if yeni_urun is None:
                    self.bant_bitti = True
                    self.logger.info("Kuyruktan bitiş (None) sinyali alındı.")
                else:
                    self.test_resimleri.append(yeni_urun)
                    
            if self.idx < 0: 
                self.idx = 0
                
            if not self.test_resimleri:
                bekleme_resmi = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(bekleme_resmi, "BANT BASLATILIYOR...", (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                cv2.imshow(self.pencere_adi, bekleme_resmi)
                
                key = cv2.waitKey(100) & 0xFF
                if cv2.getWindowProperty(self.pencere_adi, cv2.WND_PROP_VISIBLE) < 1 or key == ord('q'):
                    break
                continue
                
            if self.idx >= len(self.test_resimleri):
                self.idx = len(self.test_resimleri) - 1
                
            dosya_yolu = self.test_resimleri[self.idx]
            dosya_adi = os.path.basename(dosya_yolu)
            
            if self.idx in self.islenen_kareler:
                img_cizilmis = self.islenen_kareler[self.idx].copy()
            else:
                img_cizilmis = self.isleme_adimi(dosya_yolu, dosya_adi)
                
            if self.is_paused:
                if self.bant_bitti and self.idx == len(self.test_resimleri) - 1:
                    cv2.putText(img_cizilmis, "BANT SONU (BITTI)", (img_cizilmis.shape[1]//2 - 150, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                else:
                    cv2.putText(img_cizilmis, "DURAKLATILDI", (img_cizilmis.shape[1]//2 - 120, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
            cv2.imshow(self.pencere_adi, img_cizilmis)
            
            if self.klavye_dinle():
                break
                
        cv2.destroyAllWindows()
        self.rapor_yazdir()
        
    def isleme_adimi(self, dosya_yolu, dosya_adi):
        baslangic_zamani = time.time()
        img = cv2.imread(dosya_yolu)
        
        if img is None:
            self.logger.warning(f"Okunamayan resim atlandı: {dosya_yolu}")
            # return empty image so it doesn't crash
            return np.zeros((480, 640, 3), dtype=np.uint8)
            
        self.toplam_taranan += 1
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, self.cv_thresh, 255, cv2.THRESH_BINARY)
        
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
            guven = round(random.uniform(self.bas_min, self.bas_max), 2)
            self.db.log_ekle(dosya_adi, isleme_suresi, "GECTI", hata_kodu="YOK", guven_skoru=guven)
            
            if polygon_points:
                pts = np.array(polygon_points, np.int32).reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, (0, 255, 0), self.cv_kalinlik)
            else:
                cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 255, 0), self.cv_kalinlik)
                
            cv2.putText(img, "DURUM: GECTI", (img.shape[1]-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            self.logger.debug(f"İşlendi (Geçti): {dosya_adi}")
        else:
            self.hatali_sayisi += 1
            print(f"{Fore.RED}{Style.BRIGHT}[!] {dosya_adi} -> HATA TESPİT EDİLDİ (Fire ayrılıyor...)")
            guven = round(random.uniform(self.hat_min, self.hat_max), 2)
            self.db.log_ekle(dosya_adi, isleme_suresi, "FIRE", hata_kodu="ERR_BARCODE_UNREADABLE", guven_skoru=guven)
            
            cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 0, 255), self.cv_kalinlik)
            cv2.putText(img, "DURUM: FIRE (HATALI)", (img.shape[1]-250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-250, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(img, "AYRILIYOR...", (img.shape[1]//2 - 100, img.shape[0]//2), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 3)
            
            hata_kayit_yolu = os.path.join(self.fire_klasoru, f"FIRE_{dosya_adi}")
            cv2.imwrite(hata_kayit_yolu, img)
            self.logger.warning(f"Fire ayrıldı: {dosya_adi}")
    
        self.islenen_kareler[self.idx] = img.copy()
        return self.islenen_kareler[self.idx].copy()
        
    def klavye_dinle(self):
        bekleme_suresi = 50 if self.is_paused else self.video_gecikme
        key = cv2.waitKey(bekleme_suresi) & 0xFF
        
        if cv2.getWindowProperty(self.pencere_adi, cv2.WND_PROP_VISIBLE) < 1:
            self.logger.warning("Pencere manuel kapatıldı.")
            print(f"\n{Fore.YELLOW}[!] Pencere 'X' butonundan manuel olarak kapatildi. Çıkış yapılıyor...")
            return True # Çıkış
            
        if key == ord('q'):
            self.logger.info("'Q' ile çıkış yapıldı.")
            return True
        elif key == ord('p') or key == ord(' '):
            self.is_paused = not self.is_paused
            self.logger.debug(f"Duraklatma değişti: {self.is_paused}")
        elif key == ord('a'):
            self.idx -= 1
            self.is_paused = True 
        elif key == ord('d'):
            if self.idx < len(self.test_resimleri) - 1:
                self.idx += 1
            self.is_paused = True 
        elif key == ord('1'):
            self.idx = 0
            self.is_paused = True
        else:
            if not self.is_paused:
                if not self.bant_bitti and self.idx == len(self.test_resimleri) - 1:
                    pass
                elif self.bant_bitti and self.idx == len(self.test_resimleri) - 1:
                    self.is_paused = True
                else:
                    self.idx += 1
        return False
        
    def rapor_yazdir(self):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== ÜRETİM BANDI KALİTE KONTROL RAPORU ===")
        print(f"{Fore.WHITE}Toplam Taranan Kutu : {self.toplam_taranan}")
        print(f"{Fore.GREEN}Sağlam Geçen        : {self.toplam_taranan - self.hatali_sayisi}")
        print(f"{Fore.RED}Ayrılan Fire        : {self.hatali_sayisi}")
        print(f"{Fore.CYAN}{'='*42}")
        print(f"{Fore.GREEN}[*] İzleme tamamlandı. Program güvenle kapatıldı.")
        self.logger.info(f"Sistem kapandı. Taranan: {self.toplam_taranan}, Fire: {self.hatali_sayisi}")

# Geriye dönük uyumluluk
def kalite_kontrol_baslat():
    system = QualityControlSystem()
    system.baslat()

if __name__ == '__main__':
    kalite_kontrol_baslat()
