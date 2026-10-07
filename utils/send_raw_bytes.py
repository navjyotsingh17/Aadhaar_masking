import requests, os

def tiff_to_raw_and_send(file_path, api_url):
    try:
        filename = os.path.basename(file_path)
        print(f"Sending file: {filename} to {api_url}")

        with open(file_path, 'rb') as f:
            raw_bytes = f.read()

        print(f"Read {len(raw_bytes)} bytes from {filename}")
        response = requests.post(
            api_url,
            data=raw_bytes,
            headers={
                'Content-Type': 'application/octet-stream',
                'X-Filename': filename,
                'X-Password': 'i2UYSL94jrUWTI8B73mc3w==',
                'X-Mimetype':'tiff',
                'X-Output-Folder': '/data/masked_docs',
                'page':'97'

            }
        )

        print(f"Received response: {response.status_code}")
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
file_path = r'D:\Python_Masking_Engine\unmasked_docs\4_unmasked.tiff'

api_endpoint = "http://localhost:5000/mask"

tiff_to_raw_and_send(file_path, api_endpoint)
