import sqlite3
import datetime

DB_ISMI = "kalite_raporlari.db"

def db_kurulum():
    conn = sqlite3.connect(DB_ISMI)
    cursor = conn.cursor()
    # DROP TABLE satırını kaldırdık! Artık geçmiş veriler asla silinmeyecek.
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

def log_ekle(urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu="YOK", guven_skoru=99.9, aciklama="-"):
    conn = sqlite3.connect(DB_ISMI)
    cursor = conn.cursor()
    su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    saat = datetime.datetime.now().hour
    if 8 <= saat < 16: vardiya = "GÜNDÜZ_08-16"
    elif 16 <= saat < 24: vardiya = "AKŞAM_16-24"
    else: vardiya = "GECE_24-08"
    
    kamera_id = "KAMERA_HAT-01_BANT-A"
    
    cursor.execute('''
        INSERT INTO uretim_loglari (islem_tarihi, vardiya_kodu, kamera_id, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu, algoritma_guven_skoru, aciklama)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (su_an, vardiya, kamera_id, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu, guven_skoru, aciklama))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    db_kurulum()
