import os, signal, re, time, threading
import base64
import uuid
from services.mask_image import mask_aadhaar_image, image_classification
from flask import Flask, jsonify, request, redirect, url_for, render_template, session, flash,send_file, abort, make_response
from flask_session import Session  # Import Flask-Session
import sqlite3
from werkzeug.security import check_password_hash
from datetime import datetime
import logging
from flask_cors import CORS
from utils import encrypt_decrypt
from dotenv import load_dotenv
from config.logging_config import setup_logger
from werkzeug.utils import secure_filename

load_dotenv()
log = setup_logger()

app = Flask(__name__)

# Database setup
DATABASE = 'masking_audit.db'

def delayed_shutdown():
    time.sleep(1)  # give Flask time to send the response
    os.kill(os.getpid(), signal.SIGTERM)

@app.route("/shutdown", methods=["POST"])
def shutdown():
    token = request.headers.get("X-SHUTDOWN-TOKEN")
    decrypted_token = encrypt_decrypt.decrypt(token, os.getenv('secret_key'))

    # 🔐 Protect this endpoint
    if decrypted_token != os.getenv('password'):
        return jsonify({"error": "Unauthorized"}), 403

    # ✅ Shutdown in background after response is sent
    thread = threading.Thread(target=delayed_shutdown)
    thread.daemon = True
    thread.start()

    return jsonify({"status": "Terminating masking engine"}), 200

@app.route('/health', methods=['GET'])
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

@app.route('/mask', methods=['POST'], provide_automatic_options=False)
def mask():
    bytes_data = request.data
    header_password = request.headers.get('X-Password')
    filename = request.headers.get('X-Filename')
    mimetype = request.headers.get('X-Mimetype')
    page = request.headers.get('page')
    OUTPUT_FOLDER = request.headers.get('X-Output-Folder')
    
    if header_password:
        decrypted_key = encrypt_decrypt.decrypt(header_password, os.getenv('secret_key'))

        if decrypted_key == os.getenv('password'):

            # pattern = r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,99}"
            # if not re.fullmatch(pattern, filename, re.IGNORECASE):
                # return jsonify({'status':'failure',"message": "Invalid filename"}), 400
            # filename = secure_filename(filename)
        
            if not filename:
                log.info(f"Filename is not present for this document, therefore giving it a unique ID as filename")
                doc_name = uuid.uuid4()

            else:
                doc_name = filename.split(".")[0]
            
            if mimetype in ('tiff', 'tif', 'pdf') :
                redacted = mask_aadhaar_image(bytes_data, mimetype, doc_name)
                
                if redacted.get("status") == "masked":
                    # Step 4: Decode masked image back from Base64
                    masked_img_bytes = base64.b64decode(redacted["masked_image_base64"])
                    output_path = os.path.join(OUTPUT_FOLDER, f"{doc_name}_masked.{mimetype}")
                    with open(output_path, 'wb') as f:
                        f.write(masked_img_bytes)   

                    # Step 5: Return raw bytes with appropriate headers
                    response = make_response(masked_img_bytes)
                    response.headers.set('status','masked')
                    response.headers.set('masked_page_numbers', redacted.get("masked_page_numbers"))
                    response.headers.set('partially_masked_page_numbers', redacted.get("partially_masked_page_numbers"))
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(10)
                    return response    
                else:
                    response = make_response('')        
                    response.headers.set('status','unmasked')
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(10)
                    return response        
                
            elif mimetype in ('jpeg','jpg','png'):
                redacted = mask_aadhaar_image(bytes_data, mimetype, doc_name, page)
                
                if redacted.get("status") == "masked":
                    # Step 4: Decode masked image back from Base64
                    masked_img_bytes = base64.b64decode(redacted["masked_image_base64"])
                    output_path = os.path.join(OUTPUT_FOLDER, f"{doc_name}_masked.{mimetype}")
                    with open(output_path, 'wb') as f:
                            f.write(masked_img_bytes)   

                    # Step 5: Return raw bytes with appropriate headers
                    response = make_response(masked_img_bytes)
                    response.headers.set('status','masked')
                    response.headers.set('masked_page_numbers', redacted.get("masked_page_numbers"))
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(15)
                    return response  
                   
                else:
                    response = make_response('')        
                    response.headers.set('status','unmasked')
                    response.headers.set('unmasked_page_numbers', redacted.get("unmasked_page_numbers"))
                    response.headers.set('remark', redacted.get("remark"))
                    time.sleep(15)
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
        decrypted_key = encrypt_decrypt.decrypt(header_password, os.getenv('secret_key'))

        if decrypted_key == os.getenv('password'):
        
            if not filename:
                log.info(f"Filename is not present for this document, therefore giving it a unique ID as filename")
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
    
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/audit-history')
def audit_hsitory():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_details')
    rows = cursor.fetchall()
    conn.close()
    
    records = [dict(row) for row in rows]
    
    return render_template('audit_history.html', records=records)

@app.route('/file-mask')
def file_mask():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('file_mask.html')

@app.route('/bulk-mask')
def bulk_mask():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('directory_masking.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()

    # Fetch accuracy data
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN accuracy <= 50 THEN 1 ELSE 0 END) as count_0_50,
            SUM(CASE WHEN accuracy > 50 AND accuracy <= 90 THEN 1 ELSE 0 END) as count_50_90,
            SUM(CASE WHEN accuracy > 90 THEN 1 ELSE 0 END) as count_above_90
        FROM audit_details
    ''')
    accuracy_counts = cursor.fetchone() or (0, 0, 0)

    # Prepare accuracy data for rendering in the template
    accuracy_data = {
        '0-50': accuracy_counts[0],
        '50-90': accuracy_counts[1],
        'above-90': accuracy_counts[2]
    }

    # Fetch yearly processing data
    cursor.execute('''
        SELECT 
            strftime('%Y', create_date) as year,
            COUNT(*) as count
        FROM audit_details
        GROUP BY year
    ''')
    yearly_counts = cursor.fetchall()

    # Prepare yearly data for rendering in the template
    yearly_data = {year: count for year, count in yearly_counts}

    # Fetch masked and unmasked counts
    cursor.execute('''
        SELECT 
            SUM(CASE WHEN masking_status = 'masked' THEN 1 ELSE 0 END) as masked_count,
            SUM(CASE WHEN masking_status = 'unmasked' THEN 1 ELSE 0 END) as unmasked_count
        FROM audit_details
    ''')
    mask_counts = cursor.fetchone() or (0, 0)

    # Prepare masked and unmasked counts for rendering in the template
    masked_count = mask_counts[0]
    unmasked_count = mask_counts[1]

    conn.close()

    return render_template('dashboard.html', accuracy_data=accuracy_data, yearly_data=yearly_data, masked_count=masked_count, unmasked_count=unmasked_count)

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('masking_audit.db')
    cursor = conn.cursor()

    # Fetch total Aadhar processed count
    cursor.execute('SELECT COUNT(*) FROM audit_details')
    total_aadhar_processed = cursor.fetchone()[0] or 0

    # Fetch earliest create date (Live Since)
    cursor.execute('SELECT MIN(create_date) FROM audit_details')
    live_since_str = cursor.fetchone()[0] 

    # Convert live_since_str to datetime if it's not None
    #live_since = datetime.strptime(live_since_str, '%Y-%m-%d %H:%M:%S.%f') if live_since_str else None
    live_since = datetime.strptime(live_since_str, '%Y-%m-%d %H:%M:%S') if live_since_str else None
    

    # Fetch average accuracy
    cursor.execute('SELECT AVG(accuracy) FROM audit_details')
    average_accuracy = cursor.fetchone()[0] or 0.0

    conn.close()

    return render_template('home.html', total_aadhar_processed=total_aadhar_processed,
                           live_since=live_since, average_accuracy=average_accuracy)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')
    # return redirect(url_for('home'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/open_attachment/<path:file_path>')
def open_attachment(file_path):
    # Decode the URL-encoded file path
    decoded_path = file_path.replace('%20', ' ')

    print(f"Decode path:- {decoded_path}")
    
    # Check if the file exists
    if os.path.exists(decoded_path):
        if decoded_path.endswith(".tiff"):
            try:
                return send_file(file_path, mimetype='image/tiff', as_attachment=False)
            except Exception as e:
                return str(e), 500
        
        else:
            try:
                return send_file(decoded_path, as_attachment=False)
            except Exception as e:
                return str(e)
    else:
        abort(404, description="File not found")

# Setup logging
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == '__main__':
    app.run(debug=True)
    app.run(host="0.0.0.0", port=5000)



