import os
from PIL import Image, ImageSequence
from pdf2image import convert_from_path

# im = Image.open("C:\\Users\\Lenovo\\Desktop\\Kotak\\unmasked_tiff_images\\0946641145.tiff")

# for i, page in enumerate(ImageSequence.Iterator(im)):
#     page.save("C:\\Users\\Lenovo\\Desktop\\Kotak\\testing\\split_images\\Page%d.tiff" % i)

# Input folder containing TIFF files
input_folder = r"C:\Users\Lenovo\Desktop\Aadhaar Masking\prod_files_uploaded_to uat\Account Opening 20408912.tif"

# Output base folder to save split images
output_base_folder = r"C:\Users\Lenovo\Desktop\Aadhaar Masking\prod_files_uploaded_to uat"

# Ensure output base folder exists
os.makedirs(output_base_folder, exist_ok=True)

# Iterate over all .tiff files in the input folder
for filename in os.listdir(input_folder):
    if filename.lower().endswith('.tiff') or filename.lower().endswith('.tif'):
        file_path = os.path.join(input_folder, filename)
        file_basename = os.path.splitext(filename)[0]
        
        # Create output folder for the current file
        output_folder = output_base_folder
        os.makedirs(output_folder, exist_ok=True)

        # Open TIFF and iterate through pages
        with Image.open(file_path) as im:
            for i, page in enumerate(ImageSequence.Iterator(im)):
                output_path = os.path.join(output_folder, f"{file_basename}_Page{i}.png")
                page.save(output_path)
        print(f"Processed: {filename} -> {output_folder}")

    if filename.lower().endswith('.pdf'):
        file_path = os.path.join(input_folder, filename)
        file_basename = os.path.splitext(filename)[0].split(".")[0]
        # print(f"file path:- {file_path} and file base name:- {file_basename}")
        
        output_folder = output_base_folder
        os.makedirs(output_folder, exist_ok=True)

        pages = convert_from_path(file_path)
        for i, page in enumerate(pages):
            output_path = os.path.join(output_folder, f"{file_basename}_Page{i}.png")
            page.save(output_path, 'PNG')

        print(f"Processed: {filename} -> {output_folder}")


# if file_extension == 'pdf':
#             try:
#                 pdf_images = process_base64_pdf(decoded_image)
#                 masked_images = []
#                 is_masked = False
#                 aadhaar_number, occurrence = None, 0

#                 for img in pdf_images:
#                     masked_img_cv2, masked, aadhaar_number, occurrence = process_image(img)
#                     if aadhaar_number and aadhaar_number.isdigit():  # Ensure valid Aadhaar number
#                         masked_images.append(Image.fromarray(cv2.cvtColor(masked_img_cv2, cv2.COLOR_BGR2RGB)))
#                         is_masked = is_masked or masked
#                     else:
#                         logging.warning("Invalid Aadhaar number found in PDF")
#                         masked_images.append(img)  # Keep original image if invalid Aadhaar number

#                 if is_masked:
#                     output_buffer = BytesIO()
#                     masked_images[0].save(output_buffer, format='PDF', save_all=True, append_images=masked_images[1:])
#                     masked_image_base64 = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
#                     return {"status": "masked", "masked_image_base64": masked_image_base64}
#                 else:
#                     return {"status": "unmasked", "masked_image_base64": None}
            
#             except Exception as err:
#                 logging.error(f"Error processing PDF: {err}")
#                 return {"status": "error processing pdf", "masked_image_base64": None}
            
# elif file_extension in ('jpeg', 'jpg', 'png'):
#             try:
#                 input_stream = BytesIO(decoded_image)
#                 image = Image.open(input_stream)
#                 image_cv2 = ensure_correct_channels(image)
#                 masked_img_cv2, is_masked, aadhaar_number, occurrence = process_image(image_cv2)
                
#                 if aadhaar_number and aadhaar_number.isdigit():  # Ensure valid Aadhaar number
#                     end_time = time.time()
#                     time_taken_single = round(end_time - start_time)
#                     log_audit_details(filename, filename, 'masked' if is_masked else 'unmasked', aadhaar_number, occurrence, 100 if is_masked else 0, time_taken_single)
                    
#                     _, buffer = cv2.imencode('.jpg', masked_img_cv2)
#                     masked_image_base64 = base64.b64encode(buffer).decode('utf-8')
#                     return {"status": "masked" if is_masked else "unmasked", "masked_image_base64": masked_image_base64 if is_masked else ""}
#                 else:
#                     logging.warning("Invalid Aadhaar number found in image")
#                     return {"status": "unmasked", "masked_image_base64": ""}
            
#             except Exception as err:
#                 logging.error(f"Error processing image: {err}")
#                 return {"status": "error processing image", "masked_image_base64": None}
            

# def handle_tiff():
#     raw_data = request.data
#     filename = request.headers.get('X-Filename')

#     # Load raw bytes into PIL Image
#     tiff_io = io.BytesIO(raw_data)
#     try:
#         img = Image.open(tiff_io)
#     except Exception as e:
#         return jsonify({'error': f'Invalid TIFF data: {str(e)}'}), 400

#     redacted_pages = []
#     redaction_performed = False

#     # Loop through all pages based on total frames
#     for i in range(img.n_frames):
#         try:
#             img.seek(i)
#         except EOFError:
#             break  # Safety check in case of malformed TIFF

#         original_size = img.size  # Store original size (width, height)
        
#         # Enlarge the image (e.g., double the size)
#         enlarged_img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)

#         # Convert enlarged image to base64
#         buffer = io.BytesIO()
#         enlarged_img.save(buffer, format="TIFF")
#         base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

#         document_name = f"{filename}.tiff"

#         # Send for redaction
#         redacted = mask_aadhaar_in_image_base64(base64_data, document_name)
#         # print("Redacted :- ",redacted)

#         if redacted.get("status") == "masked":
#             redaction_performed = True
#             redacted_img_data = base64.b64decode(redacted["masked_image_base64"])
#             redacted_img = Image.open(io.BytesIO(redacted_img_data))

#             # Resize redacted image back to original size
#             resized_back_img = redacted_img.resize(original_size, Image.LANCZOS)
#             redacted_pages.append(resized_back_img.copy())
#         else:
#             redacted_pages.append(img.copy())

#     # Save redacted TIFF only if redaction occurred
#     if redaction_performed:
#         existing_files = os.listdir(OUTPUT_FOLDER)
#         # Create new file name
#         filename = f"{filename}_redacted.tiff"
#         output_path = os.path.join(OUTPUT_FOLDER, filename)
#         redacted_pages[0].save(output_path, save_all=True, append_images=redacted_pages[1:])
#         return jsonify({'status': 'Redaction complete', 'saved_path': output_path})
#     else:
#         return jsonify({'status': 'No redaction performed'})
    

    