<div align="center">

# Audio To Discogs CSV Exporter

[![Download Script](https://img.shields.io/badge/Download%20Script-blue?style=for-the-badge)](https://github.com/chr1sx/Audio-To-Discogs-CSV-Exporter/archive/refs/heads/main.zip)

*A Python script that creates CSVs from your music folders,   
reading tags from multiple audio formats.*

</div>

---

## Features

- Supports common audio formats: MP3, FLAC, OGG, WAV, AIFF, AAC, M4A, MP4, WV, APE, MPC
- Reads metadata tags: Artist, Album, Album Artist, Track Title, Genre, Style, Label, Catalog Number, Year
- Handles multi-artist tracks: extra artists are clearly shown with an em dash (—) before the track title
- Automatic subfolder detection: Detects album folders at any depth and processes each separately
- Processing modes:
  - Generate individual CSV for each album folder
  - Combine all albums into one CSV file
- Supports cover images:
  - Extracts embedded artwork if available, or falls back to artwork in the folder
  - Resizes image to 600×600 and uploads to Litterbox
- Defaults for missing metadata:
  - Label: Not On Label (Artist Self-released)
  - Catalog Number: none
  - Format: File
- CSV is automatically named:
  - Individual: Artist - Album (Date).csv
  - Combined: Combined CSV (YYYYMMDD_HHMMSS).csv
- Files are saved to your Desktop

---

## Installation

1. Install Python 3.
2. Install required packages: `pip install mutagen pillow requests`

---

## Usage

1. [Download the script](https://github.com/chr1sx/Audio-To-Discogs-CSV-Exporter/archive/refs/heads/main.zip).
2. Drag and drop one or more music folders onto the script file.
3. CSV files will appear on your Desktop, ready to use.
4. [Upload your CSV files on Discogs](https://www.discogs.com/release/csv_to_draft).
5. **Optional** - Use this in combination with [**Discogs Edit Helper**](https://github.com/chr1sx/Discogs-Edit-Helper/),  
since Discogs CSV files don’t include duration or artist (VA) fields by default.

---
