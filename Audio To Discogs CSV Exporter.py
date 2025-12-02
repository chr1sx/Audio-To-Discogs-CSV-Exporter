import os
import sys
import csv
import tempfile
import requests
from mutagen import File as MutagenFile
from pathlib import Path
from PIL import Image
from io import BytesIO

AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".oga", ".wav", ".aiff", ".aif",
    ".aac", ".m4a", ".mp4", ".wv", ".ape", ".mpc"
}

def get_tag(tags, *keys, default=""):
    for key in keys:
        if key in tags:
            value = tags[key]
            if isinstance(value, list):
                return value
            return [str(value)]
    return [default]

def resize_image(image_bytes, size=(600, 600)):
    try:
        with Image.open(BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail(size, Image.LANCZOS)
            output = BytesIO()
            img.save(output, format="JPEG", quality=90, subsampling=0)
            return output.getvalue()
    except Exception as e:
        print(f"Image resize failed: {e}")
        return image_bytes

def upload_to_litterbox(image_bytes):
    try:
        image_bytes = resize_image(image_bytes, (600, 600))
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            response = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                files={"fileToUpload": f},
                data={"reqtype": "fileupload", "time": "24h"}
            )

        os.remove(tmp_path)
        if response.status_code == 200 and response.text.startswith("https"):
            print(f"Uploaded image: {response.text.strip()}")
            return response.text.strip()
    except Exception as e:
        print(f"Upload failed: {e}")
    return "ImageUploadFailed"

def extract_embedded_artwork(audio):
    try:
        if not hasattr(audio, "tags"):
            return None
        if hasattr(audio, "pictures") and audio.pictures:
            return audio.pictures[0].data
        if "APIC:" in audio.tags:
            return audio.tags["APIC:"].data
        for tag in audio.tags.values():
            if hasattr(tag, "data"):
                return tag.data
    except Exception:
        pass
    return None

def find_external_image(folder):
    for file in os.listdir(folder):
        if file.lower().endswith((".jpg", ".jpeg", ".png")):
            return os.path.join(folder, file)
    return None

def process_folder(folder):
    folder_data = {
        "artist": None,
        "albums": set(),
        "label": None,
        "catno": "none",
        "format": "File",
        "genre": set(),
        "style": set(),
        "tracks": [],
        "date": None,
        "images": "ImageUploadFailed"
    }

    artwork_uploaded = False

    for root, _, files in os.walk(folder):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in AUDIO_EXTENSIONS:
                continue

            path = os.path.join(root, file)
            audio = MutagenFile(path, easy=True)
            if not audio or not audio.tags:
                continue

            if not artwork_uploaded:
                # 1️⃣ Try embedded artwork
                try:
                    full_audio = MutagenFile(path)
                    img_data = extract_embedded_artwork(full_audio)
                    if img_data:
                        folder_data["images"] = upload_to_litterbox(img_data)
                        artwork_uploaded = True
                except Exception:
                    pass

                # 2️⃣ If no embedded art, try external image file
                if not artwork_uploaded:
                    ext_img_path = find_external_image(root)
                    if ext_img_path:
                        with open(ext_img_path, "rb") as f:
                            folder_data["images"] = upload_to_litterbox(f.read())
                        artwork_uploaded = True

            tags = audio.tags
            artist_list = get_tag(tags, "artist", default="Unknown Artist")
            artist_str = ";".join(artist_list)
            album = get_tag(tags, "album", default=os.path.splitext(file)[0])[0]
            album_artist = get_tag(tags, "albumartist", "album artist", default=artist_str)[0]
            title = get_tag(tags, "title", default=os.path.splitext(file)[0])[0]
            genre = get_tag(tags, "genre", default="none")[0]
            style = get_tag(tags, "style", "styles", default="none")[0]
            label = get_tag(tags, "label", default=f"Not On Label ({album_artist} Self-released)")[0]
            catno = get_tag(tags, "catalog", "catno", "cat#", default="none")[0]
            date = get_tag(tags, "date", "year", default="Unknown")[0]

            if folder_data["artist"] is None:
                folder_data["artist"] = album_artist
            if folder_data["label"] is None:
                folder_data["label"] = label
            if folder_data["date"] is None:
                folder_data["date"] = date

            folder_data["albums"].add(album)
            folder_data["genre"].add(genre)
            folder_data["style"].add(style)

            length_str = ""
            if audio.info and audio.info.length:
                minutes = int(audio.info.length // 60)
                seconds = int(audio.info.length % 60)
                length_str = f" {minutes}:{seconds:02d}"

            track_artist_clean = artist_str.strip()
            album_artist_clean = album_artist.strip()

            if track_artist_clean == album_artist_clean:
                track_entry = f"{title}{length_str}"
            elif album_artist_clean in track_artist_clean:
                extras = track_artist_clean.replace(album_artist_clean, "").strip(" ;,")
                track_entry = f"{extras} — {title}{length_str}" if extras else f"{title}{length_str}"
            else:
                track_entry = f"{track_artist_clean} — {title}{length_str}"

            folder_data["tracks"].append(track_entry)

    combined_album = " / ".join(folder_data["albums"])
    combined_genre = ", ".join(sorted(folder_data["genre"]))
    combined_style = ", ".join(sorted(folder_data["style"]))

    return {
        "artist": folder_data["artist"],
        "title": combined_album,
        "label": folder_data["label"],
        "catno": folder_data["catno"],
        "format": folder_data["format"],
        "genre": combined_genre,
        "style": combined_style,
        "tracks": "\n".join(folder_data["tracks"]),
        "date": folder_data["date"],
        "images": folder_data["images"]
    }

def save_individual_csv(folder_data, desktop):
    safe_artist = "".join(c for c in folder_data["artist"] if c.isalnum() or c in " _-").strip()
    safe_album = "".join(c for c in folder_data["title"] if c.isalnum() or c in " _-").strip()
    safe_date = folder_data["date"]

    filename = f"{safe_artist} - {safe_album} ({safe_date}).csv"
    filepath = os.path.join(desktop, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["artist", "title", "label", "catno", "format", "genre", "style", "tracks", "date", "images"])
        writer.writerow([
            folder_data["artist"],
            folder_data["title"],
            folder_data["label"],
            folder_data["catno"],
            folder_data["format"],
            folder_data["genre"],
            folder_data["style"],
            folder_data["tracks"],
            folder_data["date"],
            folder_data["images"]
        ])

    print(f"CSV saved: {filepath}")

def save_combined_csv(all_folder_data, desktop):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Combined CSV ({timestamp}).csv"
    filepath = os.path.join(desktop, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["artist", "title", "label", "catno", "format", "genre", "style", "tracks", "date", "images"])
        
        for folder_data in all_folder_data:
            writer.writerow([
                folder_data["artist"],
                folder_data["title"],
                folder_data["label"],
                folder_data["catno"],
                folder_data["format"],
                folder_data["genre"],
                folder_data["style"],
                folder_data["tracks"],
                folder_data["date"],
                folder_data["images"]
            ])

    print(f"Combined CSV saved: {filepath}")

def find_album_folders(root_folder):
    """Find all folders that contain audio files (album folders)"""
    album_folders = []
    
    for dirpath, dirnames, filenames in os.walk(root_folder):
        # Check if current folder has audio files
        has_audio = any(os.path.splitext(f)[1].lower() in AUDIO_EXTENSIONS for f in filenames)
        
        if has_audio:
            album_folders.append(dirpath)
            # Don't traverse into subfolders of album folders
            dirnames.clear()
    
    return album_folders

def main():
    if len(sys.argv) < 2:
        print("Drag and drop one or more folders onto this script.")
        return

    desktop = str(Path.home() / "Desktop")
    folders = sys.argv[1:]
    
    # Find all album folders (folders containing audio files)
    all_album_folders = []
    for folder in folders:
        album_folders = find_album_folders(folder)
        if album_folders:
            all_album_folders.extend(album_folders)
        else:
            # No audio found, but add the folder anyway
            all_album_folders.append(folder)

    # If only one album folder, just process it
    if len(all_album_folders) == 1:
        print(f"Processing folder: {all_album_folders[0]}")
        folder_data = process_folder(all_album_folders[0])
        save_individual_csv(folder_data, desktop)
        return

    # Multiple folders - offer choice
    print(f"\nFound {len(all_album_folders)} folders to process\n")
    
    while True:
        print("Choose an option:")
        print("1. Generate separate CSV for each folder")
        print("2. Combine all folders into one CSV")
        print()
        
        choice = input("Enter your choice (1 or 2): ").strip()

        if choice == "1":
            print("\nProcessing folders individually...\n")
            for folder in all_album_folders:
                print(f"Processing: {folder}")
                folder_data = process_folder(folder)
                save_individual_csv(folder_data, desktop)
            print(f"\nGenerated {len(all_album_folders)} CSV files!")
            break
        
        elif choice == "2":
            print("\nProcessing and combining folders...\n")
            all_folder_data = []
            for folder in all_album_folders:
                print(f"Processing: {folder}")
                folder_data = process_folder(folder)
                all_folder_data.append(folder_data)
            save_combined_csv(all_folder_data, desktop)
            print(f"\nCombined {len(all_album_folders)} folders into one CSV!")
            break
        
        else:
            print("\nInvalid choice. Please enter 1 or 2.\n")

if __name__ == "__main__":
    main()
