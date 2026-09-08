import sqlite3
import datetime
import json
from logger_kurulum import setup_logger

class DatabaseManager:
    def __init__(self):
        self.logger = setup_logger("DatabaseManager")
        self.config = self._get_config()
        self.db_ismi = self.config.get('veritabani_ayarlari', {}).get('db_ismi', 'kalite_raporlari.db')
        self.kamera_id = self.config.get('veritabani_ayarlari', {}).get('kamera_id', 'KAMERA_HAT-01')
        self.kurulum()
        
    def _get_config(self):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config dosyasi okunamadi: {e}")
            return {}

    def kurulum(self):
        try:
            conn = sqlite3.connect(self.db_ismi)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS uretim_loglari (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    islem_tarihi TEXT,
                    vardiya_kodu TEXT,
                    kamera_id TEXT,
                    urun_barkodu TEXT,
                    isleme_suresi_ms REAL,
                    kalite_durumu TEXT,
                    hata_kodu TEXT,
                    algoritma_guven_skoru REAL,
                    aciklama TEXT
                )
            ''')
            conn.commit()
            conn.close()
            self.logger.info("Veritabani baglantisi saglandi ve tablolar hazir.")
        except Exception as e:
            self.logger.error(f"Veritabani kurulumunda hata: {e}")

    def log_ekle(self, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu="YOK", guven_skoru=99.9, aciklama="-"):
        try:
            conn = sqlite3.connect(self.db_ismi)
            cursor = conn.cursor()
            su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            saat = datetime.datetime.now().hour
            if 8 <= saat < 16: vardiya = "GUNDUZ_08-16"
            elif 16 <= saat < 24: vardiya = "AKSAM_16-24"
            else: vardiya = "GECE_24-08"
            
            cursor.execute('''
                INSERT INTO uretim_loglari (islem_tarihi, vardiya_kodu, kamera_id, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu, algoritma_guven_skoru, aciklama)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (su_an, vardiya, self.kamera_id, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu, guven_skoru, aciklama))
            
            conn.commit()
            conn.close()
            self.logger.debug(f"DB Log eklendi: {urun_barkodu} - {kalite_durumu}")
        except Exception as e:
            self.logger.error(f"Log eklenirken veritabani hatasi: {e}")

if __name__ == '__main__':
    db = DatabaseManager()
