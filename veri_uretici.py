import os
import cv2
import numpy as np
from barcode import Code128
from barcode.writer import ImageWriter
import random
import shutil
import json
import time
from logger_kurulum import setup_logger

class SimulationProducer:
    def __init__(self, kuyruk=None):
        self.logger = setup_logger("SimulationProducer")
        self.kuyruk = kuyruk
        self.config = self._get_config()
        self.hedef_klasor = self.config.get('klasor_ayarlari', {}).get('uretim_bandi_klasoru', 'uretim_bandi')
        self.toplam_urun = self.config.get('simulasyon_ayarlari', {}).get('uretilecek_toplam_kutu', 50)
        self.fire_ihtimali = self.config.get('simulasyon_ayarlari', {}).get('fire_ihtimali', 0.3)
        self.uretim_hizi = self.config.get('simulasyon_ayarlari', {}).get('uretim_hizi_saniye', 1.0)
        
    def _get_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config dosyasi okunamadi: {e}")
            return {}

    def start_production(self):
        if os.path.exists(self.hedef_klasor):
            shutil.rmtree(self.hedef_klasor)
        os.makedirs(self.hedef_klasor, exist_ok=True)

        self.logger.info("Gercekci uretim bandi simulasyonu basliyor...")
        
        saglam_sayisi = 0
        hatali_sayisi = 0
        
        for i in range(1, self.toplam_urun + 1):
            try:
                barkod_verisi = f"SUT-2026-08-{i:04d}"
                dosya_adi = f"{self.hedef_klasor}/urun_{i:03d}"
                
                writer = ImageWriter()
                kutu = Code128(barkod_verisi, writer=writer)
                gecici_isim = "temp_barkod"
                kutu.save(gecici_isim)
                
                img = cv2.imread(f"{gecici_isim}.png")
                if img is None: 
                    self.logger.warning(f"{gecici_isim}.png okunamadi, atlaniyor.")
                    continue
                
                is_hatali = random.random() < self.fire_ihtimali
                
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
                    
                if self.kuyruk is not None:
                    self.kuyruk.put(f"{dosya_adi}.png")
                    time.sleep(self.uretim_hizi)
            except Exception as e:
                self.logger.error(f"Urun {i} uretilirken hata olustu: {e}")
                
        if os.path.exists("temp_barkod.png"):
            os.remove("temp_barkod.png")
            
        if self.kuyruk is not None:
            self.kuyruk.put(None)
            
        self.logger.info(f"Uretim Bandi Simulasyonu Tamamlandi! Uretilen: {self.toplam_urun}, Saglam: {saglam_sayisi}, Hatali: {hatali_sayisi}")

def uret_ve_boz(kuyruk=None):
    producer = SimulationProducer(kuyruk)
    producer.start_production()

if __name__ == '__main__':
    producer = SimulationProducer()
    producer.start_production()
