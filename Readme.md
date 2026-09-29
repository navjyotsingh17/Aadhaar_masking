# Python Masking Engine

A Python-based data masking utility for protecting sensitive information in datasets, logs, API payloads, and application data while preserving usability for testing, development, and analytics.

## Overview

The Python Masking Engine helps teams sanitize sensitive data such as names, email addresses, phone numbers, account IDs, and other personally identifiable information (PII) before it is stored, shared, or logged. It is designed to be easy to configure, reusable, and suitable for a wide range of Python projects.

## Features

- Mask sensitive fields in structured data
- Support for common PII types such as emails, phone numbers, IDs, and names
- Configurable masking rules and patterns
- Works with dictionaries, JSON payloads, and nested data structures
- Easy to extend with custom masking logic
- Lightweight and dependency-friendly

## Typical Use Cases

- Redacting customer information in test environments
- Sanitizing logs before sending to external systems
- Protecting data in ETL pipelines and export files
- Preparing realistic-but-safe sample data for demos and QA


## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd Python_Masking_Engine
```

2. Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate   # On macOS/Linux
venv\Scripts\activate      # On Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Unzip poppler, tesseract OCR and Easy OCR

Open "Poppler_tesseractOCR_easyOCR_setup_link.txt" file download and extract the zip in the same directory as project. This file contains poppler package, Tesseract.exe and EasyOCR models

5. Update poppler path

Go to this path from project's root

```bash
poppler-24.08.0\Library\bin
```

copy the path as per your machine and add it in system's environment vairiable. This poppler package is required to read PDFs

6. Update Tesseract path

Copy below tesseract.exe path as per you machine, path should be as below

```bash
C:\Users\<USER_NAME AS PER YOUR MACHINE>\Desktop\Python_Masking_Engine\Tesseract-OCR\tesseract.exe
```

Create a .env at project's root, and below key value pair

```bash
tesseract_path = r"C:\Users\<USER_NAME AS PER YOUR MACHINE>\Desktop\Python_Masking_Engine\Tesseract-OCR\tesseract.exe"
```

7. Easy OCR package

From the same zip file which you've unzipped copy the .EasyOCR folder and paste at below location

```bash
C:\Users\<USER_NAME AS PER YOUR MACHINE>\
```

8. Create secret key and password

The /mask endpoint which is used to mask Aadhaar number is password protected, therefore to access it you'll need add secrect key and password in your .env file.

execute below file

```bash
/utils/encrypt_decrypt.py
```

Set the secret key and password as per your choice and and encrypt the password. Paste secret key and password in .env file.

## Usage

Once all the dependencies are installed in the virtual env, then run below command to start the masking engine from the root directory of the project.

```bash
python wsgi.py
```
Above command will start the masking engine.

Go to /utils/send_raw_bytes.py file, update the document path which you need to mask, add the encrytped password in headers, add the output folder location where masked document will be saved and then execute below command

```bash
python send_raw_bytes.py
```

## Contributing

Contributions are welcome. Please:

- Open an issue for bug reports or feature requests
- Keep changes focused and well-documented
- Add or update tests for new masking rules

