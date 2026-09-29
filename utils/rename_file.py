# import os

# def rename_files(folder_path):
#     """Remove .rf.* pattern from all filenames"""
    
#     for filename in os.listdir(folder_path):
#         if '.rf.' in filename:
#             # Split at .rf. and keep only first part
#             new_filename = filename.split('.rf.')[0]
            
#             old_path = os.path.join(folder_path, filename)
#             new_path = os.path.join(folder_path, new_filename+".png")
            
#             os.rename(old_path, new_path)
#             print(f"✓ Renamed: {filename} → {new_filename}")

# # Usage
# rename_files("C:\\Users\\Lenovo\\Desktop\\Aadhaar Masking\\new")


import os
# Specify the path to your folder
folder_path = r'C:\Users\Navjyot\Desktop\masking_engine\unmasked_docs'
# Change the current working directory
os.chdir(folder_path)
# Get all PDF files and sort them alphabetically
pdf_files = [f for f in os.listdir() if f.lower().endswith('.png')]
pdf_files.sort()
# Rename the files sequentially
for i, filename in enumerate(pdf_files, start=1):
    new_name = f"{i}_unmasked.png"
    
    # Avoid renaming if the file is already named correctly
    if filename != new_name:
        os.rename(filename, new_name)
        print(f"Renamed: {filename} -> {new_name}")
print("Renaming complete!")