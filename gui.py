import sys
import os
import shutil
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QFileDialog, QTextEdit, QProgressBar, QLabel, QHBoxLayout, QCheckBox)
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
from compressor import VideoCompressor

class VideoCompressorThread(QThread):
    progress_updated = pyqtSignal(int, str)
    compression_complete = pyqtSignal(bool, str)
    file_progress = pyqtSignal(int, int)

    def __init__(self, folder_path, keep_originals, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.keep_originals = keep_originals
        self.compressor = VideoCompressor(parent=self)
        self.compressor.compression_complete.connect(self.handle_compression_complete)
        self.compressor.progress_updated.connect(parent.update_progress)
        self.file_progress.connect(parent.update_file_count)

    def run(self):
        video_files = [f for f in os.listdir(self.folder_path) if self.compressor.is_video_file(f)] 
        files_to_compress = [f for f in video_files if self.compressor.get_file_size(os.path.join(self.folder_path, f)) > self.compressor.target_size_mb]
        
        total_files = len(files_to_compress)
        if total_files > 0:
            self.file_progress.emit(1, total_files) 
        for index, video_file in enumerate(files_to_compress):
            video_path = os.path.join(self.folder_path, video_file)
            
            success = self.compressor.compress_video(video_path, self.keep_originals)
            
            if not success:
                self.compression_complete.emit(False, f"Compression failed for {video_file}")

            self.file_progress.emit(index + 2, total_files)  
            
            # Emit progress update after compression is done
            self.progress_updated.emit(((index + 1) / total_files) * 100, video_file)
            
        self.compression_complete.emit(True, "\nAll files compressed successfully!\n")

    @pyqtSlot(bool, str)
    def handle_compression_complete(self, success, output):
        self.compression_complete.emit(success, output)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Compressor")
        self.setGeometry(100, 100, 800, 600)
        self.progress_info = QLabel("Compressing...")
        self.file_count_label = QLabel("0/0")
        self.progress_info.setVisible(False)
        self.file_count_label.setVisible(False)
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

        # Keep original checkbox
        self.keep_original_checkbox = QCheckBox("Keep original?") 
        self.keep_original_checkbox.setChecked(True)  
        main_layout.addWidget(self.keep_original_checkbox)

        progress_layout = QHBoxLayout()
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        # Progress information - initially hidden
        progress_layout.addWidget(self.progress_info) 

        # File count label - initially hidden
        progress_layout.addWidget(self.file_count_label)

        main_layout.addLayout(progress_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Stylesheet
        self.setStyleSheet(styles) 

        self.console_log.append("Welcome to Video Compressor!")

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.console_log.append(f"Selected folder: {folder_path}")
            self.thread = VideoCompressorThread(folder_path, self.keep_original_checkbox.isChecked(), self)
            self.thread.progress_updated.connect(self.update_progress)
            self.thread.compression_complete.connect(self.on_compression_complete)
            self.thread.file_progress.connect(self.update_file_count)  
            self.thread.start()
            # Show progress info and file count label when compression starts
            self.progress_info.setVisible(True)
            self.file_count_label.setVisible(True)

    @pyqtSlot(bool, str) 
    def on_compression_complete(self, success, message):
        self.append_to_console(message)
        if success:
            self.progress_bar.setValue(100)
        if message != "All files compressed successfully!":
            self.append_to_console(f"Saved to location: {self.thread.compressor.destination_path}")

    @pyqtSlot(str)
    def append_to_console(self, message):
        if message.startswith("Compression successful."):
            self.console_log.append(f"\n{message}\n")
        else:
            self.console_log.append(message)

    @pyqtSlot(int, int)
    def update_file_count(self, current_file, total_files): 
        # Update file count label and ensure it does not exceed total files
        current_file = min(current_file, total_files)
        self.file_count_label.setText(f"{current_file}/{total_files}")

    def update_progress(self, percentage):
        if percentage == 100:
            return
        self.progress_bar.setValue(percentage)

# Stylesheet  
styles = """ 
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
"""

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())