import io,os, re
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import torch
import easyocr
import pytesseract
import cv2, gc
import math
import base64
import warnings
import numpy as np
import logging
from PIL import Image
from io import BytesIO
from pdf2image import convert_from_bytes
from collections import deque
from ultralytics import YOLO
from config.logging_config import setup_logger

warnings.filterwarnings("ignore")

logging = setup_logger()

torch.set_num_threads(1)

primary_reader = easyocr.Reader(['en'], gpu=False, detector='dbnet18',  verbose=False)
devnagiri_reader = easyocr.Reader(['en','hi','mr'], gpu=False, detector='dbnet18',  verbose=False)
final_reader = None
# secondary_reader = easyocr.Reader(['en', 'ta', 'te', "kn", "bn"], gpu=False, detector='dbnet18',  verbose=False)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

canvas_size=1920
mag_ratio=1.5

# Pre-compile pattern and freeze anchor set at module level — done once, not per call
AADHAAR_ANCHORS = frozenset([
    "unique identification", "authority of india",
    "erwolment mo", "enrollment no", "male", "female", "aadhaa", "aadhaar", "qr code",
    "aadhoar nc", "aadhaar number", "aadhaar no", "aadhoar no", "aadhoar number",
    "aadhoar nomber", "aadhoar nombor", "mera aadhaar meri pehacham", "your aadhaar no", "आधार", "आथार", "आभार",
    "फहचान", "षहचान", "मारतीय", "भारतीय विशिष्ट पहचान प्राधिकरण", "विशिष्ट",
    "प्राधिकरण", "सामान्य", "माणसाचा", "अधिकार", "कार्ड", "ओळख", "भारतीय",
    "पहचान", "प्राधिकरन", "भारत सरकार"
])

NEGATIVE_ANCHORS = frozenset([
   'income tax department', 'income', 'tax', 'department', 
   'permanent account number', 'permanent', 'account', 'number', 'indian union driving licence', 
   'indian', 'union', 'driving', 'licence', 'union of india driving licence', 
   'आयकर   विभाग', 'आयकर', 'विभाग','1800 300 1947' '1800', '300', '1947'
])

skip_keywords = ["vid", "vd", "date", "birth", "address", "/", "\\", "|", "!", "1800", "1888", "3888", "1000", "300", "1947", "1047"]

QUARTLET_PATTERN = re.compile(r"\b\d{4}[.\s\-\/]{1,3}\d{4}[.\s\-\/]{1,3}\d{4}\b")
# PARTIAL_QUARTLET_PATTERN = re.compile(r"\b\d{4}[\W_]?\d{4}\b")

# CLAHE instance created once at module level — expensive to recreate per call
CLAHE = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

MAX_PIXELS = 800 * 800 

classification_model = YOLO(".\\models\\classification_model.pt")
boundary_detection_model = YOLO(".\\models\\detection_model.pt")

CONF_THRESHOLD = 0.80 
NMS_THRESHOLD = 0.15 

THRESHOLDS = {
    "aadhar_cards": 0.65, 
    "mixed_docs": 0.65,   
    "other_docs": 0.85     
}

def mask_aadhaar_image(bytes_data, mimetype, doc_name, page):
    page = int(page)
    # start_time = time.time()
    is_masked = False
    aadhar_cards_count = 0
    mixed_docs_count = 0
    other_docs_count = 0
    masked_images_array = []
    masked_page_numbers = []
    unmasked_page_numbers = []
    partially_masked_page_numbers = []

    try:
        if mimetype in ('tiff', 'tif', 'pdf'):
            try:
                print(f"File extension detected: {mimetype} File {doc_name} processing started ------------------------->")
                
                if mimetype in ('tif', 'tiff'):
                    is_tiff = True
                    pages, original_mode, original_dpi, original_compression = separate_tiff_pages(bytes_data)
                else:
                    is_tiff = False
                    original_mode = 'RGB'
                    original_dpi = (200, 200)
                    pages = process_base64_pdf(bytes_data)

                for i, frame in enumerate(pages):

                    if is_tiff:
                        original_frame = frame.copy()  
                        # frame = frame.convert("RGB")
                        frame_np = np.array(frame)
                    else:
                        frame_np = frame
                        original_frame = Image.fromarray(cv2.cvtColor(frame_np, cv2.COLOR_BGR2RGB))
                    
                    # if i < page or i > page:
                        # continue

                    masked_image, masked, is_aadhaar, confidence, class_name, is_mixed_docs = process_image(frame_np)
                    pil_image = Image.fromarray(cv2.cvtColor(masked_image, cv2.COLOR_BGR2RGB))

                    if not isinstance(masked_image, np.ndarray):
                        logging.error(f"process_image returned invalid image at page { i+1 }")
                        continue
                    
                    if class_name in ('aadhar_cards'):
                        aadhar_cards_count += 1
                    elif class_name in ('mixed_docs'):
                        mixed_docs_count += 1
                    else:
                        other_docs_count += 1

                    if masked == 1 and is_aadhaar:
                        is_masked = True
                        masked_images_array.append(make_save_ready(pil_image, original_mode))
                        masked_page_numbers.append(i + 1)
                        print(f"#### page number {i + 1} is fully masked ####")

                    elif masked == -1 and is_aadhaar:
                        is_masked=True
                        masked_images_array.append(make_save_ready(pil_image, original_mode))
                        partially_masked_page_numbers.append(i + 1)
                        print(f"#### page number {i + 1} is partially masked ####")

                    elif masked == 0 and is_aadhaar:
                        masked_images_array.append(make_save_ready(original_frame, original_mode))
                        if is_mixed_docs and confidence >= 0.80:
                            pass
                        elif confidence >= 0.90:
                            unmasked_page_numbers.append(i + 1)
                        print(f"#### page number {i + 1}, is maybe a aadhaar card but it's unmasked ####")

                    else:
                        masked_images_array.append(make_save_ready(original_frame, original_mode))
                        print(f"#### page number {i + 1} is unmasked ####")

                    del frame, masked_image, pil_image
                    gc.collect()

                if is_masked:
                    # end_time = time.time()
                    # time_taken_single = round(end_time - start_time, 2)
                    output_buffer = BytesIO()

                    if is_tiff:
                        compression = get_compression(original_mode, original_compression)
                        masked_images_array[0].save(output_buffer,format='TIFF',save_all=True, append_images=masked_images_array[1:], compression=compression, dpi=original_dpi)
                    else:
                        masked_images_array[0].save(output_buffer, format='PDF', save_all=True, append_images=masked_images_array[1:])

                    masked_image_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                
                    if masked_page_numbers and unmasked_page_numbers and partially_masked_page_numbers:
                        remark = "Recommended to review UNMASKED & PARTIALLY MASKED AADHAAR page numbers"
                    
                    elif unmasked_page_numbers and partially_masked_page_numbers:
                        remark = "Recommended to review UNMASKED & PARTIALLY MASKED AADHAAR page numbers"
                    
                    elif unmasked_page_numbers:
                        remark = "Recommended to review UNMASKED AADHAAR page numbers"
                    
                    elif partially_masked_page_numbers:
                        remark = "Recommended to review PARTIALLY MASKED AADHAAR page numbers"
                    
                    else:
                        remark = "Recommended to review MASKED AADHAAR page numbers"

                    return {"status": "masked","masked_image_base64": masked_image_base64,"masked_page_numbers": masked_page_numbers,"unmasked_page_numbers": unmasked_page_numbers,"partially_masked_page_numbers": partially_masked_page_numbers, "remark": remark}
                
                else:
                    # end_time = time.time()
                    # time_taken_single = round(end_time - start_time, 2)
                    if unmasked_page_numbers: 
                        return {"status": "unmasked", "unmasked_page_numbers": unmasked_page_numbers, "remark":"Recommended to review UNMASKED AADHAAR page numbers"}
                    else:
                        return {"status": "unmasked", "unmasked_page_numbers": unmasked_page_numbers, "remark":"Model didn't classified document as Aadhaar card"}

            except Exception as err:
                logging.error(f"Error processing TIFF / PDF: {err}")
                return {"status": "unmasked", "masked_image_base64": None, "masked_page_numbers": "","unmasked_page_numbers": "","partially_masked_page_numbers": "", "remark": err}
    
        else:
            try:
                print(f"File extension detected: {mimetype} File {doc_name} processing started ------------------------->")
                input_stream = io.BytesIO(bytes_data)
                image = Image.open(input_stream)
                image_cv2 = ensure_correct_channels(image)
                image_cv2 = downscale_and_denoise(image_cv2)               
                masked_image, masked, is_aadhaar, confidence, class_name, is_mixed_docs = process_image(image_cv2)
                
                if class_name in ('aadhar_cards'):
                    aadhar_cards_count += 1
                elif class_name in ('mixed_docs'):
                    mixed_docs_count += 1
                else:
                    other_docs_count += 1

                if masked == 1 and is_aadhaar:
                    _, buffer = cv2.imencode('.jpg', masked_image)
                    masked_image_base64 = base64.b64encode(buffer).decode('utf-8')
                    return {"status": "masked", "masked_image_base64": masked_image_base64, "masked_page_numbers": "1", "remark":"Since model found 2 aadhaar numbers, it can be considered as fully masked"}
                
                elif masked == -1 and is_aadhaar:
                    _, buffer = cv2.imencode('.jpg', masked_image)
                    masked_image_base64 = base64.b64encode(buffer).decode('utf-8')
                    return {"status": "masked", "masked_image_base64": masked_image_base64, "masked_page_numbers": "1", "remark":"Model found less than 2 or more than 3 aadhaar numbers. Recommended to review MASKED AADHAAR page numbers"}
                
                elif masked == 0 and is_aadhaar:
                    print("Current jpeg, jpg or png image is maybe a aadhaar but it's unmasked")
                    return {"status": "unmasked", "unmasked_page_numbers": "1","remark":"Model classified few pages as aadhaar cards but unable to detect aadhaar number. Recommended to review UNMASKED AADHAAR page numbers"}
                
                else:
                    print("Current jpeg, jpg or png image is unmasked")
                    return {"status": "unmasked", "remark":"Model did not classify document as Aadhaar card"}

            except Exception as err:
                logging.error(f"Error processing JPEG, JPG, PNG: {err}")
                return {"status": "unmasked", "masked_image_base64": None, "masked_page_numbers": "","unmasked_page_numbers": "","partially_masked_page_numbers": "", "remark": err}
            
            finally:
                del image_cv2            
                gc.collect()                                       
    
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"status": "unmasked", "masked_image_base64": None, "masked_page_numbers": "","unmasked_page_numbers": "","partially_masked_page_numbers": "", "remark": err}
    
    finally:
        masked_images_array.clear()
        gc.collect()
        print(f"File {doc_name} has been processed successfully and has {aadhar_cards_count} aadhaar cards, {mixed_docs_count} mixed docs and {other_docs_count} other docs ----------------------------------->")


def process_image(frame_np):
    masked=0
    is_aadhaar=False
    is_mixed_docs=False
    aadhaar_anchors_present=False
    frame_cv2 = cv2.cvtColor(frame_np, cv2.COLOR_RGB2BGR)
    # frame_cv2 = downscale_and_denoise(frame_np)
    frame_cv2 = cv2.bilateralFilter(frame_cv2, 9, 75, 75)
    class_name, confidence, is_aadhaar, angle, entropy, is_mixed_docs = classify_image(frame_cv2)
    
    print(f"Classification model response Class_name: {class_name} and confidence:- {confidence} and image is_aadhaar is {is_aadhaar}, angle is {angle} and entropy is {round(entropy, 4)}")
    
    if is_aadhaar:
        corrected_image , is_corrected = correct_image_orientation(frame_cv2)

        if is_corrected:
            aadhaar_anchors_present = check_ocr_or_quartlet_after_rotation(corrected_image, -1)
            print(f"aadhaar_anchors_present in check_ocr_or_quartlet_after_rotation:- {aadhaar_anchors_present}")
    
        if aadhaar_anchors_present:
            masked_image, masked = detect_boundaries_and_mask(corrected_image, primary_reader)
            return masked_image , masked, is_aadhaar, confidence, class_name, is_mixed_docs
    
        elif entropy <= 0.15:
            masked_image, masked = detect_boundaries_and_mask(frame_cv2, primary_reader)
            return masked_image , masked, is_aadhaar, confidence, class_name, is_mixed_docs
    
        else:
            logging.warning(f"POSSIBLE FALSE POSITIVE CASE - attempting all angles OCRing")
            aadhaar_anchors_present = check_ocr_or_quartlet_after_rotation(frame_np, angle)
            print(f"aadhaar_anchors_present in check_ocr_or_quartlet_after_rotation:- {aadhaar_anchors_present}")

            if aadhaar_anchors_present:
                masked_image, masked = detect_boundaries_and_mask(frame_cv2, primary_reader)
                return masked_image , masked, is_aadhaar, confidence, class_name, is_mixed_docs
        
    else:
        print(f"current image is not an aadhaar card")

    return frame_cv2, masked, is_aadhaar, confidence, class_name, is_mixed_docs

    
def classify_image(image, rotations=[0, 90, 180, 270]):
    rotation_count=0
    # Get the predicted class probabilities
    
    for angle in rotations:
        # print(f"For classification, rotating image for angle {angle} degree")
        rotated_image = rotate_image(image, angle) 
        results = classification_model([rotated_image], imgsz=1024 ,device='cpu', verbose=False)
        # print(f"results:- {results}")
        
        if results:
            probs = results[0].probs
            class_id = probs.top1
            class_name = results[0].names[class_id]
            confidence = round(probs.top1conf.item(), 2)
            class_threshold = THRESHOLDS.get(class_name, 0.85)
            all_probs = probs.data.cpu().numpy()
            probs_clipped = np.clip(all_probs, 1e-9, 1.0)
            entropy = float(-np.sum(probs_clipped * np.log2(probs_clipped)))
            # confidence_distribution = {results[0].names[i]: round(float(all_probs[i]), 4) for i in range(len(all_probs))}
            # print(f"confidence_distribution:- {confidence_distribution}")
            
            if class_name == 'aadhar_cards':
                
                if confidence >= class_threshold:
                    # if entropy > 0.15:
                    return class_name , confidence, True, angle, entropy, False
                else:
                    print(f"confidence {confidence} is less than class threshold")
                    return class_name, confidence, False, angle, entropy, False
                
            elif class_name == 'mixed_docs':
                
                if confidence >= class_threshold:
                    # if entropy > 0.15:
                    return class_name , confidence, True, angle, entropy, True
                else:
                    print(f"confidence {confidence} is less than class threshold")
                    return class_name, confidence, False, angle, entropy, False
                
            else:
                rotation_count=rotation_count + 1
                # print(f"class name is {class_name}")
        
        else:
            # logging.error(f"No results from document classification model.")
            return "unknown", 0, False, angle, entropy, False
    
    if rotation_count == 4:    
        # print(f"rotation count is {rotation_count}, therefore we can clearly say that image is non-aadhaar image")
        return class_name, confidence, False, angle, entropy, False


def detect_boundaries_and_mask(image, reader):
    
    try:
        original_img = image
        if original_img is None: return None, 0
        deskewed_img, skew_angle, M = deskew_image_via_contours(original_img)

        is_skewed = False

        if M is not None and (skew_angle >= 10 or skew_angle <= -10): 
            # print(f"[🔄 Deskew Ran] IMAGE IS HIGHLY SKEWED BY {skew_angle:.2f} DEGREE. REQUEST TO MASK MANUALLY.")
            is_skewed = True

        orig_h, orig_w = original_img.shape[:2]
        gray_page = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
        _, global_std_dev = cv2.meanStdDev(gray_page)
        global_contrast = float(global_std_dev.item() if hasattr(global_std_dev, 'item') else global_std_dev[0][0])

        all_mapped_boxes = []
        all_confidences = []

        angles = [0, 90, 180, 270]
        inference_sizes = [640, 320, 1280] 

        for angle in angles:
            rotated_img = rotate_image(original_img, angle)
            rot_h, rot_w = rotated_img.shape[:2]

            current_angle_boxes = []
            current_angle_confs = []

            for img_sz in inference_sizes:
                results = boundary_detection_model(rotated_img, conf=CONF_THRESHOLD, imgsz=img_sz, verbose=False)
                
                for result in results:
                    if result.boxes is not None:
                        xyxy_array = result.boxes.xyxy.cpu().numpy()
                        conf_array = result.boxes.conf.cpu().numpy()
                        
                        for i in range(len(xyxy_array)):
                            coords = xyxy_array[i].tolist()
                            conf = float(conf_array[i])

                            if conf <= 0.75:
                                continue
                            
                            mapped_box = map_box_back_to_original(coords, angle, rot_w, rot_h, orig_w, orig_h)
                            if mapped_box is not None:
                                current_angle_boxes.append(mapped_box)
                                current_angle_confs.append(conf)

            slice_step = rot_h // 5
            slices = [
                (0, slice_step * 2),                  
                (slice_step, slice_step * 3),         
                (slice_step * 2, slice_step * 4),     
                (slice_step * 3, slice_step * 5),     
                (slice_step * 4, rot_h)               
            ]
            
            for y_start, y_end in slices:
                y_start = max(0, y_start)
                y_end = min(rot_h, y_end)
                
                crop_window = rotated_img[y_start:y_end, 0:rot_w]
                
                if crop_window.size > 0 and crop_window.shape[0] > 40:
                    for img_sz in inference_sizes:
                        crop_results = boundary_detection_model(crop_window, conf=CONF_THRESHOLD, imgsz=img_sz, verbose=False)
                        
                        for result in crop_results:
                            if result.boxes is not None:
                                xyxy_crop_array = result.boxes.xyxy.cpu().numpy()
                                conf_crop_array = result.boxes.conf.cpu().numpy()
                                
                                for i in range(len(xyxy_crop_array)):
                                    _, y1_local, _, _ = xyxy_crop_array[i]
                                    coords = xyxy_crop_array[i].tolist()
                                    conf = float(conf_crop_array[i])

                                    if conf <= 0.75:
                                        continue
                                    
                                    if y1_local < 12:
                                        continue

                                    mapped_box = map_box_back_to_original(
                                        coords, angle, rot_w, rot_h, orig_w, orig_h, crop_offset=(y_start, 0)
                                    )
                                    if mapped_box is not None:
                                        current_angle_boxes.append(mapped_box)
                                        current_angle_confs.append(conf)

            if len(current_angle_boxes) >= 1:
                all_mapped_boxes.extend(current_angle_boxes)
                all_confidences.extend(current_angle_confs)

        if is_skewed: 
            # print(f"[🔄 Deskew Run] IMAGE ROTATING BY {skew_angle:.2f} DEGREE...")
            deskew_h, deskew_w = deskewed_img.shape[:2]
            
            for angle in angles:
                # print(f'ROTATING DSKEWED IMAGE BY {angle}')
                rotated_img = rotate_image(deskewed_img, angle)
                rot_h, rot_w = rotated_img.shape[:2]
                
                for img_sz in inference_sizes:
                    results = boundary_detection_model(rotated_img, conf=CONF_THRESHOLD, imgsz=img_sz, verbose=False)
                    for result in results:
                        if result.boxes is not None:
                            xyxy_array = result.boxes.xyxy.cpu().numpy()
                            conf_array = result.boxes.conf.cpu().numpy()
                            for i in range(len(xyxy_array)):
                                coords = xyxy_array[i].tolist()
                                conf = float(conf_array[i])
                                if conf <= 0.75: continue
                                
                                mapped_to_deskew = map_box_back_to_original(coords, angle, rot_w, rot_h, deskew_w, deskew_h)
                                if mapped_to_deskew is not None:
                                    final_orig_box = map_deskew_box_back_to_original(mapped_to_deskew, M, orig_w, orig_h)
                                    all_mapped_boxes.append(final_orig_box)
                                    all_confidences.append(conf)
                                else:
                                    # print("THERE IS NOTHING 'MAPPED TO DESKEW', HENCE NOTHING ADDED TO all_mapped_boxes")
                                    pass

        if len(all_mapped_boxes) == 0:
            return original_img, 0

        nms_boxes = [box[:4] for box in all_mapped_boxes]
        indices = cv2.dnn.NMSBoxes(nms_boxes, all_confidences, CONF_THRESHOLD, NMS_THRESHOLD)

        
        if len(indices) > 0:
            masked_img = original_img.copy()

            valid_detections = []
            
            for i in np.array(indices).flatten():
                x, y, w, h, detection_angle = all_mapped_boxes[i]
                conf = all_confidences[i]
                
                if h > 0:
                    aspect_ratio = w / h
                    
                    if detection_angle in (0, 180):
                        if not is_skewed:
                            if aspect_ratio < 2.5 or aspect_ratio > 9.0:
                                continue

                        if is_skewed:
                            if aspect_ratio < 1.9 or aspect_ratio > 9.0:
                                continue

                        if h > (orig_h * 0.11):
                            continue  
                            
                    elif detection_angle in (90, 270):
                        
                        if aspect_ratio < 0.1 or aspect_ratio > 0.45:
                            continue  
                        if w > (orig_w * 0.11):
                            continue  
                        if orig_h < 2200:
                            if h < (orig_h * 0.06):
                                continue
                        elif orig_h > 2200 and int(global_contrast) <= 70:
                            if h < (orig_h * 0.07):
                                continue
                        else:
                            if h < (orig_h * 0.15):
                                continue

                valid_detections.append({'box': [x, y, w, h], 'conf': conf, 'angle': detection_angle})
                
            final_boxes_to_mask = []
            skip_indices = set()

            for idx1 in range(len(valid_detections)):
                if idx1 in skip_indices: continue
                
                det1 = valid_detections[idx1]
                x1, y1, w1, h1 = det1['box']
                angle1 = det1['angle']
                
                keep_this = True

                MAX_ALLOWED_DIST = int(orig_w * 0.10)

                for idx2 in range(len(valid_detections)):
                    if idx1 == idx2 or idx2 in skip_indices: continue
                    
                    det2 = valid_detections[idx2]
                    x2, y2, w2, h2 = det2['box']
                    cx1 = x1 + (w1 / 2)
                    cy1 = y1 + (h1 / 2)
                    
                    cx2 = x2 + (w2 / 2)
                    cy2 = y2 + (h2 / 2)
                    
                    euclidean_dist = math.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)                
                    if angle1 in (90, 270):
                        if angle1 == 270:
                            if x1 < x2: 
                                if euclidean_dist < MAX_ALLOWED_DIST:
                                    keep_this = False
                                    break
                            else:
                                if euclidean_dist < MAX_ALLOWED_DIST:
                                    skip_indices.add(idx2)
                                    
                        elif angle1 == 90:
                            if x1 > x2:
                                if euclidean_dist < MAX_ALLOWED_DIST:
                                    keep_this = False
                                    break
                            else:
                                if euclidean_dist < MAX_ALLOWED_DIST:
                                    skip_indices.add(idx2)
                        
                        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
                        if x_overlap > (min(w1, w2) * 0.4): 
                            
                            if angle1 == 270:
                                if x1 < x2: 
                                    keep_this = False
                                    break
                                else:
                                    skip_indices.add(idx2)
                                    
                            elif angle1 == 90:
                                if x1 > x2:
                                    keep_this = False
                                    break
                                else:
                                    skip_indices.add(idx2)

                    else:
                        x_overlap = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
                        if x_overlap > (min(w1, w2) * 0.5):
                            y_dist = abs(y1 - y2)
                            if y_dist < 60: 
                                if det1['conf'] < det2['conf']:
                                    keep_this = False
                                    break
                                else:
                                    skip_indices.add(idx2)
                
                if keep_this:
                    final_boxes_to_mask.append(det1)

            is_masked = False
           
            for det in final_boxes_to_mask:
                x, y, w, h = det['box']
                detection_angle = det['angle']
                
                if detection_angle in (0, 180):
                    shrink_w = int(w * 0.03)  
                    shrink_h = int(h * 0.05)  
                else:
                    shrink_w = int(w * 0.05)  
                    shrink_h = int(h * 0.03)

                if detection_angle in (0, 180):
                    xpand_w = int(w * 1.50)
                    xpand_h = h  
                else:
                    xpand_w = w  
                    xpand_h = int(h * 1.50)
                
                crop_image = masked_img[y:y+xpand_h, x:x+xpand_w]
                _, full_text = verify_classification_text(crop_image, reader)

                is_break = False

                if not full_text:
                    is_break = True

                for keyword in skip_keywords:
                    if keyword in full_text:
                        is_break = True

                if re.search(r'[a-z]{3,}', full_text):
                    is_break = True

                if is_break:
                    continue

                x_start = max(0, x + shrink_w)
                y_start = max(0, y + shrink_h)
                x_end = min(orig_w, x + w - shrink_w)
                y_end = min(orig_h, y + h - shrink_h)
                
                if (x_end > x_start) and (y_end > y_start):
                    cv2.rectangle(masked_img, (x_start, y_start), (x_end, y_end), (0, 0, 0), -1)
                    is_masked = True

            if is_masked:        
                if len(final_boxes_to_mask) < 2 or len(final_boxes_to_mask) > 3:
                        return masked_img, -1
                else:
                    return masked_img, 1

            else:
                print("Skip keywords found inside detect_boundaries_and_mask function or not able extract aadhaar number properly, therefore image is unmasked")
                return original_img, 0
            
        else:
            # cv2.imwrite(os.path.join(OUTPUT_DIR, f"failed_{image_path.name}"), original_img)
            return original_img, 0

    except Exception as e:
        logging.error(f"Exception in detect_boundaries_and_mask function:- {e}")
        return original_img, 0


# BELOW ARE ALL HELPER METHODS

def correct_image_orientation(image):

    print("inside correct_image_orientation")

    if image is None:
        return None, False

    try:
        osd = pytesseract.image_to_osd(image)
        angle = int(re.search(r'(?<=Rotate: )\d+', osd).group(0))
        print(f"[INFO] IMAGE IS ROTATED BY {angle}°")
    except Exception as e:
        logging.error(f"[ERROR] CANNOT IDENTIFY ORIENTATION, DEFAULT TO MODEL ANGLE. error: {e}")
        return image, False

    if angle == 90:
        corrected_img = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        corrected_img = cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        corrected_img = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    else:
        corrected_img = image

    return corrected_img, True


def check_ocr_or_quartlet_after_rotation(image, angle):
    print("inside check_ocr_or_quartlet_after_rotation")
    aadhaar_available = False

    # FOR CORRECTED IMAGES
    if angle == -1:
        aadhaar_available, _ = verify_classification_text(image, primary_reader)
        print(f"aadhaar_available in english reader:- {aadhaar_available}")

        if not aadhaar_available:
            aadhaar_available, _ = verify_classification_text(image, devnagiri_reader)
            print(f"aadhaar_available in devnagiri reader:- {aadhaar_available}")
    
        return aadhaar_available

    # FOR FAILED CORRECTED IMAGES 
    # angle_list = deque(a for a in [180, 0, 90, 270] if a != angle)

    match angle:
        case 0:
            angle_list = deque([180])
        case 180:
            angle_list = deque([0])
        case 90:
            angle_list =  deque([270])
        case 270:
            angle_list =  deque([90])
        case _: 
            angle_list =  deque([])

    # while angle_list:
    current_angle = angle_list.popleft()
    print(f"trying rotation for angle : {current_angle}")
    rotated_image = rotate_image(image, current_angle)

    aadhaar_available, _ = verify_classification_text(rotated_image, primary_reader)
    print(f"aadhaar_available in english reader:- {aadhaar_available}")

    if not aadhaar_available:
        aadhaar_available, _ = verify_classification_text(rotated_image, devnagiri_reader)
        print(f"aadhaar_available in devnagiri reader:- {aadhaar_available}")

    if aadhaar_available:
        return aadhaar_available
    else:
        return aadhaar_available


def verify_classification_text(image, reader):
    print("inside verify_classification_text")

    try:
        # Reuse module-level CLAHE instead of creating new one each iteration
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        enhanced = CLAHE.apply(gray)
        rgb_img = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)

        ocr_results = reader.readtext(
            rgb_img,
            detail = 0,
            paragraph = False,
            decoder = 'greedy',
            workers = 0,
            mag_ratio = mag_ratio,
            canvas_size = canvas_size
        )
        print(f"ocr_results: {ocr_results}")

        split_text = ocr_results.split(" ")
            
        for number in split_text:
            if number.isdigit():
                if len(number) > 4:
                    return False, []

    except Exception as e:
        logging.error(f"error in verify_classification_text: {e}")
        ocr_results = []  # prevent NameError on full_text join below

    full_text = " ".join(ocr_results).lower()

    # print(f"full_text {full_text}")

    # check fo negative anchors, in a page
    if any(anchor in full_text for anchor in NEGATIVE_ANCHORS):
        return False, full_text

    # frozenset lookup is O(1) vs O(n) list scan
    elif any(anchor in full_text for anchor in AADHAAR_ANCHORS):
        return True, full_text

    # Pre-compiled regex — no recompilation overhead
    if QUARTLET_PATTERN.search(full_text):
        print("aadhaar pattern found in verify_classification_text")
        return True, full_text
    
    else:
        return False, full_text


def deskew_image_via_contours(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    angles = []
    for cnt in contours:
        if cv2.contourArea(cnt) < 1000: continue
        minAreaRect = cv2.minAreaRect(cnt)
        angle = minAreaRect[-1]
        if angle < -45: angle = 90 + angle
        elif angle > 45: angle = angle - 90
        if abs(angle) > 0.5 and abs(angle) < 45:
            angles.append(angle)
            
    if len(angles) > 0:
        median_angle = np.median(angles)
        if abs(median_angle) > 1.5:  
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,255))
            return rotated, median_angle, M
    return image, 0.0, None


def map_deskew_box_back_to_original(box, M, orig_w, orig_h):
    if M is None: return box
    x, y, w, h, angle = box
    
    pts = np.array([
        [x, y], 
        [x + w, y], 
        [x + w, y + h], 
        [x, y + h]
    ], dtype='float32')
    
    M_inv = cv2.invertAffineTransform(M)
    
    transformed_pts = cv2.transform(np.array([pts]), M_inv)[0]
    
    xs = transformed_pts[:, 0]
    ys = transformed_pts[:, 1]
    
    new_x1 = max(0, min(int(np.min(xs)), orig_w))
    new_y1 = max(0, min(int(np.min(ys)), orig_h))
    new_x2 = max(0, min(int(np.max(xs)), orig_w))
    new_y2 = max(0, min(int(np.max(ys)), orig_h))
    
    calc_w = new_x2 - new_x1
    calc_h = new_y2 - new_y1
    
    if calc_w <= 0 or calc_h <= 0: return None
    return [new_x1, new_y1, calc_w, calc_h, angle]


def map_box_back_to_original(box, angle, rot_w, rot_h, orig_w, orig_h, crop_offset=None):
    flat_box = np.array(box).flatten()
    if len(flat_box) < 4: return None
        
    x1, y1, x2, y2 = flat_box[0], flat_box[1], flat_box[2], flat_box[3]
    
    if crop_offset is not None:
        crop_y1, crop_x1 = crop_offset
        x1 += crop_x1
        x2 += crop_x1
        y1 += crop_y1
        y2 += crop_y1
    
    angle = int(angle)
    if angle == 0:
        orig_x1, orig_y1, orig_x2, orig_y2 = x1, y1, x2, y2
    elif angle == 90:
        orig_x1 = y1
        orig_y1 = rot_w - x2
        orig_x2 = y2
        orig_y2 = rot_w - x1
    elif angle == 180:
        orig_x1 = rot_w - x2
        orig_y1 = rot_h - y2
        orig_x2 = rot_w - x1
        orig_y2 = rot_h - y1
    elif angle == 270:
        orig_x1 = rot_h - y2
        orig_y1 = x1
        orig_x2 = rot_h - y1
        orig_y2 = x2
    else:
        orig_x1, orig_y1, orig_x2, orig_y2 = x1, y1, x2, y2

    orig_x1 = int(max(0, min(orig_x1, orig_w)))
    orig_y1 = int(max(0, min(orig_y1, orig_h)))
    orig_x2 = int(max(0, min(orig_x2, orig_w)))
    orig_y2 = int(max(0, min(orig_y2, orig_h)))
    
    return [orig_x1, orig_y1, orig_x2 - orig_x1, orig_y2 - orig_y1, angle]


def rotate_image(image, angle):
    """Rotate the image by the given angle (90, 180, or 270 degrees)."""
    if angle == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif angle == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    elif angle == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def ensure_correct_channels(pil_image):
    """Convert any PIL image mode to OpenCV BGR"""
    
    # Binary image (mode 1)
    if pil_image.mode == '1':
        pil_image = pil_image.convert('RGB')
    # Grayscale (mode L)
    elif pil_image.mode == 'L':
        pil_image = pil_image.convert('RGB')
    # RGBA
    elif pil_image.mode == 'RGBA':
        pil_image = pil_image.convert('RGB')
    # Any other mode
    elif pil_image.mode != 'RGB':
        pil_image = pil_image.convert('RGB')
    
    # Convert to OpenCV BGR
    np_array = np.array(pil_image, dtype=np.uint8)
    return cv2.cvtColor(np_array, cv2.COLOR_RGB2BGR)


def make_save_ready(image, original_mode):
    if isinstance(image, np.ndarray):
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    if original_mode == '1':
        gray = image.convert('L')
        return gray.convert('1', dither=Image.Dither.NONE)  # ✅ no dithering
    elif original_mode == 'L':
        return image.convert('L')  # ✅ direct grayscale
    else:
        return image.convert(original_mode)


# def get_compression(original_mode):
#     if original_mode == '1':
#         return 'group4'    # ✅ best for 1-bit
#     else:
#         return 'tiff_lzw'  # ✅ best for grayscale or default


def get_compression(original_mode, original_compression=None):
    # ✅ If original used JPEG, keep using JPEG!
    if original_compression and original_compression.lower() in ('jpeg', 'jpg'):
        return 'jpeg'
    
    # Otherwise, use optimal compression per mode
    if original_mode == '1':
        return 'group4'
    elif original_mode == 'L':
        # For grayscale, prefer deflate over lzw (slightly better)
        return 'tiff_deflate'
    else:
        return 'tiff_deflate'


# def downscale_cv2(img):
#     h, w = img.shape[:2]
#     if h * w > MAX_PIXELS:
#         scale = (MAX_PIXELS / (h * w)) ** 0.5
#         img = cv2.resize(img, (int(w * scale), int(h * scale)))
#     return img

  
def downscale_and_denoise(img):
    h, w = img.shape[:2]
    if h * w > MAX_PIXELS:
        scale = (MAX_PIXELS / (h * w)) ** 0.5
        # डाउनस्केल करण्यापूर्वी हलका ब्लर केल्यास TIFF चा नॉईज निघून जातो
        img = cv2.GaussianBlur(img, (3, 3), 0)
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


# def downscale_and_denoise(img):
#     """Downscale and denoise image for model input only — never for saving"""
#     h, w = img.shape[:2]
    
#     # Step 1 — downscale if needed
#     if h * w > MAX_PIXELS:
#         scale = (MAX_PIXELS / (h * w)) ** 0.5
#         img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    
#     # Step 2 — detect image quality and apply appropriate filter
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
#     # measure blur level — low value = blurry image
#     blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    
#     # measure noise level — high std = noisy image  
#     noise_score = gray.std()
    
#     print(f"blur_score: {blur_score:.2f}, noise_score: {noise_score:.2f}")
    
#     # Step 3 — apply filter based on image condition
#     if blur_score < 50:
#         # very blurry image — sharpen first
#         print("applying sharpening — blurry image detected")
#         kernel_sharpen = np.array([
#             [ 0, -1,  0],
#             [-1,  5, -1],
#             [ 0, -1,  0]
#         ])
#         img = cv2.filter2D(img, -1, kernel_sharpen)
    
#     if noise_score > 60:
#         # noisy image — denoise
#         print("applying denoising — noisy image detected")
#         img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
#     else:
#         # mild noise — light gaussian blur sufficient
#         img = cv2.GaussianBlur(img, (3, 3), 0)
    
#     # Step 4 — enhance contrast for low quality/rotated images
#     lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
#     l, a, b = cv2.split(lab)
#     clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
#     l = clahe.apply(l)
#     lab = cv2.merge((l, a, b))
#     img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
#     return img

# def separate_tiff_pages(bytes_data):
#     stream = io.BytesIO(bytes_data)
#     image = Image.open(stream)
#     original_mode = image.mode
#     original_dpi = image.info.get('dpi')
    
#     frames = []
#     try:
#         while True:
#             frame = image.copy()
#             frames.append(frame)
#             image.seek(image.tell() + 1)
#     except EOFError:
#         pass  # No more frames

#     return frames, original_mode, original_dpi


def separate_tiff_pages(bytes_data):
    stream = io.BytesIO(bytes_data)
    image = Image.open(stream)
    original_mode = image.mode
    original_dpi = image.info.get('dpi')
    original_compression = image.info.get('compression')
    print(f"mode is {original_mode}, dpi is {original_dpi} and compression {original_compression}")
    
    frames = []
    try:
        while True:
            frame_rgb = image.convert('RGB')
            
            TARGET_WIDTH = 1500
            w, h = frame_rgb.size
            
            if w > TARGET_WIDTH:
                scale = TARGET_WIDTH / w
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame_rgb = frame_rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            frames.append(frame_rgb)
            image.seek(image.tell() + 1)
    except EOFError:
        pass  

    return frames, original_mode, original_dpi, original_compression


def process_base64_pdf(pdf):
    try:
        images = convert_from_bytes(pdf)
        print("PDF Processing Finished")
        return [cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR) for image in images]
    except Exception as e:
        print(f"Error processing base64 PDF: {e}")
        return []

        
def image_classification(image, mimetype, doc_name):
    if mimetype in ("jpeg", "jpg", "png"):
        print(f"File {doc_name} processing started ------------------------->")
        input_stream = io.BytesIO(image)
        image = Image.open(input_stream)
        image_cv2 = ensure_correct_channels(image)
        image_cv2 = downscale_and_denoise(image_cv2)      
        class_name, confidence , is_aadhaar, angle, entropy = classify_image(image_cv2)
        print(f"Classification model response Class_name: {class_name}, confidence:- {confidence} and image is_aadhaar is {is_aadhaar}")
        print(f"File {doc_name} has been processed successfully -------------------------->")
        return class_name
    elif mimetype in ("pdf"):
        pdf_images = process_base64_pdf(image)  # This should return list of numpy arrays
        for i, frame in enumerate(pdf_images):
            frame = downscale_and_denoise(frame)                       
            class_name, confidence , is_aadhaar, angle, entropy = classify_image(frame)
            print(f"Classification model response Class_name: {class_name}, confidence:- {confidence} and image is_aadhaar is {is_aadhaar}")
            print(f"File {doc_name} has been processed successfully -------------------------->")
        return class_name
    else:
        pass


