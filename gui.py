import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QTextEdit, QProgressBar, QLabel, QHBoxLayout)
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
from compressor import VideoCompressor

class VideoCompressorThread(QThread):
    progress_updated = pyqtSignal(int, str)  # Signal for progress updates
    compression_complete = pyqtSignal(bool, str)  # Signal for completion message
    file_progress = pyqtSignal(int, int)  # Signal for file count

    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.compressor = VideoCompressor(parent=self)
        self.compressor.compression_complete.connect(self.handle_compression_complete)
        self.compressor.progress_updated.connect(parent.update_progress)

    def run(self):
        video_files = [f for f in os.listdir(self.folder_path) if self.compressor.is_video_file(f)] 
        files_to_compress = [f for f in video_files if self.compressor.get_file_size(os.path.join(self.folder_path, f)) > self.compressor.target_size_mb]
        
        for index, video_file in enumerate(files_to_compress):
            video_path = os.path.join(self.folder_path, video_file)
            
            success, output = self.compressor.compress_video(video_path)
            
            if not success:
                self.compression_complete.emit(False, f"Compression failed for {video_file}")
                
            self.file_progress.emit(index + 1, len(files_to_compress))
            
        self.compression_complete.emit(True, "All compressions finished.")

    @pyqtSlot(bool, str)
    def handle_compression_complete(self, success, output):
        self.compression_complete.emit(success, output)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Compressor")
        self.setGeometry(100, 100, 800, 600)  # Set window size
        self.initUI()

    def initUI(self):
        # Main layout
        main_layout = QVBoxLayout()

        # Console log
        self.console_log = QTextEdit()
        self.console_log.setReadOnly(True)
        main_layout.addWidget(self.console_log)

        # Folder selection button
        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.select_folder)
        main_layout.addWidget(self.folder_button)

        # Progress bar and information
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_info = QLabel("0%")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.progress_info)
        self.file_count_label = QLabel("0/0")  # File count
        progress_layout.addWidget(self.file_count_label)
        main_layout.addLayout(progress_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.setStyleSheet("""
            QWidget {
                color: #dcdcdc;
                background-color: #2d2d2d;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #3A3939;
                padding: 5px;
                border-radius: 2px;
                outline: none;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QPushButton:pressed {
                background-color: #5d5d5d;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: None;
            }
            QProgressBar {
                border: 2px solid #3A3939;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #6897bb;
                width: 20px;
            }
            QLabel {
                qproperty-alignment: 'AlignLeft | AlignVCenter';
            }
        """)

        self.console_log.append("Welcome to Video Compressor!")

    def select_folder(self):
        # Open a dialog to select a folder
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            # Update the console log with the selected folder path
            self.console_log.append(f"Selected folder: {folder_path}")
            # Create a thread to compress videos in the selected folder
            self.thread = VideoCompressorThread(folder_path, self)
            self.thread.progress_updated.connect(self.update_progress)
            self.thread.compression_complete.connect(self.on_compression_complete)
            self.thread.file_progress.connect(self.update_file_count)
            self.thread.start()

    @pyqtSlot(bool, str)
    def on_compression_complete(self, success, message):
        self.append_to_console(message)
        self.progress_bar.setValue(100)  # Update the progress bar to 100%
        self.progress_info.setText("Done")
        self.console_log.append(f"Saved to location: {self.thread.folder_path}")

    @pyqtSlot(str)
    def append_to_console(self, message):
        self.console_log.append(message)

    def update_file_count(self, current, total):
        self.file_count_label.setText(f"{current}/{total}")  # Update file count label

    def update_progress(self, percentage, info):

        if percentage == 100:
            return
        
        self.progress_bar.setValue(percentage)
        
        if info:
            self.progress_info.setText(info)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())