from ultralytics import YOLO



if __name__ == "__main__":
    model = YOLO("yolo26n.pt")
    
    results = model("https://ultralytics.com/images/bus.jpg")
    r = results[0]
    
    for box in r.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        print(f"Class ID: {class_id}, Confidence: {confidence:.2f}, Box: {box.xyxy[0].tolist()}")