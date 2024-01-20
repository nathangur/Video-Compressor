# Video-Compressor
A simple video compressor made to compress videos to under 25mb to fit into discord. Designed to compress video files in a selected folder to reduce their file size to under 25 MB. The goal is to achieve this reduction with minimal quality loss, targeting an average video size reduction from 50 MB to 25 MB.

## Features

- Scans a specified directory for video files.
- Compresses video files to a target size of 25 MB or less.
- Supports various video formats including MP4, AVI, MOV, MKV, FLV, and WMV.
- Ensures efficient and quick compression with minimal quality loss.

## Usage

The video compressor will check a video file for a date format such as year -> month -> day. Once the date has been parsed, a new folder will be created where you selected the video file to be converted called "compressed". The date will then be taken to make a new folder that is year -> month -> day. 

There is an option to keep the original files. If selected (on by default) the original files will be moved from the selected folder into a new folder called "originals" and organized by the date. If this option is not selected, the original files will be deleted after being compressed.
