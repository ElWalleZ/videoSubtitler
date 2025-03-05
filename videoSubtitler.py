import cv2
import sys
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QUrl, QLoggingCategory
from PyQt6.QtWidgets import QHBoxLayout, QMessageBox, QSlider
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

QLoggingCategory.setFilterRules("qt.multimedia.*=false") #para que no salgan mensajes feos

class MiEtiqueta(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.Lista = []
        self.setStyleSheet("border: 1px solid black;")

class Window(QtWidgets.QWidget):

    def center(self):
        """
        Centra la Ventada SI o SI
        """
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def __init__(self):
        super().__init__()
        self.OpenCV_image3 = None
        self.OpenCV_image = None
        self.OpenCV_image2 = None
        self.center()

        self._path = None

        self.viewer = MiEtiqueta()
        self.viewer2 = MiEtiqueta()
        self.viewer.setFixedSize(840, 680)
        self.viewer2.setFixedSize(840, 680)
        self.viewer.setScaledContents(True)
        self.viewer2.setScaledContents(True)

        self.buttonOpen = QtWidgets.QPushButton("Select Video")
        BUTTON_SIZE = QSize(200, 50)
        self.buttonOpen.setMinimumSize(BUTTON_SIZE)
        self.buttonOpen.clicked.connect(self.handleOpen)

        self.elements = []

        #self.procesarImagenEntrada = QtWidgets.QPushButton("Procesar")
        self.procesarImagenEntrada = QtWidgets.QPushButton("Play/Puase")
        self.procesarImagenEntrada.setMinimumSize(BUTTON_SIZE)
        self.procesarImagenEntrada.clicked.connect(self.toggle_playback)
        #self.procesarImagenEntrada.clicked.connect(self.ProcesarImage)

        self.guardarImagen = QtWidgets.QPushButton("Save Video")
        self.guardarImagen.setMinimumSize(BUTTON_SIZE)
        self.guardarImagen.clicked.connect(self.handleSaveFile)

        layout = QtWidgets.QGridLayout(self)
        self.botonProcesaReservado = QtWidgets.QPushButton("Select SRT")
        # self.botonProcesaReservado.setText("Marker Ratio")
        # self.botonProcesaReservado.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.botonProcesaReservado.setMinimumSize(BUTTON_SIZE)
        self.botonProcesaReservado.clicked.connect(self.detectSigns)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.buttonOpen)
        button_layout.addWidget(self.procesarImagenEntrada)
        button_layout.addWidget(self.botonProcesaReservado)
        button_layout.addWidget(self.guardarImagen)

        layout.addLayout(button_layout, 0, 0, 1, 4)
        layout.addWidget(self.viewer, 1, 0, 1, 2)
        layout.addWidget(self.viewer2, 1, 2, 1, 2)

        self.cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30

        # Media player setup
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        layout.addWidget(self.slider, 2, 0, 1, 2)  # Add to layout
        self.slider.sliderMoved.connect(self.seek_frame)

        Tamano = (self.viewer.size().width(), self.viewer.size().height())

        print(self.viewer.size(), type(self.viewer.size()), Tamano)

    def ProcesarImage(self):
        pass

    def handleSaveFile(self):
        if self.OpenCV_image2 is not None:
            defaultname = "example.png"

            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", defaultname,
                                                                "Images(*.jpg *.png)")

            if fileName:
                if not fileName.endswith(('.png', '.jpg')):
                    fileName += ".png"
                cv2.imwrite(fileName, self.OpenCV_image2)
        else:
            QMessageBox.warning(self, "Error", "No hay nada que guardar aun")

    def handleOpen(self):
        start = "."
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose Video", start, "Videos(*.mp4 *.avi *.mov *.mkv)"
        )
        if path:
            self._path = path
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Error", "Could not open video file")
                return

            # Initialize video properties
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.slider.setMaximum(self.total_frames - 1)

            # Set up media player for audio
            self.media_player.setSource(QUrl.fromLocalFile(path))

            # Show first frame
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = 0
                self.update_viewers(frame)

    def toggle_playback(self):
        if self.OpenCV_image2 is not None:
            if self.is_playing:
                self.timer.stop()
                self.media_player.pause()
                self.is_playing = False
            else:
                interval = int(1000 / self.fps) if self.fps > 0 else 33
                self.timer.start(interval)
                self.media_player.play()
                self.is_playing = True
        else:
            QMessageBox.warning(self, "Error", "NO VIDEO LOADED YET!")


    def seek_frame(self, position):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = position
            self.update_viewers(frame)
            ms_position = int(position / self.fps * 1000)
            self.media_player.setPosition(ms_position)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.current_frame += 1
            self.slider.setValue(self.current_frame)
            self.update_viewers(frame)
        else:
            self.timer.stop()
            self.media_player.stop()
            self.is_playing = False

    def detectSigns(self):
        if self.OpenCV_image2 is not None:
            self.ActualizarPixMap2(self.OpenCV_image2)
        else:
            QMessageBox.warning(self, "Error", "No VIDEO LOADED YET!")

    def update_viewers(self, frame):
        self.ActualizarPixMap(frame)
        self.ActualizarPixMap2(frame)
        # Store current frame for processing
        self.OpenCV_image2 = frame.copy()

    def ActualizarPixMap(self, image):
        display_width = self.viewer.width()
        display_height = self.viewer.height()
        resized = cv2.resize(image, (display_width, display_height))
        QImageTemp = QtGui.QImage(
            cv2.cvtColor(resized, cv2.COLOR_BGR2RGB),
            resized.shape[1],
            resized.shape[0],
            resized.shape[1] * 3,
            QtGui.QImage.Format.Format_RGB888
        )
        self.viewer.setPixmap(QtGui.QPixmap(QImageTemp))

    def ActualizarPixMap2(self, image):
        display_width = self.viewer2.width()
        display_height = self.viewer2.height()
        resized_image = cv2.resize(image, (display_width, display_height))
        qimage = QtGui.QImage(
            cv2.cvtColor(resized_image, cv2.COLOR_BGR2RGB),
            resized_image.shape[1],
            resized_image.shape[0],
            resized_image.shape[1] * 3,
            QtGui.QImage.Format.Format_RGB888
        )
        self.viewer2.setPixmap(QtGui.QPixmap(qimage))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = Window()
    window.setWindowTitle("Traffic Sign Detector")
    window.show()
    sys.exit(app.exec())