import os, cv2, sys, re
from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QUrl, QLoggingCategory
from PyQt6.QtWidgets import QHBoxLayout, QMessageBox, QSlider
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from moviepy import VideoFileClip

##pip install moviepy TODO: OCUPAN ESTO

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
        self.subtitles = []

        self._path = None

        self.viewer = MiEtiqueta()
        self.viewer2 = MiEtiqueta()
        self.viewer.setFixedSize(800, 680)
        self.viewer2.setFixedSize(800, 680)
        self.viewer.setScaledContents(True)
        self.viewer2.setScaledContents(True)

        self.buttonOpen = QtWidgets.QPushButton("Select Video")
        BUTTON_SIZE = QSize(200, 50)
        self.buttonOpen.setMinimumSize(BUTTON_SIZE)
        self.buttonOpen.clicked.connect(self.handleOpen)

        self.elements = []

        self.procesarImagenEntrada = QtWidgets.QPushButton("Play/Pause")
        self.procesarImagenEntrada.setMinimumSize(BUTTON_SIZE)
        self.procesarImagenEntrada.clicked.connect(self.toggle_playback)

        self.guardarImagen = QtWidgets.QPushButton("Save Video")
        self.guardarImagen.setMinimumSize(BUTTON_SIZE)
        self.guardarImagen.clicked.connect(self.handleSaveFile)

        layout = QtWidgets.QGridLayout(self)
        self.botonProcesaReservado = QtWidgets.QPushButton("Select SRT")
        self.botonProcesaReservado.setMinimumSize(BUTTON_SIZE)
        self.botonProcesaReservado.clicked.connect(self.handleOpenSRT)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.buttonOpen)
        button_layout.addWidget(self.procesarImagenEntrada)
        button_layout.addWidget(self.botonProcesaReservado)
        button_layout.addWidget(self.guardarImagen)

        self.srt_display = QtWidgets.QTextEdit()
        self.srt_display.setReadOnly(True)
        self.srt_display.setFixedSize(150,680)

        layout.addLayout(button_layout, 0, 0, 1, 4)
        layout.addWidget(self.viewer, 1, 0, 1, 2)
        layout.addWidget(self.viewer2, 1, 2, 1, 2)
        layout.addWidget(self.srt_display, 1, 4, 2, 1)

        self.cap = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30

        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        layout.addWidget(self.slider, 2, 0, 1, 2)
        self.slider.sliderMoved.connect(self.seek_frame)

        Tamano = (self.viewer.size().width(), self.viewer.size().height())

        print(self.viewer.size(), type(self.viewer.size()), Tamano)

    def handleOpenSRT(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose SRT File", ".", "Subtitles (*.srt)"
        )
        if path:
            with open(path, "r", encoding="utf-8") as file:
                srt_content = file.read()
                self.parse_srt(path)
                self.srt_display.setPlainText(srt_content)

    def parse_srt(self, path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                srt_content = file.read()
            pattern = r"(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\Z)"
            matches = re.finditer(pattern, srt_content, re.DOTALL)
            self.subtitles = []
            for match in matches:
                start_time = self.srt_time_to_ms(match.group(2))
                end_time = self.srt_time_to_ms(match.group(3))
                text = match.group(4).replace("\n", " ")
                self.subtitles.append((start_time, end_time, text))
        except Exception as e:
            QMessageBox.critical(self, "SRT Error", f"Invalid subtitle format: {str(e)}")
            self.subtitles = []
            return

    def srt_time_to_ms(self, time_str):
        h, m, s_ms = time_str.split(":")
        s, ms = s_ms.split(",")
        return (int(h) * 3600 + int(m) * 60 + int(s)) * 1000 + int(ms)


    def handleSaveFile(self):
        if self.cap is None or not self.cap.isOpened():
            QMessageBox.warning(self, "Error", "Nothing to save yet!.")
            return
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Video", "output.mp4", "Videos (*.mp4)")
        if not fileName:
            return
        temp_video = "temp_video.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        out = cv2.VideoWriter(temp_video, fourcc, fps, (frame_width, frame_height))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            timestamp_ms = int(self.cap.get(cv2.CAP_PROP_POS_MSEC))
            frame = self.add_subtitle_to_frame(frame, timestamp_ms)
            out.write(frame)
        out.release()
        original_clip = VideoFileClip(self._path)
        processed_clip = VideoFileClip(temp_video)
        final_clip = processed_clip.with_audio(original_clip.audio)
        final_clip.write_videofile(fileName, codec="libx264", audio_codec="aac")
        os.remove(temp_video)
        QMessageBox.information(self, "Success", "Video saved successfully!")

    def handleOpen(self):
        start = "."
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose Video", start, "Videos(*.mp4)"
        )
        if path:
            self._path = path
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Error", "Could not open video file")
                return
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.slider.setMaximum(self.total_frames - 1)
            self.media_player.setSource(QUrl.fromLocalFile(path))
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = 0
                self.ActualizarPixMap(frame)
                self.ActualizarPixMap2(frame)
                self.OpenCV_image2 = frame.copy()

    def toggle_playback(self):
        if self.cap is not None and self.cap.isOpened():
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
            QMessageBox.warning(self, "Error", "No video loaded yet!")

    def seek_frame(self, position):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
        ret, original_frame = self.cap.read()
        if ret:
            self.current_frame = position
            ms_position = int(position / self.fps * 1000)
            subtitle_frame = self.add_subtitle_to_frame(original_frame.copy(), ms_position)
            self.ActualizarPixMap(original_frame)
            self.ActualizarPixMap2(subtitle_frame)
            self.media_player.setPosition(ms_position)
            self.OpenCV_image2 = subtitle_frame.copy()

    def update_frame(self):
        ret, original_frame = self.cap.read()
        if ret:
            self.current_frame += 1
            self.slider.setValue(self.current_frame)
            timestamp = int(self.media_player.position())
            subtitle_frame = self.add_subtitle_to_frame(original_frame.copy(), timestamp)
            self.ActualizarPixMap(original_frame)
            self.ActualizarPixMap2(subtitle_frame)
            self.OpenCV_image2 = subtitle_frame.copy()
        if self.current_frame >= self.total_frames - 1:
            self.timer.stop()
            self.media_player.stop()
            self.is_playing = False

    def add_subtitle_to_frame(self, frame, timestamp):
        for start, end, text in self.subtitles:
            if start <= timestamp <= end:
                return self.draw_text_on_frame(frame, text) #si si tiene
        return frame #si no tiene

    def draw_text_on_frame(self, frame, text):
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        font_thickness = 1
        text_color = (255, 255, 255)
        outline_color = (0, 0, 0)
        max_width = frame.shape[1] - 100
        wrapped_text = self.wrap_text(text, font, font_scale, font_thickness, max_width)
        text_height = cv2.getTextSize("A", font, font_scale, font_thickness)[0][1]
        total_height = len(wrapped_text) * (text_height + 5)
        text_x = frame.shape[1] // 2
        text_y = frame.shape[0] - 60 - total_height
        for i, line in enumerate(wrapped_text):
            y_offset = text_y + i * (text_height + 5)
            text_size = cv2.getTextSize(line, font, font_scale, font_thickness)[0]
            x_offset = text_x - (text_size[0] // 2)
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                cv2.putText(frame, line, (x_offset + dx, y_offset + dy), font, font_scale, outline_color,
                            font_thickness + 1, cv2.LINE_AA)
            cv2.putText(frame, line, (x_offset, y_offset), font, font_scale, text_color, font_thickness, cv2.LINE_AA)
        return frame

    def wrap_text(self, text, font, font_scale, font_thickness, max_width):
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            text_size = cv2.getTextSize(test_line, font, font_scale, font_thickness)[0]
            if text_size[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def update_viewers(self, frame):
        self.ActualizarPixMap(frame)
        self.ActualizarPixMap2(frame)

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
    window.setWindowTitle("Video Subtitler")
    window.show()
    sys.exit(app.exec())