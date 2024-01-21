import os
import re
import shutil
import subprocess
from moviepy.editor import VideoFileClip
from PyQt5.QtCore import pyqtSignal, QProcess, QObject

class VideoCompressor(QObject):
    compression_complete = pyqtSignal(bool, str)
    progress_updated = pyqtSignal(int, str)

    def __init__(self, target_size_mb=25, max_quality_loss=5, parent=None):
        super().__init__(parent)
        self.target_size_mb = target_size_mb
        self.max_quality_loss = max_quality_loss
        self.destination_path = ""  # Initialize the attribute

    def is_video_file(self, filename):
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        return any(filename.lower().endswith(ext) for ext in video_extensions)

    def get_file_size(self, path):
        return os.path.getsize(path) / (1024 * 1024)  # Convert bytes to MB

    def get_video_duration(self, video_path):
        # Use ffprobe to get the duration of the video
        process = subprocess.Popen(['ffprobe', '-v', 'error', '-show_entries',
                                    'format=duration', '-of',
                                    'default=noprint_wrappers=1:nokey=1', video_path],
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out, _ = process.communicate()
        return float(out)

    def calculate_target_bitrate(self, duration, min_size_mb, max_size_mb):
        # Calculate the bitrate to achieve a file size within the target range
        min_bitrate = (min_size_mb * 8 * 1024) / duration  # in kilobits per second
        max_bitrate = (max_size_mb * 8 * 1024) / duration  # in kilobits per second
        return int((min_bitrate + max_bitrate) / 2)  # Return the average bitrate as an integer

    def compress_video(self, video_path, keep_originals):
        if not self.is_video_file(video_path):
            return False, ""

        original_size = self.get_file_size(video_path)
        if original_size <= self.target_size_mb:
            date_pattern = re.compile(r'Replay (\d{4})-(\d{2})-(\d{2})')
            date_match = date_pattern.search(video_path)
            if date_match:
                year, month, day = date_match.groups()
                date_folder = os.path.join(year, month, day)
                compressed_folder = os.path.join(os.path.dirname(video_path), 'compressed', date_folder)
                os.makedirs(compressed_folder, exist_ok=True)
                self.destination_path = os.path.join(compressed_folder, os.path.basename(video_path)) 
                shutil.move(video_path, self.destination_path)
                return True, f"File is already under the target size, moved to {self.destination_path}."

        clip = VideoFileClip(video_path)

        # Create a 'compressed' folder if it doesn't exist
        compressed_folder = os.path.join(os.path.dirname(video_path), 'compressed')
        os.makedirs(compressed_folder, exist_ok=True)

        date_pattern = re.compile(r'Replay (\d{4})-(\d{2})-(\d{2})')
        date_match = date_pattern.search(video_path)
        if date_match:
            year, month, day = date_match.groups()
            date_folder = f"{year}-{month}-{day}"
            compressed_folder = os.path.join(compressed_folder, date_folder)
            os.makedirs(compressed_folder, exist_ok=True)

        base, ext = os.path.splitext(os.path.basename(video_path))
        self.destination_path = os.path.join(compressed_folder, f"{base}_compressed{ext}")  # Set the attribute for compressed files

        process = QProcess()
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(lambda: self.read_output(process))
        process.finished.connect(lambda: self.process_finished())

        # Calculate the bitrate for the target size (20-25 MB range)
        duration = self.get_video_duration(video_path)
        target_bitrate = self.calculate_target_bitrate(duration, 20, 25)

        process.start('ffmpeg', [
            '-i', video_path,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-maxrate', f'{target_bitrate}k', '-bufsize', f'{2 * target_bitrate}k',
            '-pix_fmt', 'yuv420p',  
            '-c:a', 'aac', '-b:a', '128k', 
            '-movflags', '+faststart', 
            '-y', self.destination_path
        ])

        self.process = process
        self.clip = clip
        self.output = ""

        self.process.waitForFinished()

        return_code = self.process.exitCode()
        
        if return_code == 0:
            # After compression is done
            if keep_originals:
                # Move the original to the 'originals' folder
                originals_folder = os.path.join(os.path.dirname(video_path), 'originals', date_folder)
                os.makedirs(originals_folder, exist_ok=True)
                shutil.move(video_path, os.path.join(originals_folder, os.path.basename(video_path)))
            else:
                # Delete the original file
                os.remove(video_path)
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
