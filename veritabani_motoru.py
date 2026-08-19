import sqlite3
import datetime
import json

def get_config():
    with open('config.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def db_kurulum():
    config = get_config()
    db_ismi = config['veritabani_ayarlari']['db_ismi']
    
    conn = sqlite3.connect(db_ismi)
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

def log_ekle(urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu="YOK", guven_skoru=99.9, aciklama="-"):
    config = get_config()
    db_ismi = config['veritabani_ayarlari']['db_ismi']
    kamera_id = config['veritabani_ayarlari']['kamera_id']
    
    conn = sqlite3.connect(db_ismi)
    cursor = conn.cursor()
    su_an = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    saat = datetime.datetime.now().hour
    if 8 <= saat < 16: vardiya = "GÜNDÜZ_08-16"
    elif 16 <= saat < 24: vardiya = "AKŞAM_16-24"
    else: vardiya = "GECE_24-08"
    
    cursor.execute('''
        INSERT INTO uretim_loglari (islem_tarihi, vardiya_kodu, kamera_id, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu, algoritma_guven_skoru, aciklama)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (su_an, vardiya, kamera_id, urun_barkodu, isleme_suresi_ms, kalite_durumu, hata_kodu, guven_skoru, aciklama))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    db_kurulum()
