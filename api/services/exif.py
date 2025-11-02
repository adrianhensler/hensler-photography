"""
EXIF metadata extraction from images
"""
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import piexif
from datetime import datetime
from pathlib import Path


def extract_exif(image_path: str) -> dict:
    """
    Extract EXIF metadata from an image

    Returns:
    - camera_make, camera_model, lens
    - focal_length, aperture, shutter_speed, iso
    - date_taken, location (if GPS available)
    - width, height, aspect_ratio
    """

    try:
        img = Image.open(image_path)
        width, height = img.size
        aspect_ratio = round(width / height, 2)

        # Try to get EXIF data
        exif_dict = piexif.load(image_path)

        # Helper to get EXIF values
        def get_exif(ifd, key):
            try:
                return exif_dict[ifd].get(key)
            except:
                return None

        # Extract camera info
        camera_make = get_exif("0th", piexif.ImageIFD.Make)
        camera_model = get_exif("0th", piexif.ImageIFD.Model)
        lens = get_exif("Exif", piexif.ExifIFD.LensModel)

        # Decode bytes to strings
        if camera_make and isinstance(camera_make, bytes):
            camera_make = camera_make.decode('utf-8', errors='ignore').strip()
        if camera_model and isinstance(camera_model, bytes):
            camera_model = camera_model.decode('utf-8', errors='ignore').strip()
        if lens and isinstance(lens, bytes):
            lens = lens.decode('utf-8', errors='ignore').strip()

        # Extract exposure settings
        focal_length = get_exif("Exif", piexif.ExifIFD.FocalLength)
        if focal_length:
            focal_length = f"{focal_length[0] / focal_length[1]:.0f}mm" if isinstance(focal_length, tuple) else f"{focal_length}mm"

        aperture = get_exif("Exif", piexif.ExifIFD.FNumber)
        if aperture:
            aperture = f"f/{aperture[0] / aperture[1]:.1f}" if isinstance(aperture, tuple) else f"f/{aperture}"

        shutter_speed = get_exif("Exif", piexif.ExifIFD.ExposureTime)
        if shutter_speed:
            if isinstance(shutter_speed, tuple):
                if shutter_speed[0] < shutter_speed[1]:
                    shutter_speed = f"1/{shutter_speed[1] // shutter_speed[0]}s"
                else:
                    shutter_speed = f"{shutter_speed[0] / shutter_speed[1]:.1f}s"

        iso = get_exif("Exif", piexif.ExifIFD.ISOSpeedRatings)

        # Extract date
        date_taken = get_exif("Exif", piexif.ExifIFD.DateTimeOriginal)
        if date_taken and isinstance(date_taken, bytes):
            try:
                date_taken = date_taken.decode('utf-8')
                # Parse "2024:10:15 14:30:22" format
                date_taken = datetime.strptime(date_taken, "%Y:%m:%d %H:%M:%S").isoformat()
            except:
                date_taken = None

        # Extract GPS location
        location = None
        gps_data = exif_dict.get("GPS", {})
        if gps_data:
            try:
                lat = gps_data.get(piexif.GPSIFD.GPSLatitude)
                lat_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef)
                lon = gps_data.get(piexif.GPSIFD.GPSLongitude)
                lon_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef)

                if lat and lon:
                    # Convert to decimal degrees
                    def to_degrees(value):
                        d = value[0][0] / value[0][1]
                        m = value[1][0] / value[1][1]
                        s = value[2][0] / value[2][1]
                        return d + (m / 60.0) + (s / 3600.0)

                    lat_dec = to_degrees(lat)
                    lon_dec = to_degrees(lon)

                    if lat_ref == b'S':
                        lat_dec = -lat_dec
                    if lon_ref == b'W':
                        lon_dec = -lon_dec

                    location = f"{lat_dec:.6f}, {lon_dec:.6f}"
            except:
                pass

        return {
            "camera_make": camera_make,
            "camera_model": camera_model,
            "lens": lens,
            "focal_length": focal_length,
            "aperture": aperture,
            "shutter_speed": shutter_speed,
            "iso": iso,
            "date_taken": date_taken,
            "location": location,
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio
        }

    except Exception as e:
        print(f"EXIF extraction error: {e}")

        # Fallback: at least return dimensions
        try:
            img = Image.open(image_path)
            width, height = img.size
            return {
                "camera_make": None,
                "camera_model": None,
                "lens": None,
                "focal_length": None,
                "aperture": None,
                "shutter_speed": None,
                "iso": None,
                "date_taken": None,
                "location": None,
                "width": width,
                "height": height,
                "aspect_ratio": round(width / height, 2)
            }
        except:
            return {
                "camera_make": None,
                "camera_model": None,
                "lens": None,
                "focal_length": None,
                "aperture": None,
                "shutter_speed": None,
                "iso": None,
                "date_taken": None,
                "location": None,
                "width": None,
                "height": None,
                "aspect_ratio": None
            }
