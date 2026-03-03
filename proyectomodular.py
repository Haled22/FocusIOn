import sys
from eyetrax import GazeEstimator, run_9_point_calibration
from PyQt5.QtWidgets import QApplication, QRubberBand, QWidget,QListWidget,QListWidgetItem,QProgressBar, QPushButton, QLabel,QComboBox,QDesktopWidget,QMessageBox
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QCursor
from pynput import mouse
import pyautogui
import threading
import time
import os.path
import cv2


tolerancia_max =100
tolerancia_elegida=0

area_trabajo = []


class GazeListener(QObject):
    update_coordinates = pyqtSignal(int,int)
    
    def __init__(self):
        super(GazeListener, self).__init__()
        self.corriendo = True
        self.x =0
        self.y=0
        self.paused= False
        
        
    def initGazeEstimator(self):
        self.estimator = GazeEstimator()
        if os.path.isfile("gaze_model.pkl"):
            
            loaded_model = self.estimator.load_model("gaze_model.pkl")
        else:
            run_9_point_calibration(self.estimator)
            self.estimator.save_model("gaze_model.pkl")
            self.estimator = GazeEstimator()
            self.estimator.load_model("gaze_model.pkl")
        self.cap = cv2.VideoCapture(0)
    def run(self):
        self.initGazeEstimator()
        self.pause()
        while True:
            while self.paused:
                time.sleep(0.1)
                if self.corriendo == False:
                
                    break
            time.sleep(0.1)
            
            self.gaze_check()
            #temp = self.is_inside_window(self.x,self.y)
            
            self.update_coordinates.emit(int(self.x),int(self.y))
            if self.corriendo == False:
                
                break

    def gaze_check(self):
        
        ret, frame = self.cap.read()
        features, blink = self.estimator.extract_features(frame)

        # Predict screen coordinates
        if features is not None and not blink:
            self.x, self.y = self.estimator.predict([features])[0]
           
        
        
    #def is_in_window(self):

    #    return self
    
    def stop(self):
        self.corriendo= False
    def pause(self):
        if self.paused:
            self.paused = False
        else:
            self.paused = True
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
        #print("hola")
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
    
        


class AreaTrabajo(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        
       
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
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
           #self.rubberBand.hide()
            # Rect is finalized, perform selection logic here
            selection_rect = self.rubberBand.geometry()
            self.aceptar_seleccion()
            
    def mostrar_instrucciones(self):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowFlags(Qt.WindowStaysOnTopHint)
        msg.setText("Seleccione el area de trabajo manteniendo presionando su boton izquierdo y moviendo su mouse para generar la seleccion sobre la pantalla roja semi transparente")
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

class timerThread(QObject):
    update_timer = pyqtSignal(int)
    finished = pyqtSignal()
    def __init__(self):
        super(timerThread, self).__init__()
        self.corriendo = True
        self.paused= False
    def run(self):     
        #tolerancia_elegida*60, el 5 es hardcodeado para pruebas
        x=0
        while x<10:
            self.update_timer.emit(x)
            time.sleep(1)
            x+=1
            if self.corriendo == False:
                break
            while self.paused:
                time.sleep(0.1)
                x=0
                if self.corriendo == False:
                    break             
        self.finished.emit()
    def stop(self):
        self.corriendo= False
    def pause(self):
        if self.paused:
            self.paused = False
        else:
            self.paused = True
        
            
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
class WaitManager(QObject):
    finished = pyqtSignal()
    
    def run(self):
        time.sleep(30)
        self.finished.emit()  
                
class FocusIOn(QWidget):
    start_timer_signal = pyqtSignal()
    start_listening_signal = pyqtSignal()
    #start_wait = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.punto_visual = Punto_visual()
        self.punto_visual.show()
        self.tarea_iniciada = False
        self.tarea = []
        self.paused = False
        self.lista_mostrada = False
        self.interrumpido = False
        self.timer_thread = QThread()
        self.timer_worker = timerThread()
        self.clic_thread = QThread()
        self.clic_worker = MouseListener()
        self.wait_worker = WaitManager()
        self.wait_thread = QThread()
        self.gaze_worker = GazeListener()
        self.gaze_thread = QThread()
        self.clicks_count =0
        self.timer_iniciado = False
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)       

        self.start_gaze_tracking()
        self.start_timer_signal.connect(self.start_timer_thread)
        """ self.start_listening_signal.connect(self.start_clic_manager)
        self.start_listening_signal.emit()  """

        width, height = 200, 400
        
        self.resize(width, height)
        screen = QDesktopWidget().availableGeometry()
        x = screen.width() - width
        y = screen.height()- height
        self.move(round(x+width/2),y)
        self.original_pos=QPoint(round(x+width/2),y)
        self.hover_pos = QPoint(x,y)
        self.setWindowTitle("FocusIOn")
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300) # 300ms
        self.animation.setEasingCurve(QEasingCurve.OutQuad)
           
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


        self.b_pause = QPushButton("▶", self)
        self.b_pause.setToolTip('Pausar tarea/Continuar tarea')
        self.b_pause.setGeometry(30,0, 30, 30)
        self.b_pause.raise_()
        self.b_pause.clicked.connect(self.pause_tracking) 
        
        """  self.instrucciones = QLabel("De clic a una o varias varias para seleccionar las areas de atención",self)
        self.instrucciones.setGeometry(40, 10, 120, 120)
        self.instrucciones.setAlignment(Qt.AlignCenter)
        self.instrucciones.setWordWrap(True)
        self.instrucciones.raise_() """

        self.b_acceptar = QPushButton("Empezar", self)
        self.b_acceptar.setToolTip('Comenzar trackeo')
        self.b_acceptar.setGeometry(40, 280, 70, 40)
        self.b_acceptar.raise_()
        self.b_acceptar.clicked.connect(self.iniciar_tarea)

        self.b_agregar = QPushButton("+", self)
        self.b_agregar.setGeometry(120, 280, 20, 20)
        self.b_agregar.setToolTip('Agrega la pagina seleccionada') 
        self.b_agregar.raise_()
        self.b_agregar.clicked.connect(self.agregar_tarea)



        """ self.l_timer = QLabel("00:00:00",self)

        self.l_timer.setGeometry(40, 350, 120, 40)
        self.l_timer.raise_()
 """
        self.bar_timer = QProgressBar(self)
        self.bar_timer.setGeometry(10,40,10,320)
        self.bar_timer.setOrientation(Qt.Vertical)
        self.bar_timer.setTextVisible(False)
        self.bar_timer.raise_()

        self.bar_timer.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 5px;
                text-align: center;
                background-color: transparent;
            }
            QProgressBar::chunk {
                background-color: #4CAF50; 
                margin: 1px; 
            }
        """)
        
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
       
        self.b_cerrar.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 92, 92, 220);
                
                color: white;
                font-size: 14px;
                border: none;
            }
            QPushButton:hover {
                background-color: rgba(255, 20, 20, 240);
            }
        """)
        self.b_pause.setStyleSheet("""
            QPushButton {
                background-color:rgba(93, 243, 66, 0.52);               
                color: black;
                font-size: 20px;
                border: none;
              
            }
            QPushButton:hover {
                background-color: rgba(39, 187, 13, 0.52);
            }
            
        """)
        
        self.b_agregar.setStyleSheet("""
            QPushButton {
                background-color:rgba(93, 140, 238, 0.8);               
                color: black;
                font-size: 10px;
                border: none;
              
            }
            QPushButton:hover {
                background-color: rgba(45, 105, 233, 0.8);
            }
            
        """)
        
    
    def enterEvent(self, event):
        self.animation.stop()
        self.animation.setEndValue(self.hover_pos)
        self.animation.start()

    def leaveEvent(self, event):
        self.wait_worker.moveToThread(self.wait_thread)
        self.wait_thread.started.connect(self.wait_worker.run)
        self.wait_worker.finished.connect(self.animation_leave)
        
        self.wait_thread.start()
        
    def animation_leave(self):
        self.animation.stop()
        self.animation.setEndValue(self.original_pos)
        self.animation.start()
        if self.wait_worker:
            
            self.wait_thread.quit()
    def mostrar_lista(self):
        if self.lista_mostrada == False:
            self.lista_mostrada = True
            #self.l_timer.hide()
            self.b_acceptar.hide()
            self.b_agregar.hide()
            self.bar_timer.hide()
           
            self.b_remover.hide()
            self.ventana.hide()
            self.instrucciones.hide()
            self.cb_tolerancia.hide()
            items_lista = [self.l_lista.item(i).text() for i in range(self.l_lista.count())]
            if items_lista != self.tarea:
                self.l_lista.clear()
                for tarea in self.tarea:
                    QListWidgetItem(tarea, self.l_lista)
            self.l_lista.show()
        else:
            self.lista_mostrada = False
            self.l_lista.hide()
            #self.l_timer.show()
            self.bar_timer.show()
            self.b_acceptar.show()
            self.b_agregar.show()
            
           
            self.b_remover.show()
            self.ventana.show()
            self.instrucciones.show()
            self.cb_tolerancia.show()
    def start_clic_manager(self):
        #print("Hola")
        self.clic_worker.moveToThread(self.clic_thread)
        
        self.clic_thread.started.connect(self.clic_worker.run)
        
        self.clic_worker.pressed_signal.connect(self.evt_clic)
        self.clic_worker.finished.connect(self.clic_thread.quit)
        self.clic_worker.finished.connect(self.clic_worker.deleteLater)
        self.clic_thread.finished.connect(self.clic_thread.deleteLater)
       
        self.clic_thread.start()
    # x,y,w,h
    def start_gaze_tracking(self):

        self.gaze_worker.moveToThread(self.gaze_thread)

        self.gaze_thread.started.connect(self.gaze_worker.run)
        self.gaze_worker.update_coordinates.connect(self.evt_is_in_window)

        #self.timer_worker.finished.connect(self.evt_ventana_llamado_atencion)
        self.gaze_thread.start()
    def evt_clic(self):
       global area_trabajo
       
       
       window_title = pyautogui.getActiveWindowTitle()
       if area_trabajo and self.tarea_iniciada and not self.clic_worker.paused:
            
            #x,y = pyautogui.position()#This is not working
            x = QCursor.pos().x()
            y= QCursor.pos().y()
            
            x_max = area_trabajo[0][0]
            act_w = area_trabajo[0][2]
            y_max = area_trabajo[0][1]
            act_h = area_trabajo[0][3]
            if (x_max < x < x_max +act_w) and \
            (y_max < y < y_max + act_h):
                #print("Dio click a aquí")
                if self.timer_iniciado:
                    #self.interrumpido=False
                    if self.timer_worker and self.timer_worker.paused == False:
                        self.timer_worker.pause()
                        if self.bar_timer:
                           
                            self.bar_timer.setValue(0)
        
                            time.sleep(0.1)
                           
                        #self.timer_iniciado== False
                   
            else:
                if window_title != self.windowTitle():
                    
                        

                    if self.tarea_iniciada == True and self.timer_iniciado==False:
                        self.timer_iniciado = True
                        self.interrumpido = False
                        #tolerancia_elegida= int(self.cb_tolerancia.currentText())
                        #tolerancia_elegida*60, el 5 es hardcodeado para pruebas
                        self.bar_timer.setMaximum(10)
                        self.start_timer_signal.emit()
                        #print("Dio click afuera")
                    elif self.timer_worker.paused:
                        self.timer_worker.pause()
                        self.interrumpido =False
                       
    def evt_is_in_window(self,x,y):
       global area_trabajo
       
       
       
       if area_trabajo and self.tarea_iniciada and not self.clic_worker.paused:
            
          
            self.punto_visual.move(int(x),int(y))
            
            x_max = area_trabajo[0][0]
            act_w = area_trabajo[0][2]
            y_max = area_trabajo[0][1]
            act_h = area_trabajo[0][3]
            if (x_max < x < x_max +act_w) and \
            (y_max < y < y_max + act_h):
                #print("Dio click a aquí")
                if self.timer_iniciado:
                    #self.interrumpido=False
                    if self.timer_worker and self.timer_worker.paused == False:
                        self.timer_worker.pause()
                        if self.bar_timer:  
                            self.bar_timer.setValue(0)
                            time.sleep(0.1)      
                        #self.timer_iniciado== False     
            else:
                if self.tarea_iniciada == True and self.timer_iniciado==False:
                    self.timer_iniciado = True
                    self.interrumpido = False
                    #tolerancia_elegida= int(self.cb_tolerancia.currentText())
                    #tolerancia_elegida*60, el 5 es hardcodeado para pruebas
                    self.bar_timer.setMaximum(10)
                    self.start_timer_signal.emit()
                    #print("Dio click afuera")
                elif self.timer_worker.paused:
                    self.timer_worker.pause()
                    self.interrumpido =False
                       
                    
                
                   

    def evt_update_timer(self,cont):       
        self.bar_timer.setValue(cont+1)
       #self.l_timer.setText(val)
    def start_timer_thread(self):     
        self.timer_worker.moveToThread(self.timer_thread)
        self.timer_thread.started.connect(self.timer_worker.run)
        self.timer_worker.update_timer.connect(self.evt_update_timer)
        self.timer_worker.finished.connect(self.evt_ventana_llamado_atencion)
        self.bar_timer.show()
        self.timer_thread.start()
        
    def evt_ventana_llamado_atencion(self):
        #window_title = pyautogui.getActiveWindowTitle()     
        if self.interrumpido == False and self.tarea_iniciada:
            self.gaze_worker.pause()
            #self.target_window.isVisible()
            self.llamada_atención = Advertencia()
            self.llamada_atención.show()      
            self.llamada_atención.show_question_messagebox()
            self.llamada_atención.destroyed.connect(self.reset_timer)
            #self.reset_timer()
        else:
            print("No llamada de atencion")
            #self.reset_timer()
            
            
    def reset_timer(self):
        if self.bar_timer:
            self.bar_timer.setValue(0)
        if self.timer_worker:
            self.timer_worker.stop()
            self.timer_thread.quit()
        #if self.gaze_worker:
            #self.gaze_worker.pause()
            
        time.sleep(1)

        self.interrumpido = False
        self.timer_iniciado=False
        #self.l_timer.setText("00:00:00")
        self.timer_thread = QThread()
        self.timer_worker = timerThread()
        self.gaze_worker.pause()
    def agregar_tarea(self):

        self.seleccionar_area = AreaTrabajo()
        self.seleccionar_area.show()

        
    def eliminar_tarea(self):
        if self.ventana.text() in self.tarea:
            self.tarea.remove(self.ventana.text())   
        if len(self.tarea) ==0:
            self.tarea_iniciada= False
            self.timer_iniciado=False
            self.pause_tracking()
            time.sleep(1)
            self.reset_timer()
    def empty_tareas(self):
        self.tarea = []
        
    def iniciar_tarea(self):
        global area_trabajo
        print("hola")
        if area_trabajo:
            self.tarea_iniciada = True
            self.gaze_worker.pause()
            #self.tarea=self.ventana.text()
    def pause_tracking(self):
        if self.clic_worker:
            if self.clic_worker.paused==False:
                self.timer_worker.pause()
            if self.bar_timer:  
                self.bar_timer.setValue(0)
                time.sleep(0.1)

            
            self.clic_worker.pause()
        if self.gaze_worker:
            if self.gaze_worker.paused==False:
                self.gaze_worker.pause()
            if self.bar_timer:  
                self.bar_timer.setValue(0)
                time.sleep(0.1)

            
            self.gaze_worker.pause()
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
