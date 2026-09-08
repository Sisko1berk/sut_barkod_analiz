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
        
        self.bant_klasoru = self.config.get('klasor_ayarlari', {}).get('uretim_bandi_klasoru', 'uretim_bandi')
        self.fire_klasoru = self.config.get('klasor_ayarlari', {}).get('fire_klasoru', 'ayrilan_fireler')
        self.kurtarilanlar_klasoru = self.config.get('klasor_ayarlari', {}).get('kurtarilanlar_klasoru', 'kurtarilan_urunler')
        
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
        self.kurtarilan_sayisi = 0
        self.kurtarilan_dosyalar = []
        self.pencere_adi = "Sut Fabrikasi - Bant 1 HMI Paneli"

    def _get_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config okunamadi: {e}")
            return {}
            
    def baslat(self):
        self.logger.info("YAPAY GORME KALITE KONTROL MOTORU BASLATILDI")
        
        print(f"{Fore.CYAN}{Style.BRIGHT}[*] YAPAY GORME KALITE KONTROL MOTORU BASLATILDI\n")
        print(f"{Fore.YELLOW}[*] Bant sifirlaniyor ve simulasyon arka planda baslatiliyor...{Style.RESET_ALL}")
        
        if os.path.exists(self.fire_klasoru):
            shutil.rmtree(self.fire_klasoru)
        os.makedirs(self.fire_klasoru, exist_ok=True)
        
        if os.path.exists(self.kurtarilanlar_klasoru):
            shutil.rmtree(self.kurtarilanlar_klasoru)
        os.makedirs(self.kurtarilanlar_klasoru, exist_ok=True)
        
        producer = SimulationProducer(self.urun_kuyrugu)
        uretici_thread = threading.Thread(target=producer.start_production)
        uretici_thread.daemon = True
        uretici_thread.start()
        self.logger.debug("Uretici thread baslatildi.")
        
        print(f"{Fore.MAGENTA}[*] HMI Interaktif Arayuz Basliyor...")
        
        from PyQt5.QtWidgets import QApplication
        from arayuz_gui import HMIWindow
        import sys
        
        # Eger QApplication daha once baslatilmadiysa baslat (ornek: Jupyter vb icin onlem)
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
            
        self.hmi = HMIWindow(self)
        self.hmi.show()
        
        sys.exit(app.exec_())
        
        
    def isleme_adimi(self, dosya_yolu, dosya_adi):
        baslangic_zamani = time.time()
        img = cv2.imread(dosya_yolu)
        
        if img is None:
            self.logger.warning(f"Okunamayan resim atlandi: {dosya_yolu}")
            return np.zeros((480, 640, 3), dtype=np.uint8)
            
        orijinal_img = img.copy()
            
        self.toplam_taranan += 1
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, self.cv_thresh, 255, cv2.THRESH_BINARY)
        
        barkodlar = decode(thresh)
        okundu_mu = False
        kurtarma_yontemi = ""
        polygon_points = None
        
        for barkod in barkodlar:
            barkod_verisi = barkod.data.decode('utf-8')
            if "SUT" in barkod_verisi:
                okundu_mu = True
                polygon_points = barkod.polygon
                break
                
        if not okundu_mu:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl1 = clahe.apply(gray)
            barkodlar_clahe = decode(cl1) 
            for barkod in barkodlar_clahe:
                barkod_verisi = barkod.data.decode('utf-8')
                if "SUT" in barkod_verisi:
                    okundu_mu = True
                    kurtarma_yontemi = "CLAHE"
                    polygon_points = barkod.polygon
                    break
                    
        if not okundu_mu:
            kernel = np.ones((5,1),np.uint8)
            opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            barkodlar_morph = decode(opened)
            
            if not barkodlar_morph:
                barkodlar_morph = decode(gray) 
                
            for barkod in barkodlar_morph:
                barkod_verisi = barkod.data.decode('utf-8')
                if "SUT" in barkod_verisi:
                    okundu_mu = True
                    kurtarma_yontemi = "MORFOLOJI"
                    polygon_points = barkod.polygon
                    break
                
        bitis_zamani = time.time()
        gercek_isleme_suresi_ms = (bitis_zamani - baslangic_zamani) * 1000
        isleme_suresi = round(gercek_isleme_suresi_ms + random.uniform(15.0, 45.0), 2)
        fps = int(1000 / (isleme_suresi if isleme_suresi > 0 else 1))
        
        cv2.putText(img, f"FPS: {fps}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(img, f"KAMERA: HAT-01", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        if okundu_mu:
            if kurtarma_yontemi == "":
                print(f"{Fore.GREEN}[+] {dosya_adi} -> BASARILI (Banttan gecti)")
                guven = round(random.uniform(self.bas_min, self.bas_max), 2)
                self.db.log_ekle(dosya_adi, isleme_suresi, "GECTI", hata_kodu="YOK", guven_skoru=guven)
                
                if polygon_points:
                    pts = np.array(polygon_points, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(img, [pts], True, (0, 255, 0), self.cv_kalinlik)
                else:
                    cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 255, 0), self.cv_kalinlik)
                    
                cv2.putText(img, "DURUM: GECTI", (img.shape[1]-200, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-200, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                self.logger.debug(f"Islendi (Gecti): {dosya_adi}")
            else:
                self.kurtarilan_sayisi += 1
                self.kurtarilan_dosyalar.append(dosya_adi)
                print(f"{Fore.YELLOW}[*] {dosya_adi} -> KURTARILDI ({kurtarma_yontemi})")
                guven = round(random.uniform(self.bas_min - 5, self.bas_max - 2), 2)
                self.db.log_ekle(dosya_adi, isleme_suresi, "GECTI", hata_kodu="YOK", guven_skoru=guven, aciklama=f"KURTARILDI - {kurtarma_yontemi}")
                
                if polygon_points:
                    pts = np.array(polygon_points, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(img, [pts], True, (255, 255, 0), self.cv_kalinlik)
                else:
                    cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (255, 255, 0), self.cv_kalinlik)
                    
                cv2.putText(img, "DURUM: KURTARILDI", (img.shape[1]-300, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(img, f"YONTEM: {kurtarma_yontemi}", (img.shape[1]-300, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-300, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                kurtarilan_kayit_yolu = os.path.join(self.kurtarilanlar_klasoru, f"KURTARILDI_{dosya_adi}")
                cv2.imwrite(kurtarilan_kayit_yolu, img)
                
                # Kurtarilan urunun orjinal fire halini de kaydet
                orijinal_fire_yolu = os.path.join(self.fire_klasoru, f"FIRE_ONCESI_{dosya_adi}")
                cv2.imwrite(orijinal_fire_yolu, orijinal_img)
                
                self.logger.info(f"Kurtarildi ({kurtarma_yontemi}): {dosya_adi}")
        else:
            self.hatali_sayisi += 1
            print(f"{Fore.RED}{Style.BRIGHT}[!] {dosya_adi} -> HATA TESPIT EDILDI (Fire ayriliyor...)")
            guven = round(random.uniform(self.hat_min, self.hat_max), 2)
            self.db.log_ekle(dosya_adi, isleme_suresi, "FIRE", hata_kodu="ERR_BARCODE_UNREADABLE", guven_skoru=guven)
            
            cv2.rectangle(img, (10, 10), (img.shape[1]-10, img.shape[0]-10), (0, 0, 255), self.cv_kalinlik)
            cv2.putText(img, "DURUM: FIRE (HATALI)", (img.shape[1]-250, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(img, f"GUVEN: %{guven}", (img.shape[1]-250, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(img, "AYRILIYOR...", (img.shape[1]//2 - 100, img.shape[0]//2), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 255), 3)
            
            hata_kayit_yolu = os.path.join(self.fire_klasoru, f"FIRE_{dosya_adi}")
            cv2.imwrite(hata_kayit_yolu, img)
            self.logger.warning(f"Fire ayrildi: {dosya_adi}")
    
        self.islenen_kareler[self.idx] = img.copy()
        return self.islenen_kareler[self.idx].copy()
        

        
    def rapor_yazdir(self):
        print(f"\n{Fore.CYAN}{Style.BRIGHT}=== URETIM BANDI KALITE KONTROL RAPORU ===")
        print(f"{Fore.WHITE}Toplam Taranan Kutu : {self.toplam_taranan}")
        print(f"{Fore.GREEN}Saglam Gecen        : {self.toplam_taranan - self.hatali_sayisi - self.kurtarilan_sayisi}")
        print(f"{Fore.YELLOW}Kurtarilan Urun     : {self.kurtarilan_sayisi}")
        print(f"{Fore.RED}Ayrilan Fire        : {self.hatali_sayisi}")
        
        if self.kurtarilan_dosyalar:
            print(f"{Fore.CYAN}{'-'*42}")
            print(f"{Fore.YELLOW}Kurtarilan Dosyalar:")
            for d in self.kurtarilan_dosyalar:
                print(f"  - {d}")
                
        print(f"{Fore.CYAN}{'='*42}")
        print(f"{Fore.GREEN}[*] Izleme tamamlandi. Program guvenle kapatildi.")
        self.logger.info(f"Sistem kapandi. Taranan: {self.toplam_taranan}, Kurtarilan: {self.kurtarilan_sayisi}, Fire: {self.hatali_sayisi}")

def kalite_kontrol_baslat():
    system = QualityControlSystem()
    system.baslat()

if __name__ == '__main__':
    kalite_kontrol_baslat()
