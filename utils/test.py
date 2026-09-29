import cv2
import pytesseract
import re

image_path=r"C:\Users\Lenovo\Desktop\Aadhaar Masking\rotated_images\12_v4_ds.jpg" 

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def correct_image_orientation(image_path):

    image = cv2.imread(image_path)
    if image is None:
        return None

    try:
        osd = pytesseract.image_to_osd(image)

        angle = int(re.search(r'(?<=Rotate: )\d+', osd).group(0))
        print(f"[INFO] IMAGE IS ROTATED BY {angle}°")
    except Exception as e:
        print(f"[ERROR] CANNOT IDENTIFY ORIENTATION, DEFAULT TO MODEL ANGLE. error: {e}")
        return image_path, False

    if angle == 90:
        corrected_img = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        corrected_img = cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        corrected_img = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        corrected_img = image

    return corrected_img, True

correct_image_orientation(image_path)