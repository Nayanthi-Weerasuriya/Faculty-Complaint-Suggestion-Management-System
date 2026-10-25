import os
import re
import subprocess
import tempfile
from django.conf import settings
import imageio_ffmpeg
from io import BytesIO
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

ALLOWED_VIDEO_EXTS = ['.mp4', '.mov', '.avi', '.mkv']
IMAGE_FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}


def validate_evidence(file):
    if not file:
        return file
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in list(IMAGE_FORMATS) + ALLOWED_VIDEO_EXTS:
        raise ValidationError('Use JPG, JPEG, PNG, WEBP, MP4, MOV, AVI, or MKV evidence.')
    if not file.size or file.size > 25 * 1024 * 1024:
        raise ValidationError('Evidence must be non-empty and no larger than 25 MB.')
    try:
        if ext in IMAGE_FORMATS:
            with Image.open(BytesIO(file.read())) as image:
                if image.format != IMAGE_FORMATS[ext]:
                    raise ValidationError('The image content does not match its extension.')
                image.verify()
        else:
            header = file.read(64)
            valid = ((ext in ['.mp4', '.mov'] and header[4:8] == b'ftyp')
                     or (ext == '.avi' and header[:4] == b'RIFF' and header[8:12] == b'AVI ')
                     or (ext == '.mkv' and header[:4] == b'\x1aE\xdf\xa3'))
            if not valid:
                raise ValidationError('The video content does not match a supported format.')
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, 'evidence' + ext)
                file.seek(0)
                with open(path, 'wb') as saved:
                    for chunk in file.chunks():
                        saved.write(chunk)
                try:
                    result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-i', path],
                                            capture_output=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                except (OSError, subprocess.TimeoutExpired, RuntimeError):
                    raise ValidationError('Video inspection failed. Please try another file.')
                details = result.stderr.decode('utf-8', errors='replace')
                duration = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', details)
                if not duration or 'Video:' not in details:
                    raise ValidationError('Upload a readable video with a valid duration and video stream.')
                seconds = int(duration[1]) * 3600 + int(duration[2]) * 60 + float(duration[3])
                limit = settings.MAX_VIDEO_DURATION_SECONDS
                if seconds <= 0 or seconds > limit:
                    raise ValidationError(f'Videos must be no longer than {limit} seconds.')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError('The uploaded image is invalid or damaged.')
    finally:
        file.seek(0)
    return file
