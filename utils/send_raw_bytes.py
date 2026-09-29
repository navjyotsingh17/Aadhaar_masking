import requests
import os

def tiff_to_raw_and_send(file_path, api_url):
    try:
        filename = os.path.basename(file_path)

        with open(file_path, 'rb') as f:
            raw_bytes = f.read()

        response = requests.post(
            api_url,
            data=raw_bytes,
            headers={
                'Content-Type': 'application/octet-stream',
                'X-Filename': filename,
                'X-Password': 'i2UYSL94jrUWTI8B73mc3w==',
                'X-Mimetype':'tif',
                'X-Output-Folder':'C:\\Users\\Navjyot\\Desktop\\masking_engine\\masked_docs',
                'page':'97'

            }
        )

        if response.status_code == 200:
            status_header = response.headers.get('status')
            if status_header == 'masked':
                print(f"File {filename} was successfully masked.")
            elif status_header == 'unmasked':
                print(f"File {filename} was not masked.")
            else:
                print(f"Unknown status for {filename}.")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

# Example usage
# tiff_file_path = r"C:\Users\Lenovo\Desktop\Aadhaar Masking\prod_files_uploaded_to uat\Account Opening (6)20399564.tif"
tiff_file_path = r"C:\Users\Navjyot\Desktop\masking_engine\unmasked_docs\4_unmasked.tiff"

api_endpoint = "http://localhost:5000/mask"

tiff_to_raw_and_send(tiff_file_path, api_endpoint)
