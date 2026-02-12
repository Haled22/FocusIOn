import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel,QComboBox,QDesktopWidget,QMessageBox
from PyQt5.QtCore import *
from pynput import mouse
import pyautogui
import threading
import time


tolerancia_max =100
tolerancia_elegida =0


class MouseListener(QObject):
    click_signal = pyqtSignal(int, int, int, int) # x, y, button, pressed
    pressed_signal = pyqtSignal()
    finished = pyqtSignal()
    def __init__(self):
        super(MouseListener, self).__init__()
        self.corriendo = True
    def run(self):
        with mouse.Listener(on_click=self.on_click) as listener:
            listener.join()
        self.finished.emit()
    def on_click(self,pressed):
        if self.corriendo == False:
                return False
        if pressed:
            time.sleep(0.1)
            self.pressed_signal.emit()
    def stop(self):
        self.corriendo= False

    
            
class timerThread(QObject):
    update_timer = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self):
        super(timerThread, self).__init__()
        self.corriendo = True

    def run(self):
        qtime = QTime(0, 0, 0)
        #tolerancia_elegida*60, el 5 es hardcodeado para pruebas
        for x in range(5):
            qtime = qtime.addSecs(1)
            self.update_timer.emit(qtime.toString("hh:mm:ss"))
            time.sleep(1)
            if self.corriendo == False:
                self.finished.emit()
                break
            

        self.finished.emit()
    def stop(self):
        self.corriendo= False
             
class Advertencia(QWidget):
    def __init__(self, target_window):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        window = target_window[0]
        x = window.left
        y = window.top
        width = window.width
        height = window.height
        self.resize(width, height)
        self.move(x,y) 
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.1)
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, width, height)
        self.background.setStyleSheet("""
            QLabel {
                background-color: red;
                
                background-position: center;
                background-repeat: no-repeat;
                
            }
        """)
        time.sleep(1)
        
    def mousePressEvent(self, event):
        
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(self.pos() + event.globalPos() - self.drag_pos)
            self.drag_pos = event.globalPos()

    def show_question_messagebox(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        msg.setText("Llamada de atención")
        
       
        msg.setWindowTitle("Se require su atención aquí")
        
      
        msg.setStandardButtons(QMessageBox.Ok)
  
        retval = msg.exec_()
        if retval == QMessageBox.Ok:
            
            self.close()
        
                
class FocusIOn(QWidget):
    start_timer_signal = pyqtSignal()
    start_listening_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.tarea_iniciada = False
        self.tarea = ""
        
        self.timer_thread = QThread()
        self.timer_worker = timerThread()
        self.clic_thread = QThread()
        self.clic_worker = MouseListener()
        self.clicks_count =0
        self.timer_iniciado = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)

        
        
        self.start_timer_signal.connect(self.start_timer_thread)
        self.start_listening_signal.connect(self.start_clic_manager)
        self.start_listening_signal.emit()
        

        width, height = 200, 400
        self.resize(width, height)
        screen = QDesktopWidget().availableGeometry()
        x = screen.width() - width
        y = screen.height()- height
        self.move(x,y)
        self.setWindowTitle("FocusIOn")

           
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, width, height)
        self.background.setStyleSheet("""
            QLabel {
              
                background-image: url(pretty.jpg);
                background-position: center;
                background-repeat: no-repeat;
               
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
        
    
    
    
    def start_clic_manager(self):
        self.clic_worker.moveToThread(self.clic_thread)

        self.clic_thread.started.connect(self.clic_worker.run)
        self.clic_worker.pressed_signal.connect(self.evt_clic)
        self.clic_worker.finished.connect(self.clic_thread.quit)
        self.clic_worker.finished.connect(self.clic_worker.deleteLater)
        self.clic_thread.finished.connect(self.clic_thread.deleteLater)
       
        self.clic_thread.start()
        
    def evt_clic(self):
        window_title = pyautogui.getActiveWindowTitle()

        
        if window_title:
            if self.tarea_iniciada and self.timer_iniciado == False and window_title != self.windowTitle():
                if window_title != self.tarea:
                    
                    self.timer_iniciado = True
                    global tolerancia_elegida
                    tolerancia_elegida= int(self.cb_tolerancia.currentText())
                    self.start_timer_signal.emit()
            elif self.tarea_iniciada == False and self.windowTitle() != window_title:
                self.target_window = pyautogui.getWindowsWithTitle(window_title)
                self.ventana.setText(window_title)

    def evt_update_timer(self,val):
        self.l_timer.setText(val)
        
    
        
    def start_timer_thread(self):
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
        #self.target_window[0].activate()
        self.llamada_atención.show_question_messagebox()
        self.llamada_atención.destroyed.connect(self.reset_timer)
    def reset_timer(self):
        
        self.timer_iniciado=False
        self.l_timer.setText("00:00:00")
        self.timer_thread = QThread()
        self.timer_worker = timerThread()
        
    def iniciar_tarea(self,nombre_tarea):
        if self.ventana.text() != "":
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
        if self.clic_worker:
            self.clic_worker.stop()
            self.clic_thread.quit()
            self.clic_thread.wait() 
            
        if self.timer_worker:
            self.timer_worker.stop()
            self.timer_thread.quit()
            self.timer_thread.wait()

        
        sys.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = FocusIOn()
    w.show() 
    sys.exit(app.exec_())

