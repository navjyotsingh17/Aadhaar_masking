import os
from PIL import Image

def merge_images_to_tiff(input_folder, output_path):
    image_files = [f for f in os.listdir(input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff'))]
    image_files.sort()  # Optional: sort for consistent order

    images = []

    for img_file in image_files:
        img_path = os.path.join(input_folder, img_file)
        img = Image.open(img_path).convert("RGB")
        images.append(img)

    if images:
        images[0].save(output_path, save_all=True, append_images=images[1:], format='TIFF')
        print(f"Saved merged TIFF to {output_path}")
    else:
        print("No images found to merge.")

# Usage
input_folder = "C:\\Users\\Lenovo\\Downloads\\masking_doc_3-1,masking_doc_3-2,masking_doc_3-3"
output_tiff_path = "C:\\Users\\Lenovo\\Desktop\\Kotak\\input_folder\\masking_tiff_doc_3.tiff"
merge_images_to_tiff(input_folder, output_tiff_path)
