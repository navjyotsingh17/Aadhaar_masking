import os
from PIL import Image

def convert_to_png_and_move(root_folder, destination_folder):
    """Convert all images to PNG and save to new folder"""
    
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
    os.makedirs(destination_folder, exist_ok=True)
    
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            if file.lower().endswith(image_extensions):
                source_path = os.path.join(root, file)
                file_name = os.path.splitext(file)[0]
                dest_path = os.path.join(destination_folder, f"{file_name}.png")
                
                try:
                    # Open image
                    img = Image.open(source_path)
                    
                    # Convert to RGB
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Handle duplicate names
                    if os.path.exists(dest_path):
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(destination_folder, f"{file_name}_{counter}.png")
                            counter += 1
                    
                    # Save as PNG
                    img.save(dest_path, 'PNG')
                    print(f"✓ Converted: {file} → PNG")
                
                except Exception as e:
                    print(f"✗ Error: {file} - {e}")

# Usage
convert_to_png_and_move("C:\\Users\\Lenovo\\Desktop\\Kotak\\testing\\split_images", "C:\\Users\\Lenovo\\Desktop\\Kotak\\testing\\unmasked_images")