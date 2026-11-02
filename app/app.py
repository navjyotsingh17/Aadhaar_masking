import os, signal, time, threading, base64, uuid
from services.mask_image import mask_aadhaar_image, image_classification
from services.encrypt_decrypt import decrypt
from flask import Flask, jsonify, request, make_response
from datetime import datetime
from dotenv import load_dotenv
# from werkzeug.utils import secure_filename
from pymongo import MongoClient

load_dotenv()

app = Flask(__name__)

# Database setup
client = MongoClient(os.getenv('db_uri'))

def delayed_shutdown():
    time.sleep(1)  # give Flask time to send the response
    os.kill(os.getpid(), signal.SIGTERM)

@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    token = request.headers.get("X-SHUTDOWN-TOKEN")
    decrypted_token = decrypt(token, os.getenv('secret_key'))

    # 🔐 Protect this endpoint
    if decrypted_token != os.getenv('password'):
        return jsonify({"error": "Unauthorized"}), 403

    # ✅ Shutdown in background after response is sent
    thread = threading.Thread(target=delayed_shutdown)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "Terminating masking engine"}), 200

@app.route('/api/health', methods=['GET'])
def app_health():
     """Health check endpoint"""
    
     return jsonify({'status': 'healthy', 'service': 'redaction-api'}), 200

@app.after_request
def add_security_headers(response):
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; object-src 'none'; require-trusted-types-for 'script';"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, post-check=0, pre-check=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/api/mask', methods=['POST'], provide_automatic_options=False)
def mask():
    bytes_data = request.data
    header_password = request.headers.get('X-Password')
    filename = request.headers.get('X-Filename')
    mimetype = request.headers.get('X-Mimetype')
    page = request.headers.get('page')
    OUTPUT_FOLDER = request.headers.get('X-Output-Folder')
    
    if header_password:
        decrypted_key = decrypt(header_password, os.getenv('secret_key'))

        if decrypted_key == os.getenv('password'):

            # pattern = r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,99}"
            # if not re.fullmatch(pattern, filename, re.IGNORECASE):
                # return jsonify({'status':'failure',"message": "Invalid filename"}), 400
            # filename = secure_filename(filename)
        
            if not filename:
                print(f"Filename is not present for this document, therefore giving it a unique ID as filename")
                doc_name = uuid.uuid4()

            else:
                doc_name = filename.split(".")[0]
            
            if mimetype in ('tiff', 'tif', 'pdf') :
                redacted = mask_aadhaar_image(bytes_data, mimetype, doc_name)
                
                if redacted.get("status") == "masked":
                    # Step 4: Decode masked image back from Base64
                    masked_img_bytes = base64.b64decode(redacted["masked_image_base64"])
                    # output_path = os.path.join(OUTPUT_FOLDER, f"{doc_name}_masked.{mimetype}")
                    # with open(output_path, 'wb') as f:
                        # f.write(masked_img_bytes)   

                    client.masking_audit.audit_details.insert_one({
                        "doc_name": doc_name,
                        "status": redacted.get("status"),
                        "date": datetime.now()
                        })

                    # Step 5: Return raw bytes with appropriate headers
                    response = make_response(masked_img_bytes)
                    response.headers.set('status','masked')
                    response.headers.set('masked_page_numbers', redacted.get("masked_page_numbers"))
                    response.headers.set('partially_masked_page_numbers', redacted.get("partially_masked_page_numbers"))
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(5)
                    return response    
                else:

                    client.masking_audit.audit_details.insert_one({
                        "doc_name": doc_name,
                        "status": redacted.get("status"),
                        "date": datetime.now()
                        })
                    
                    response = make_response('')        
                    response.headers.set('status','unmasked')
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(5)
                    return response        
                
            elif mimetype in ('jpeg','jpg','png'):
                redacted = mask_aadhaar_image(bytes_data, mimetype, doc_name)
                
                if redacted.get("status") == "masked":
                    # Step 4: Decode masked image back from Base64
                    masked_img_bytes = base64.b64decode(redacted["masked_image_base64"])
                    # output_path = os.path.join(OUTPUT_FOLDER, f"{doc_name}_masked.{mimetype}")
                    # with open(output_path, 'wb') as f:
                    #     f.write(masked_img_bytes)   

                    # Step 5: Return raw bytes with appropriate headers

                    client.masking_audit.audit_details.insert_one({
                        "doc_name": doc_name,
                        "status": redacted.get("status"),
                        "date": datetime.now()
                        })


                    response = make_response(masked_img_bytes)
                    response.headers.set('status','masked')
                    response.headers.set('masked_page_numbers', redacted.get("masked_page_numbers"))
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(5)
                    return response  
                   
                else:

                    client.masking_audit.audit_details.insert_one({
                        "doc_name": doc_name,
                        "status": redacted.get("status"),
                        "date": datetime.now()
                        })

                    response = make_response('')        
                    response.headers.set('status','unmasked')
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(5)
                    return response
                
            else:
                return jsonify({'status':'failure','message':'Unsupported mime type'}),400

        else:
            return jsonify({'status':'failure','message':'You are not authorized to access this API'}),401

    else:
        return jsonify({'status':'failure','message':'You are not authorized to access this API'}),401

@app.route('/detect', methods=['POST'])
def detect():
    raw_data = request.data
    header_password = request.headers.get('X-Password')
    filename = request.headers.get('X-Filename')
    mimetype = request.headers.get('X-Mimetype')
    OUTPUT_FOLDER = request.headers.get('X-Output-Folder')
    
    if header_password:
        decrypted_key = decrypt(header_password, os.getenv('secret_key'))

        if decrypted_key == os.getenv('password'):
        
            if not filename:
                print(f"Filename is not present for this document, therefore giving it a unique ID as filename")
                doc_name = uuid.uuid4()

            else:
                doc_name = filename.split(".")[0]
            
            if mimetype in ('tiff', 'tif') :
                base64_data = base64.b64encode(raw_data).decode('utf-8')
                redacted = image_classification(base64_data, mimetype, doc_name)
                response = make_response(redacted)
                return response     
                
            else:
                redacted = image_classification(raw_data, mimetype, doc_name)
                response = make_response(redacted)
                return response       
                
        else:
             return jsonify({'status':'failure','message':'bad key sent in request headers'}),400

    else:
        return jsonify({'status':'failure','message':'key is missing in API request headers'}),401


