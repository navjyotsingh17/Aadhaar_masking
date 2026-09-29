from ultralytics import YOLO
import matplotlib.pyplot as plt
import easyocr
import cv2

# Initialize the EasyOCR reader
reader = easyocr.Reader(['en'])

# Load a model
model = YOLO("aadhardetect2.pt")  # pretrained YOLOv8n model

# List of input images
image_paths = [
    "/Users/akshayduduskar/git/aadharmasking_yolo8/sample/result_9.jpg",
    "/Users/akshayduduskar/git/aadharmasking_yolo8/inputimages_old/img2.jpeg"
]

# Run batched inference on the list of images
results = model(image_paths)  # return a list of Results objects

# Process results list
for i, result in enumerate(results):
    boxes = result.boxes  # Boxes object for bounding box outputs
    
    # Load the original image for displaying
    original_image = cv2.imread(image_paths[i])
    original_image_rgb = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)

    # Visualize the results
    result_plotted = result.plot()

    # Convert result image to OpenCV format for EasyOCR processing
    result_image = cv2.cvtColor(result_plotted, cv2.COLOR_RGB2BGR)

    # Iterate over the detected boxes
    for box in boxes:
        class_id = box.cls  # Class ID of the detected object

        if class_id == 4:  # Check if the class ID is 4
            # Extract the bounding box coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # Draw bounding box and label on the image
            cv2.rectangle(result_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(result_image, f'({x1}, {y1})', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(result_image, f'({x2}, {y2})', (x2, y2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Crop the image around the bounding box
            cropped_image = original_image_rgb[y1:y2, x1:x2]

            # Perform OCR on the cropped image
            ocr_result = reader.readtext(cropped_image)

            # Print OCR content in the console
            print(f"OCR Results for image {i} and bounding box {box}:")
            for text in ocr_result:
                # print(text[1])

    # Display the result image with bounding boxes and coordinates
                plt.imshow(result_image)
                plt.axis('off')
                plt.show()

    # Save the result image
    cv2.imwrite(f"result_{i}.jpg", result_image)									    		
