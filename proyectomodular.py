import sys
from eyetrax import GazeEstimator, run_9_point_calibration
from eyetrax.calibration import run_dense_grid_calibration
from PyQt5.QtWidgets import QApplication, QRubberBand, QWidget,QMainWindow,QListWidget,QStackedWidget,QListWidgetItem,QProgressBar, QPushButton, QLabel,QComboBox,QDesktopWidget,QMessageBox,QGraphicsOpacityEffect
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QCursor,QFont,QPixmap,QImageReader

from pynput import mouse
import pyautogui
import threading
import time
import os.path
import cv2
from eyetrax.filters import (
    KDESmoother,
    KalmanEMASmoother,
    KalmanSmoother,
    NoSmoother,
    make_kalman,
)



tolerancia_max =100
tolerancia_elegida=QTime(0,0,15)
tolerancia_elegida_Og =QTime(0,0,15)
tiempo_elegido =0

area_trabajo = []
time_left = QTime(0,0,30)
time_left_og = QTime(0,0,30)



#Clase que maneja la parte del trackeo de ojos por medio de inteligencia artificial
#En el programa se utiliza como un worker de un thread
class GazeListener(QObject):
    update_coordinates = pyqtSignal(int,int)

    pause_timer =pyqtSignal()
    def __init__(self):
        super(GazeListener, self).__init__()
        self.corriendo = True
        self.x =0
        self.y=0
        self.paused= False
        self.recal = False
        self.cap = cv2.VideoCapture(0)      
    def initGazeEstimator(self):

        time.sleep(1)
        self.estimator = GazeEstimator()
        if os.path.isfile("gaze_model.pkl") and self.recal ==False:
            
            loaded_model = self.estimator.load_model("gaze_model.pkl")
        else:
            run_dense_grid_calibration(self.estimator)
            kalman = make_kalman()
            smoother = KalmanEMASmoother(kalman)
            smoother.tune(self.estimator)
            self.estimator.save_model("gaze_model.pkl")
            self.estimator = GazeEstimator()
            self.estimator.load_model("gaze_model.pkl")
        self.cap = cv2.VideoCapture(0)
    def recalibrate(self):
        self.recal = True
        time.sleep(1)
        self.initGazeEstimator()
    def run(self):
        self.initGazeEstimator()
        #self.pause()
        while True:
            if self.recal:
                self.pause_timer.emit()
                self.pause()
            
            while self.paused:
                if self.corriendo == False:
                    break
            time.sleep(1)
            self.gaze_check()
            self.update_coordinates.emit(int(self.x),int(self.y))
            if self.corriendo == False:
                break

    def gaze_check(self):
        ret, frame = self.cap.read()
        features, blink = self.estimator.extract_features(frame)
        if features is not None and not blink:
            self.x, self.y = self.estimator.predict([features])[0]
    def stop(self):
        self.corriendo= False
    def pause(self):
        if self.paused:
            self.paused = False
        else:
            self.paused = True
    def set_recal(self):
        if self.recal:
            self.recal = False
        else:
            self.recal = True
#Esta clase se encarga de monitorear los clicks del usuario para que el programa principal 
#Cheque si esta estos clics estan dentro de los limites del area de trabajo
class MouseListener(QObject):
    click_signal = pyqtSignal(int, int, int, int) 
    pressed_signal = pyqtSignal()
    finished = pyqtSignal()
    def __init__(self):
        super(MouseListener, self).__init__()
        self.corriendo = True
        self.paused = False
        self.listener = None
    def run(self):
        if self.listener is None:
            self.listener = mouse.Listener(on_click=self.on_click)
            self.listener.start()   
    def on_click(self,pressed):

        if self.corriendo == False:
                return False
        if pressed:
            time.sleep(0.1)
            self.pressed_signal.emit()
    def stop(self):
        self.corriendo= False    
    def pause(self):
        if self.paused:
            self.paused =False
        else:
            self.paused = True
#Clase temporal para fines de vizualizacion de la mirada del usuario
class Punto_visual(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, 20, 20)
        self.background.setStyleSheet("""
            QLabel {
                background-color: red;
                
                background-position: center;
                background-repeat: no-repeat;
                
            }
        """)

#Clase que permite al usuario seleccionar su area de trabajo
class AreaTrabajo(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowFlags( Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.2)
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, self.maximumWidth(), self.maximumHeight())
        self.background.setStyleSheet("""
            QLabel {
                background-color: grey;
                
                background-position: center;
                background-repeat: no-repeat;
                
            }
        """)
    
        self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
        self.rubberBand.hide()
        self.origin = QPoint()
        self.showMaximized()
        self.mostrar_instrucciones()

    def mousePressEvent(self, event):
        if self.rubberBand.isVisible():
            self.rubberBand.hide()
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if not self.origin.isNull():
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            selection_rect = self.rubberBand.geometry()
            self.aceptar_seleccion()

    def mostrar_instrucciones(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg.setText("Seleccione el area de trabajo manteniendo presionando su boton izquierdo y moviendo su mouse para generar la seleccion sobre la pantalla semi transparente")
        msg.setWindowTitle("Instrucciones")
        msg.setStandardButtons(QMessageBox.Ok)
        retval = msg.exec_()

    def aceptar_seleccion(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg.setText("Esta es su area de trabajo?")
        msg.setWindowTitle("Confimación")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        retval = msg.exec_()
        if retval == QMessageBox.Ok:
            global area_trabajo
            selection_rect = self.rubberBand.geometry()
            area_trabajo.append(selection_rect.getCoords())
            
            self.close()

#Clases que cuenta cuanto tiempo a pasado, la usamos para monitorear el tiempo total de trabajo
# y para checar cuanto tiempo el usuario se ha distraido
class Temporizador(QObject):
    update_timer = pyqtSignal(str)
    finished = pyqtSignal()
    success = pyqtSignal()
    update_warning = pyqtSignal()
    open_warning=pyqtSignal()
    def __init__(self,mode):
        super(Temporizador, self).__init__()
        self.corriendo = True
        self.paused= False
        self.mode = mode
        self.reset_x=False
        self.og_tolerancia = None
        self.og_time_left =None       
    def run(self): 
        if self.mode ==0:
            global time_left
            global time_left_og
            self.og_time_left = time_left_og
            time_left_og=time_left
            self.tiempo = time_left.hour()*3600+time_left.minute()*60+time_left.second()
        else:
            global tolerancia_elegida
            global tolerancia_elegida_Og
            tolerancia_elegida_Og =tolerancia_elegida
            self.og_tolerancia = tolerancia_elegida_Og
            self.og_tolerancia=tolerancia_elegida
            self.tiempo = tolerancia_elegida.hour()*3600+tolerancia_elegida.minute()*60+tolerancia_elegida.second()
        x=0
        while x<self.tiempo:
            if self.paused:
                while self.paused:
                    time.sleep(0.1)   
                    if self.corriendo == False:
                        break   
                if self.mode==0 and self.og_time_left !=time_left_og:
                    self.tiempo = time_left_og.hour()*3600+time_left_og.minute()*60+time_left_og.second()
                    time_left = time_left_og
                    x=0  
                elif self.mode ==1 and self.og_tolerancia != tolerancia_elegida_Og:
                    self.tiempo = tolerancia_elegida.hour()*3600+tolerancia_elegida.minute()*60+tolerancia_elegida.second()
                    tolerancia_elegida = tolerancia_elegida_Og
                    x=0   
            if self.mode ==0:
                time_left = time_left.addSecs(-1)
                self.update_timer.emit(time_left.toString("hh:mm:ss"))
            else:
                tolerancia_elegida = tolerancia_elegida.addSecs(-1)
                self.update_timer.emit(tolerancia_elegida.toString("hh:mm:ss"))
            time.sleep(1)
            x+=1
            if x>=self.tiempo and self.mode==0:
                self.pause()
                x=0
                self.success.emit()
                while self.paused:
                    time.sleep(0.1)
                    
                    if self.corriendo == False:
                        break   
                self.tiempo = time_left_og.hour()*3600+time_left_og.minute()*60+time_left_og.second()
                time_left = time_left_og
            if x>=self.tiempo and self.mode==1:
                self.open_warning.emit()
                n=5
                for j in range(n):
                    if self.corriendo == False:
                        break
                    for i in range(5):
                        time.sleep(1)
                        if self.corriendo == False:
                            break
                    self.update_warning.emit()
            if self.corriendo == False:
                break   
        self.finished.emit()
    def reset(self):
        self.reset_x=True
    def stop(self):
        self.corriendo= False
    def pause(self):

        if self.paused:
            self.paused = False
        else:
            self.paused = True
#Clase que modifica el QLable para que se pueda ajustar el tiempo con el drag del mouse presionado 
class label_tiempo_ajustable(QLabel):
    def __init__(self, text, parent=None, mode=None):
        super().__init__(text, parent)
        if mode is not None:
            self.mode =mode
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.last_pos = event.pos()
    def mouseMoveEvent(self, event):
        if self.mode==0:
            global time_left
            global time_left_og  
            self.time_left = time_left.hour()*3600+time_left.minute()*60+time_left.second()
        else:
            global tolerancia_elegida
            global tolerancia_elegida_Og
            self.time_left = tolerancia_elegida.hour()*3600+tolerancia_elegida.minute()*60+tolerancia_elegida.second()
        if self.last_pos is None:
            return
        dx = event.x() - self.last_pos.x()
        dy = event.y() - self.last_pos.y()
        if abs(dx) > 5:
            self.time_left += dx // 5
            self.last_pos = event.pos()
        if abs(dy) > 5:
            self.time_left += (-dy//5)*30
            self.last_pos = event.pos()
        temp = max(0, self.time_left)
        t_hrs = temp // 3600
        t_mins = (temp % 3600) //60
        t_secs = temp %60
        if self.mode==0:
            time_left = QTime(t_hrs,t_mins,t_secs)
            time_left_og = QTime(t_hrs,t_mins,t_secs)
            self.setText(time_left.toString("hh:mm:ss"))
        else:
            tolerancia_elegida = QTime(t_hrs,t_mins,t_secs)
            tolerancia_elegida_Og = QTime(t_hrs,t_mins,t_secs)
            self.setText(tolerancia_elegida.toString("hh:mm:ss"))
    def mouseReleaseEvent(self, event):
        self.last_pos = None
#Clase que coloca un pestaña semi transparente roja sobre la pantalla cuando el usuario no presta atencion
#sobre el area de trabajo elegida
class Advertencia(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        x_target = area_trabajo[0][0]
        w_target = area_trabajo[0][2]
        y_target = area_trabajo[0][1]
        h_target = area_trabajo[0][3]
        self.resize(w_target, h_target)
        self.move(x_target,y_target) 
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.1)
        self.background = QLabel(self)
        self.background.setGeometry(0, 0, w_target, h_target)
        self.background.setStyleSheet("""
            QLabel {
                background-color: red;
                
                background-position: center;
                background-repeat: no-repeat;   
            }
        """)
        time.sleep(1)
        
    def mousePressEvent(self, event):
        self.close()
    def closeEvent(self,event):
        
        self.background.deleteLater() 
        self.close()
#Clase que hace que los botones del menu principal se cambien de posicion cuando 
#se pone el pointer sobre ellos, esto para poder aprovechar mas del limitado espacio de la ui
class BotonBrincador(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.anim = None
        self.original_rect = None  
        self.hover_offset = 15  
        self.clicked.connect(self.animate_button)

    def setGeometry(self, *args):
        super().setGeometry(*args)
        self.original_rect = self.pos()

    def enterEvent(self, event):
        self.raise_()
        super().enterEvent(event)

    def animate_button(self):
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(300) 
        
        start_pos = self.pos()
        mid_pos = start_pos - QPoint(0, self.hover_offset)
        end_pos = self.original_rect
        
        self.anim.setKeyValueAt(0, start_pos)
        self.anim.setKeyValueAt(0.5, mid_pos)
        self.anim.setKeyValueAt(1, end_pos)
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.OutBounce)
        self.anim.start()              
#Aplicacion principal
class FocusIOn(QMainWindow):   
    start_countdown_signal = pyqtSignal()
    start_tracking_signal = pyqtSignal()
    start_mouse_tracking_signal = pyqtSignal()
    #start_success_msg = pyqtSignal() tbd
    start_distraido_timer = pyqtSignal()
    
    def __init__(self):
        super().__init__() 
        self.punto_visual = Punto_visual()
        self.mode =0
        self.tarea_iniciada = False
        self.paused = False
        self.interrumpido = False
        self.count=0

        self.clic_thread = QThread()
        self.clic_worker = MouseListener()
        self.gaze_worker=None
        self.gaze_thread=None

        self.count_down_worker = Temporizador(0)
        self.count_down_thread = QThread()
        self.timer_distraido_worker = Temporizador(1)
        self.timer_distraido_thread = QThread()
        self.llamada_atencion = None
        
        self.width, self.height = 160, 240
        self.resize(self.width, self.height)

        screen = QDesktopWidget().availableGeometry()
        self.x_app = screen.width() - self.width
        self.y_app = screen.height()- self.height
        self.move(self.x_app,self.y_app)
        
        self.setWindowTitle("FocusIOn")

        self.clicks_count =0
        self.timer_iniciado = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)   

        self.start_countdown_signal.connect(self.start_timer_countdown)
        self.start_distraido_timer.connect(self.start_timer_distraido)
        self.start_tracking_signal.connect(self.start_tracking)
        self.start_mouse_tracking_signal.connect(self.start_clic_manager)

        

        reader = QImageReader("add_icon.svg")
        self.add_icon = QPixmap(reader.read())
        reader = QImageReader("close_button.svg")
        self.close_icon = QPixmap(reader.read())
        reader = QImageReader("eye_icon.svg")
        self.eye_icon = QPixmap(reader.read())
        reader = QImageReader("play_pause.svg")
        self.play_icon = QPixmap(reader.read())
        reader = QImageReader("reset_icon.svg")
        self.reset_icon = QPixmap(reader.read())
        reader = QImageReader("mouse_icon.svg")
        self.mouse_icon = QPixmap(reader.read())

        self.overlay = QLabel(self)
        self.overlay.setGeometry(0, 0, self.width, self.height)
        self.overlay.setStyleSheet("background-color: rgba(20, 30, 47, 80);border-radius: 20px;border-radius: 10px;color: black;")

       
        self.paginas = QStackedWidget()
        self.menu_screen = self.initMenu()
        self.ojos_screen = None
        self.mouse_screen = None
        self.paginas.addWidget(self.menu_screen)
        self.setCentralWidget(self.paginas)
        self.initStyleApp()
    def initStyleApp(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(46,46,68,220);  
                color: rgba(255,255,255,1);             
            }
            QPushButton:hover {
                background-color: rgba(86, 86, 109, 220);
                
            }             
            QLabel {color: #F8F8F2; background-color: rgba(46,46,68,220); border-radius: 6px; padding: 6px;
                           }
            
            """                
                           )
     
    def initMenu(self):
        menu_widget = QWidget()

        self.overlay = QLabel(menu_widget)
        self.overlay.setGeometry(0, 0, self.width, self.height)
        self.overlay.setStyleSheet("background-color: rgba(20, 30, 47, 80);border-radius: 20px;border-radius: 10px;color: black;")
    
        self.b_cerrar = QPushButton(menu_widget)
        self.b_cerrar.setIcon(QIcon(self.close_icon))
        self.b_cerrar.setGeometry(130, 0, 30, 30)
        self.b_cerrar.raise_()
        self.b_cerrar.clicked.connect(self.closeEvent)

 
        self.b_mouse = BotonBrincador("Trackeo \n de mouse", menu_widget)
        self.b_mouse.setIcon(QIcon(self.mouse_icon))
        self.b_mouse.setGeometry(20, 60,80,80)
        self.b_mouse.raise_()
        self.b_mouse.clicked.connect(self.mostrarUiMouse)
 

        self.b_eyes = BotonBrincador("Trackeo \n de ojos",menu_widget)
        self.b_eyes.setIcon(QIcon(self.eye_icon))
        self.b_eyes.setToolTip('Trackeo \n de ojos 👁️')    
        self.b_eyes.setGeometry(60,100,80,80)
        self.b_eyes.raise_()
        self.b_eyes.clicked.connect(self.mostrarUiOjos)
        
        return menu_widget 
    def initOjos(self):

        ojos_widget = QWidget()
        ojos_widget.resize(self.width,self.height)

        self.b_cerrar = QPushButton(ojos_widget)
        self.b_cerrar.setIcon(QIcon(self.close_icon))
        self.b_cerrar.setGeometry(130, 0, 30, 30)
        self.b_cerrar.raise_()
        self.b_cerrar.clicked.connect(self.closeEvent)
        
        self.b_cambiar_modo = QPushButton(ojos_widget)
        self.b_cambiar_modo.setIcon(QIcon(self.mouse_icon))
        self.b_cambiar_modo.setGeometry(0, 0, 30, 30)
        self.b_cambiar_modo.raise_()
        self.b_cambiar_modo.clicked.connect(self.mostrarUiMouse)
        
        global time_left
        self.l_timer_count_down = label_tiempo_ajustable(time_left.toString("hh:mm:ss"),ojos_widget,0)
        self.l_timer_count_down.move(10,40)

        global tolerancia_elegida
        self.l_timer_distraido = label_tiempo_ajustable(tolerancia_elegida.toString("hh:mm:ss"),ojos_widget,1)
        self.l_timer_distraido.move(10,100)
        
        self.l_timer_distraido.setAlignment(Qt.AlignCenter)
        self.l_timer_distraido.setFont(QFont("Consolas", 15, QFont.Bold))  
        self.l_timer_distraido.raise_()

        self.l_timer_count_down.setAlignment(Qt.AlignCenter)
        self.l_timer_count_down.setFont(QFont("Consolas", 15, QFont.Bold))  
        self.l_timer_count_down.raise_()
        
        self.b_recalibrar = QPushButton(ojos_widget)
        self.b_recalibrar.setIcon(QIcon(self.reset_icon))
        self.b_recalibrar.setToolTip('Recalibrar trackeo de ojos')
        self.b_recalibrar.setGeometry(90,160, 30, 30)
        self.b_recalibrar.raise_()
        self.b_recalibrar.clicked.connect(self.recalibrate) 

        self.b_acceptar = QPushButton(ojos_widget)
        self.b_acceptar.setIcon(QIcon(self.play_icon))
        self.b_acceptar.setToolTip('Comenzar trackeo')
        self.b_acceptar.setGeometry(50, 160, 30, 30)
        self.b_acceptar.raise_()
        self.b_acceptar.clicked.connect(self.iniciar_tarea)


        self.b_agregar = QPushButton(ojos_widget)
        self.b_agregar.setIcon(QIcon(self.add_icon))
        self.b_agregar.setGeometry(10, 160, 30, 30)
        self.b_agregar.setToolTip('Agrega la pagina seleccionada') 
        self.b_agregar.raise_()
        self.b_agregar.clicked.connect(self.agregar_tarea)

        self.mode =1
        self.punto_visual.show()
        self.start_gaze_tracking()
        return ojos_widget
    def initMouse(self):
        mouse_widget = QWidget()
        mouse_widget.resize(self.width,self.height)
       
        self.b_cerrar = QPushButton(mouse_widget)
        self.b_cerrar.setIcon(QIcon(self.close_icon))
        self.b_cerrar.setGeometry(130, 0, 30, 30)
        self.b_cerrar.raise_()
        self.b_cerrar.clicked.connect(self.closeEvent)

        self.b_cambiar_modo = QPushButton(mouse_widget)
        self.b_cambiar_modo.setIcon(QIcon(self.eye_icon))
        self.b_cambiar_modo.setGeometry(0, 0, 30, 30)
        self.b_cambiar_modo.raise_()
        self.b_cambiar_modo.clicked.connect(self.mostrarUiOjos)
        
        global time_left
        self.l_timer_count_down = label_tiempo_ajustable(time_left.toString("hh:mm:ss"),mouse_widget,0)
        self.l_timer_count_down.move(10,40)

        global tolerancia_elegida
        self.l_timer_distraido = label_tiempo_ajustable(tolerancia_elegida.toString("hh:mm:ss"),mouse_widget,1)
        self.l_timer_distraido.move(10,100)
       
        self.l_timer_distraido.setAlignment(Qt.AlignCenter)
        self.l_timer_distraido.setFont(QFont("Consolas", 15, QFont.Bold))  
        self.l_timer_distraido.raise_()

        self.l_timer_count_down.setAlignment(Qt.AlignCenter)
        self.l_timer_count_down.setFont(QFont("Consolas", 15, QFont.Bold))  
        self.l_timer_count_down.raise_()
        
        self.b_acceptar = QPushButton(mouse_widget)
        self.b_acceptar.setIcon(QIcon(self.play_icon))
        self.b_acceptar.setToolTip('Comenzar trackeo')
        self.b_acceptar.setGeometry(50, 160, 30, 30)
        self.b_acceptar.raise_()
        self.b_acceptar.clicked.connect(self.iniciar_tarea)
        
        self.b_agregar = QPushButton(mouse_widget)
        self.b_agregar.setIcon(QIcon(self.add_icon))
        self.b_agregar.setGeometry(10, 160, 30, 30)
        self.b_agregar.setToolTip('Agrega la pagina seleccionada') 
        self.b_agregar.raise_()
        self.b_agregar.clicked.connect(self.agregar_tarea)

        self.mode =0
        return mouse_widget
    def mostrarUiMouse(self):
        if self.punto_visual.isVisible():
            self.punto_visual.hide()
        if self.count_down_worker.paused==False:
            self.count_down_worker.pause()
        if self.timer_distraido_worker.paused==False:
            self.timer_distraido_worker.pause()
        if self.gaze_thread != None:
            if self.gaze_thread.isRunning():
                self.gaze_worker.stop()
                self.gaze_thread.quit()
                self.gaze_thread.wait()
                self.gaze_worker = None
                self.gaze_thread = None 
        if self.mouse_screen == None:
            self.mouse_screen = self.initMouse()
            self.paginas.addWidget(self.mouse_screen)
        self.paginas.setCurrentWidget(self.mouse_screen)
        self.start_mouse_tracking_signal.emit()
    def mostrarUiOjos(self):
        if self.count_down_thread.isRunning():
            self.count_down_worker.stop()
            self.count_down_thread.quit()
            self.count_down_thread.wait()
            self.count_down_worker = None
            self.count_down_thread = None
            self.count_down_worker = Temporizador(0)
            self.count_down_thread = QThread()
        
        if self.timer_distraido_thread.isRunning():
            self.timer_distraido_worker.stop()
            self.timer_distraido_thread.quit()
            self.timer_distraido_thread.wait()
            self.timer_distraido_worker = None
            self.timer_distraido_thread = None
            self.timer_distraido_worker = Temporizador(1)
            self.timer_distraido_thread = QThread()
        if self.clic_thread.isRunning():
            self.clic_worker.stop()
            self.clic_thread.quit()
            self.clic_thread.wait()
            self.clic_worker = None
            self.clic_thread = None
            self.clic_worker = MouseListener()
            self.clic_thread = QThread()
        if self.ojos_screen == None:
            self.ojos_screen = self.initOjos()
            self.paginas.addWidget(self.ojos_screen)
        self.paginas.setCurrentWidget(self.ojos_screen)
    def mostrarUiMenu(self):
        self.paginas.setCurrentWidget(self.menu_screen)

    def start_clic_manager(self):
        self.clic_worker.moveToThread(self.clic_thread)
        self.clic_thread.started.connect(self.clic_worker.run)
        self.clic_worker.pressed_signal.connect(self.evt_clic)
        self.clic_worker.finished.connect(self.clic_thread.quit)
        self.clic_worker.finished.connect(self.clic_worker.deleteLater)
        self.clic_thread.finished.connect(self.clic_thread.deleteLater)
        self.clic_thread.start()
    # x,y,w,h
    def start_gaze_tracking(self):  
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if  ret or frame is not None:
                cap.release()
                time.sleep(0.1)
                self.gaze_worker = GazeListener()
                self.gaze_thread = QThread()
                self.gaze_worker.moveToThread(self.gaze_thread)
                self.gaze_thread.started.connect(self.gaze_worker.run)
                self.gaze_worker.update_coordinates.connect(self.evt_is_in_window)
                self.gaze_thread.start()
                      
    def evt_clic(self):
       global area_trabajo
       window_title = pyautogui.getActiveWindowTitle()
       if area_trabajo and self.tarea_iniciada and not self.clic_worker.paused:
            if self.count_down_thread.isRunning()==False:
                self.start_countdown_signal.emit()
            x = QCursor.pos().x()
            y= QCursor.pos().y()
            x_max = area_trabajo[0][0]
            act_w = area_trabajo[0][2]
            y_max = area_trabajo[0][1]
            act_h = area_trabajo[0][3]
            if ((x_max < x < x_max +act_w) and \
            (y_max < y < y_max + act_h)):

                if self.timer_iniciado:
                    if self.timer_distraido_worker and self.timer_distraido_worker.paused == False:
                        self.timer_distraido_worker.pause()
                        self.reset_timer()
                        time.sleep(0.1)
            else:
                if window_title != self.windowTitle():
                    if self.tarea_iniciada == True and self.timer_iniciado==False:
                        self.timer_iniciado = True
                        self.interrumpido = False
                        self.start_distraido_timer.emit()
                    elif self.timer_distraido_worker.paused: 
                        self.timer_distraido_worker.pause()
                        self.interrumpido =False
                
    def recalibrate(self):
        if os.path.isfile("gaze_model.pkl"): 
            os.remove("gaze_model.pkl")
            self.gaze_worker.recalibrate()           
    def evt_is_in_window(self,x,y):
       global area_trabajo
       global tolerancia_elegida_Og
       if self.gaze_thread != None:
        if self.gaze_thread.isRunning():
            if area_trabajo and self.tarea_iniciada and not self.gaze_worker.paused:
                    if self.count_down_thread != None:
                        if self.count_down_thread.isRunning() == False:   
                            self.start_countdown_signal.emit()
                    self.punto_visual.move(int(x),int(y))
                    x_max = area_trabajo[0][0]
                    act_w = area_trabajo[0][2]
                    y_max = area_trabajo[0][1]
                    act_h = area_trabajo[0][3]
                    if (x_max < x < x_max +act_w) and \
                    (y_max < y < y_max + act_h):
                        self.count+=1
                        if self.count == 3:
                            if self.timer_iniciado:
                                if self.count_down_worker and self.count_down_worker.paused == False:
                                    self.timer_distraido_worker.pause()
                                    if self.l_timer_distraido:  
                                        self.reset_timer() 
                    else:
                        self.count=0
                        if self.tarea_iniciada == True and self.timer_iniciado==False:
                            self.timer_iniciado = True
                            self.interrumpido = False
                            self.start_timer_distraido()
                        elif self.timer_distraido_worker.paused:
                            self.timer_distraido_worker.pause()
                            self.interrumpido =False

    def evt_update_count_down(self,val):
        self.l_timer_count_down.setText(val)
    def evt_update_distraido_timer(self,val):
        self.l_timer_distraido.setText(val)
    
    def start_timer_countdown(self):     
        self.count_down_worker.moveToThread(self.count_down_thread)
        self.count_down_thread.started.connect(self.count_down_worker.run)
        self.count_down_worker.update_timer.connect(self.evt_update_count_down)
        self.count_down_worker.success.connect(self.evt_success)
        self.count_down_worker.finished.connect(self.count_down_thread.quit)
        self.count_down_worker.finished.connect(self.count_down_worker.deleteLater)
        self.count_down_thread.finished.connect(self.count_down_thread.deleteLater)
        self.count_down_thread.start()

    def start_timer_distraido(self):     
        self.timer_distraido_worker.moveToThread(self.timer_distraido_thread)
        self.timer_distraido_thread.started.connect(self.timer_distraido_worker.run)
        self.timer_distraido_worker.update_timer.connect(self.evt_update_distraido_timer)
        self.timer_distraido_worker.update_warning.connect(self.update_warning)
        self.timer_distraido_worker.open_warning.connect(self.evt_ventana_llamado_atencion)
        self.timer_distraido_worker.finished.connect(self.timer_distraido_thread.quit)
        self.timer_distraido_worker.finished.connect(self.timer_distraido_worker.deleteLater)
        self.timer_distraido_thread.finished.connect(self.timer_distraido_thread.deleteLater)
        self.timer_distraido_thread.start()

    def update_warning(self):
        if self.llamada_atencion:
            try:
                self.llamada_atencion.setWindowOpacity(self.llamada_atencion.windowOpacity()+0.1)
            except:
                print("No se pudo cambiar la opacidad")

    def evt_success(self):
        if self.clic_worker:
            self.clic_worker.pause()
        if self.gaze_worker:
            if self.gaze_worker.paused==False:
                self.gaze_worker.pause()
        if self.count_down_worker:
            self.timer_distraido_worker.pause()
        self.l_timer_count_down.setEnabled(True)
        self.l_timer_distraido.setEnabled(True)

    def evt_ventana_llamado_atencion(self):
        if self.interrumpido == False and self.tarea_iniciada:
            self.llamada_atencion = Advertencia()
            self.llamada_atencion.show()      
            self.llamada_atencion.destroyed.connect(self.reset_timer)

    def reset_timer(self):
        if self.timer_distraido_worker:
            global tolerancia_elegida 
            global tolerancia_elegida_Og
            tolerancia_elegida= tolerancia_elegida_Og
            if tolerancia_elegida != None:
                self.evt_update_distraido_timer(tolerancia_elegida.toString("hh:mm:ss"))
            self.timer_distraido_worker.stop()
            self.timer_distraido_thread.quit()
            self.timer_distraido_thread.wait()
            self.timer_distraido_worker = None
            self.timer_distraido_thread = None 
        if self.gaze_worker:
            if self.gaze_worker.paused:
                self.gaze_worker.pause() 
        self.interrumpido = False
        self.timer_iniciado=False
       
        self.timer_distraido_thread = QThread()
        self.timer_distraido_worker = Temporizador(1)

    def agregar_tarea(self):
        self.b_acceptar.setEnabled(False)
        self.b_agregar.setEnabled(False)
        self.seleccionar_area = AreaTrabajo()
        self.seleccionar_area.show()
        self.seleccionar_area.destroyed.connect(self.start_tracking_signal.emit)
        
    def start_tracking(self):
        if self.tarea_iniciada:
            if self.mode ==0:
                self.start_clic_manager() 
                self.start_countdown_signal.emit()
            elif self.mode ==1 and self.gaze_thread.isRunning() ==False:
                self.start_gaze_tracking()
        self.l_timer_count_down.setEnabled(False)
        self.l_timer_distraido.setEnabled(False)
        self.b_agregar.setEnabled(True)
        self.b_acceptar.setEnabled(True)
 
    def iniciar_tarea(self):
        global area_trabajo
        if area_trabajo:
            if self.tarea_iniciada:
                self.pause_tracking()
            else:
                self.tarea_iniciada = True
                self.count_down_thread = QThread()
                self.count_down_worker = Temporizador(0)
                self.start_countdown_signal.emit()                 
        else:
            self.tarea_iniciada= True
            self.agregar_tarea()  
 
    def pause_tracking(self):
        if self.mode==0:
            if self.timer_distraido_worker:
                if self.clic_worker.paused != self.timer_distraido_worker.paused:
                    if self.timer_distraido_worker.paused == False:
                        self.timer_distraido_worker.pause()
        else:
            if self.timer_distraido_worker:
                if self.gaze_worker.paused != self.timer_distraido_worker.paused:
                    if self.timer_distraido_worker.paused == False:
                        self.timer_distraido_worker.pause()
        if self.clic_worker:
            self.clic_worker.pause()
        if self.gaze_worker:
            self.gaze_worker.pause()
        if self.count_down_worker:
            self.count_down_worker.pause()
            if self.count_down_worker.paused:
                self.timer_distraido_worker.pause()
        else:
            self.start_countdown_signal.emit()  
        if self.l_timer_count_down.isEnabled():
            self.l_timer_count_down.setEnabled(False)
        else:
            self.l_timer_count_down.setEnabled(True)
        if self.l_timer_distraido.isEnabled():
            self.l_timer_distraido.setEnabled(False)
        else:
            self.l_timer_distraido.setEnabled(True)
        
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
        if self.timer_distraido_worker:  
            self.timer_distraido_worker.stop()
            self.timer_distraido_thread.quit()
            self.timer_distraido_thread.wait()
        if self.llamada_atencion:
            try:
                self.llamada_atencion.close()
            except:
                print("No se pudo llamar la atencion")
            QTimer.singleShot(1000, lambda: setattr(self, 'llamada_atencion', None))      
        sys.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    w = FocusIOn()
    w.show() 
    sys.exit(app.exec_())
