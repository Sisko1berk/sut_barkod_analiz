import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QSizePolicy
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QFont
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from colorama import Fore

class HMIWindow(QMainWindow):
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.initUI()
        
        # Start update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(self.system.video_gecikme)

    def initUI(self):
        self.setWindowTitle("Sut Fabrikasi - Bant 1 HMI Paneli")
        self.resize(1200, 700)
        
        # Dark Theme QSS
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: None;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton#btn_stop { background-color: #f44336; }
            QPushButton#btn_stop:hover { background-color: #da190b; }
            QPushButton#btn_rewind { background-color: #2196F3; }
            QPushButton#btn_rewind:hover { background-color: #0b7dda; }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        
        # Left Panel (Video and Controls)
        left_layout = QVBoxLayout()
        
        self.video_label = QLabel("Kamera Bekleniyor...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: #1e1e1e; border: 2px solid #555;")
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.video_label, stretch=4)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.btn_play_pause = QPushButton("Durdur / Devam Et")
        self.btn_play_pause.clicked.connect(self.toggle_pause)
        
        self.btn_prev = QPushButton("<< Geri Sar")
        self.btn_prev.clicked.connect(lambda: self.seek(-1))
        
        self.btn_next = QPushButton("Ileri Sar >>")
        self.btn_next.clicked.connect(lambda: self.seek(1))
        
        self.btn_rewind = QPushButton("Basa Sar")
        self.btn_rewind.setObjectName("btn_rewind")
        self.btn_rewind.clicked.connect(lambda: self.seek_to(0))
        
        controls_layout.addWidget(self.btn_rewind)
        controls_layout.addWidget(self.btn_prev)
        controls_layout.addWidget(self.btn_play_pause)
        controls_layout.addWidget(self.btn_next)
        
        left_layout.addLayout(controls_layout, stretch=1)
        main_layout.addLayout(left_layout, stretch=2)
        
        # Right Panel (Stats and Pie Chart)
        right_layout = QVBoxLayout()
        
        self.title_label = QLabel("URETIM ISTATISTIKLERI")
        self.title_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        right_layout.addWidget(self.title_label)
        
        stats_layout = QGridLayout()
        self.lbl_toplam = QLabel("0")
        self.lbl_toplam.setFont(QFont("Arial", 20, QFont.Bold))
        self.lbl_saglam = QLabel("0")
        self.lbl_saglam.setFont(QFont("Arial", 20, QFont.Bold))
        self.lbl_saglam.setStyleSheet("color: #4CAF50;")
        self.lbl_fire = QLabel("0")
        self.lbl_fire.setFont(QFont("Arial", 20, QFont.Bold))
        self.lbl_fire.setStyleSheet("color: #f44336;")
        self.lbl_kurtarilan = QLabel("0")
        self.lbl_kurtarilan.setFont(QFont("Arial", 20, QFont.Bold))
        self.lbl_kurtarilan.setStyleSheet("color: #ffc107;")
        
        stats_layout.addWidget(QLabel("Toplam Kutu:"), 0, 0)
        stats_layout.addWidget(self.lbl_toplam, 0, 1)
        stats_layout.addWidget(QLabel("Saglam (Gecen):"), 1, 0)
        stats_layout.addWidget(self.lbl_saglam, 1, 1)
        stats_layout.addWidget(QLabel("Fire (Hata):"), 2, 0)
        stats_layout.addWidget(self.lbl_fire, 2, 1)
        stats_layout.addWidget(QLabel("Kurtarilan:"), 3, 0)
        stats_layout.addWidget(self.lbl_kurtarilan, 3, 1)
        
        right_layout.addLayout(stats_layout)
        
        # Pie Chart
        self.figure = plt.figure(facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.figure)
        right_layout.addWidget(self.canvas)
        
        main_layout.addLayout(right_layout, stretch=1)
        
    def toggle_pause(self):
        self.system.is_paused = not self.system.is_paused
        
    def seek(self, step):
        self.system.idx += step
        if self.system.idx < 0: self.system.idx = 0
        if self.system.idx >= len(self.system.test_resimleri):
            self.system.idx = max(0, len(self.system.test_resimleri) - 1)
        self.system.is_paused = True
        
    def seek_to(self, idx):
        self.system.idx = idx
        self.system.is_paused = True

    def update_frame(self):
        # 1. Kuyruktan gelenleri al
        while not self.system.urun_kuyrugu.empty():
            yeni_urun = self.system.urun_kuyrugu.get()
            if yeni_urun is None:
                self.system.bant_bitti = True
                self.system.logger.info("Kuyruktan bitis sinyali alindi.")
            else:
                self.system.test_resimleri.append(yeni_urun)
                
        if not self.system.test_resimleri:
            return
            
        if self.system.idx >= len(self.system.test_resimleri):
            self.system.idx = len(self.system.test_resimleri) - 1
            
        dosya_yolu = self.system.test_resimleri[self.system.idx]
        dosya_adi = os.path.basename(dosya_yolu)
        
        # Resmi isle veya onceden islenmisi al
        if self.system.idx in self.system.islenen_kareler:
            img = self.system.islenen_kareler[self.system.idx].copy()
        else:
            img = self.system.isleme_adimi(dosya_yolu, dosya_adi)
            self.update_stats()
            
        if self.system.is_paused:
            if self.system.bant_bitti and self.system.idx == len(self.system.test_resimleri) - 1:
                cv2.putText(img, "BANT SONU (BITTI)", (img.shape[1]//2 - 150, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            else:
                cv2.putText(img, "DURAKLATILDI", (img.shape[1]//2 - 120, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                
        # Görüntüyü OpenCV'den PyQt formatina (RGB -> QImage -> QPixmap) cevir
        rgb_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.video_label.setPixmap(pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        
        # Indexi ilerlet (eger paused degilse)
        if not self.system.is_paused:
            if not self.system.bant_bitti and self.system.idx == len(self.system.test_resimleri) - 1:
                pass
            elif self.system.bant_bitti and self.system.idx == len(self.system.test_resimleri) - 1:
                self.system.is_paused = True
            else:
                self.system.idx += 1
                
    def update_stats(self):
        saglam = self.system.toplam_taranan - self.system.hatali_sayisi - self.system.kurtarilan_sayisi
        fire = self.system.hatali_sayisi
        kurtarilan = self.system.kurtarilan_sayisi
        
        self.lbl_toplam.setText(str(self.system.toplam_taranan))
        self.lbl_saglam.setText(str(saglam))
        self.lbl_fire.setText(str(fire))
        self.lbl_kurtarilan.setText(str(kurtarilan))
        
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#2b2b2b')
        
        labels = ['Saglam', 'Fire', 'Kurtarilan']
        sizes = [saglam, fire, kurtarilan]
        colors = ['#4CAF50', '#f44336', '#ffc107']
        
        # Bos veya sifir olan dilimleri cizdirme
        sizes_filtered = []
        labels_filtered = []
        colors_filtered = []
        for s, l, c in zip(sizes, labels, colors):
            if s > 0:
                sizes_filtered.append(s)
                labels_filtered.append(l)
                colors_filtered.append(c)
        
        if sizes_filtered:
            wedges, texts, autotexts = ax.pie(sizes_filtered, labels=labels_filtered, colors=colors_filtered, 
                                              autopct='%1.1f%%', startangle=90, 
                                              textprops=dict(color="w", fontweight="bold"))
            ax.axis('equal')
            
        self.canvas.draw()
        
    def closeEvent(self, event):
        self.system.logger.info("Arayuz (HMI) kapatiliyor.")
        self.system.rapor_yazdir()
        event.accept()
