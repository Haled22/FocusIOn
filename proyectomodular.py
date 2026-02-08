import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel,QComboBox,QDesktopWidget
from PyQt5.QtCore import *
from pynput import mouse
import pyautogui
import threading
import time


tolerancia_max =100
tolerancia_elegida =0


class timerThread(QObject):
    update_timer = pyqtSignal(str)
    finished = pyqtSignal()
    
    def run(self):
        qtime = QTime(0, 0, 0)
        #tolerancia_elegida*60, el 5 es hardcodeado para pruebas
        for x in range(5):
            qtime = qtime.addSecs(1)
            self.update_timer.emit(qtime.toString("hh:mm:ss"))
            time.sleep(1)    
        self.finished.emit()
             
class Advertencia(QWidget):
    def __init__(self, target_window):
        super().__init__()
        window = target_window[0]
        x = window.left
        y = window.top
        width = window.width
        height = window.height
        self.resize(width, height)
        self.move(x,y) 
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.5)
                
class FocusIOn(QWidget):
    start_timer_signal = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.tarea_iniciada = False
        self.tarea = ""
        self.timer_thread = QThread()
        self.timer_worker = timerThread()
        self.clicks_count =0
        self.timer_iniciado = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        
        
        self.start_timer_signal.connect(self.start_timer_thread)
        self.listener_thread = threading.Thread(target=self.start_listener, daemon=True)
        self.listener_thread.start()

        width, height = 200, 400
        self.resize(width, height)
        screen = QDesktopWidget().availableGeometry()
        x = screen.width() - width
        y = screen.height()- height
        self.move(x,y)

           
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, width, height)
        self.background.setStyleSheet("""
            QLabel {
              
                background-image: url(pretty.jpg);
                background-position: center;
                background-repeat: no-repeat;
                background-size: cover;
            }
        """)
        

        self.b_cerrar = QPushButton("X", self)
        self.b_cerrar.setGeometry(170, 0, 30, 30)
        self.b_cerrar.raise_()
        self.b_cerrar.clicked.connect(self.closeEvent)

        
        self.instrucciones = QLabel("De clic a alguna window para seleccionar el area de trabajo",self)
        self.instrucciones.setGeometry(40, 10, 120, 120)
        self.instrucciones.setAlignment(Qt.AlignCenter)
        self.instrucciones.setWordWrap(True)
        self.instrucciones.raise_()
        
        self.ventana = QLabel("",self)
        self.ventana.setGeometry(40, 120, 120, 120)
        self.ventana.setAlignment(Qt.AlignCenter)
        self.ventana.setWordWrap(True)
        self.ventana.raise_()

        self.cb_tolerancia = QComboBox(self)
        
        self.cb_tolerancia.setGeometry(40, 250, 120, 20)
        for i in range(tolerancia_max):
            self.cb_tolerancia.addItem(str(i+1))
        

        self.b_acceptar = QPushButton("Aceptar", self)
        self.b_acceptar.setGeometry(40, 280, 120, 40)
        self.b_acceptar.raise_()
        self.b_acceptar.clicked.connect(self.iniciar_tarea)

        self.l_timer = QLabel("00:00:00",self)
        self.l_timer.setGeometry(40, 350, 120, 40)
        self.l_timer.raise_()

        self.b_acceptar.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 92, 92, 220);
                border-radius: 10px;
                color: white;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 20, 20, 240);
            }
        """)
    
    def start_listener(self):

        def on_click(x, y, button, pressed):
            if pressed:
                window_title = pyautogui.getActiveWindowTitle()
                if self.tarea_iniciada and self.timer_iniciado == False:
                    if window_title != self.tarea:
                        self.clicks_count +=1
                    if window_title != self.tarea and self.clicks_count ==2:
                        self.clicks_count =0
                        self.timer_iniciado = True
                        global tolerancia_elegida
                        tolerancia_elegida= int(self.cb_tolerancia.currentText())
                        self.start_timer_signal.emit()
                elif self.tarea_iniciada == False:
                    self.target_window = pyautogui.getWindowsWithTitle(window_title)
                    self.ventana.setText(window_title)
                
        with mouse.Listener(on_click=on_click) as listener:
            listener.join()
    def evt_update_timer(self,val):
        self.l_timer.setText(val)
        self.l_timer.adjustSize()
    def start_timer_thread(self):
        self.timer_thread = QThread()
        self.timer_worker = timerThread()

        self.timer_worker.moveToThread(self.timer_thread)

        self.timer_thread.started.connect(self.timer_worker.run)
        self.timer_worker.update_timer.connect(self.evt_update_timer)

        self.timer_worker.finished.connect(self.evt_ventana_llamado_atencion)
        self.timer_worker.finished.connect(self.timer_thread.quit)
        self.timer_worker.finished.connect(self.timer_worker.deleteLater)
        self.timer_thread.finished.connect(self.timer_thread.deleteLater)

        self.timer_thread.start()
          
    def evt_ventana_llamado_atencion(self):       
        self.llamada_atención = Advertencia(self.target_window)
        self.llamada_atención.show()

    def iniciar_tarea(self,nombre_tarea):
        self.tarea_iniciada = True
        self.tarea=self.ventana.text()
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(self.pos() + event.globalPos() - self.drag_pos)
            self.drag_pos = event.globalPos()
    def closeEvent(self, event):
        self.timer_worker.stop()
        self.timer_thread.quit()
        self.timer_thread.wait() 
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FocusIOn()
    w.show()
    sys.exit(app.exec_())
