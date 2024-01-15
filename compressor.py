import os
import re
from moviepy.editor import VideoFileClip
from PyQt5.QtCore import pyqtSignal, QProcess, QObject

class VideoCompressor(QObject):
    compression_complete = pyqtSignal(bool, str)  # Signal for completion message
    progress_updated = pyqtSignal(int, str)  # Signal for progress updates

    def __init__(self, target_size_mb=25, max_quality_loss=5, parent=None):
        super().__init__(parent)
        self.target_size_mb = target_size_mb
        self.max_quality_loss = max_quality_loss

    def is_video_file(self, filename):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        return any(filename.lower().endswith(ext) for ext in video_extensions)

    def get_file_size(self, path):
        return os.path.getsize(path) / (1024 * 1024)  # Convert bytes to MB

    def compress_video(self, video_path):
        if not self.is_video_file(video_path):
            return False, ""

        original_size = self.get_file_size(video_path)
        if original_size <= self.target_size_mb:
            return True, ""  # No need to compress

        clip = VideoFileClip(video_path)

        # Create a 'compressed' folder if it doesn't exist
        compressed_folder = os.path.join(os.path.dirname(video_path), 'compressed')
        os.makedirs(compressed_folder, exist_ok=True)

        # Construct output file path inside the 'compressed' folder
        base, ext = os.path.splitext(os.path.basename(video_path))
        output_path = os.path.join(compressed_folder, f"{base}_compressed{ext}")

        # Compress video using ffmpeg
        process = QProcess()
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(lambda: self.read_output(process))
        process.finished.connect(lambda: self.process_finished())

        process.start('ffmpeg', [
            '-i', video_path,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-pix_fmt', 'yuv420p',  
            '-c:a', 'aac', '-b:a', '128k', 
            '-movflags', '+faststart', 
            '-y', output_path
        ])

        self.process = process
        self.clip = clip
        self.output = ""

        self.process.waitForFinished()

        return_code = self.process.exitCode()
        
        if return_code == 0:
            return True, "Compression successful."
        else: 
            return False, f"Compression failed with return code {return_code}"

    def read_output(self, process):
        data = process.readAllStandardOutput().data().decode().strip() 
        self.output += data

        # Parse progress but don't emit data
        frame_progress = self.parse_frame_progress(data)
        if frame_progress is not None:
            self.progress_updated.emit(frame_progress, "")

    def parse_frame_progress(self, ffmpeg_output):
        # Regex to match the timecode (format: hh:mm:ss) 
        timecode_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})')
        match = timecode_pattern.search(ffmpeg_output)
        if match:
            hours, minutes, seconds = map(int, match.groups())
            current_time = hours * 3600 + minutes * 60 + seconds
            total_time = self.clip.duration
            progress = (current_time / total_time) * 100
            return min(int(progress), 100)
        return None

    def process_finished(self):
        return_code = self.process.exitCode()
        self.clip.close()
        if return_code == 0:
            success = True
            message = "Compression successful."
        else:
            success = False
            message = f"Compression failed with return code {return_code}"
        self.compression_complete.emit(success, message)
