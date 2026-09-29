import cv2
from waitress import serve
from app.app import app

cv2.setNumThreads(1)
cv2.ocl.setUseOpenCL(False)

if __name__ == "__main__":
    print("Masking Engine is running on http://127.0.0.1:5000/mask")
    serve(
        app,
        host="127.0.0.1",
        port=5000,
        threads=1
    )
