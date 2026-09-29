from langdetect import detect # pip install langdetect

lang_prechecker = easyocr.Reader(['en'], gpu=False, detector='dbnet18',  verbose=False)

def precheck_image_language(rgb_img):
    try:
        raw_text_list = lang_prechecker.readtext(rgb_img, detail=0, decoder='greedy', canvas_size=600, workers=0)
        
        sample_text = " ".join(raw_text_list).strip()
        
        if not sample_text:
            return "unknown"
        
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in sample_text)
        if has_devanagari:
            return "marathi_or_hindi"
        
        detected_lang = detect(sample_text)
        
        return detected_lang
    except Exception as e:
        return 'en'


detected_language = precheck_image_language(image)

if detected_language == "marathi_or_hindi":
    reader = easyocr.Reader(['en', 'hi', 'mr'], gpu=False, detector='dbnet18', verbose=False)
elif detected_language in ('ta', 'te', 'kn', 'bn', 'ml', 'pa', 'gu'):
    reader = easyocr.Reader(['en', detected_language], gpu=False, detector='dbnet18',verbose=False)                  
else:
    reader = easyocr.Reader(['en'], gpu=False, detector='dbnet18',verbose=False)  