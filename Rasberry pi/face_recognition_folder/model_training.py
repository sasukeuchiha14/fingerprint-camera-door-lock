"""
Face Recognition Model Training
Trains face recognition model from images in the dataset folder
"""

import os
from imutils import paths
import face_recognition
import pickle
import cv2


def train_face_model(dataset_path="dataset", output_path="encodings.pickle", model="hog"):
    """
    Train face recognition model from dataset
    
    Args:
        dataset_path: Path to folder containing person subfolders with images
        output_path: Path to save the pickled encodings
        model: Detection model - "hog" (faster, CPU) or "cnn" (accurate, GPU)
    
    Returns:
        Number of faces encoded
    """
    print("[INFO] Starting face encoding process...")
    
    # Get all image paths
    image_paths = list(paths.list_images(dataset_path))
    
    if not image_paths:
        print(f"[ERROR] No images found in {dataset_path}")
        return 0
    
    known_encodings = []
    known_names = []
    
    # Process each image
    for (i, image_path) in enumerate(image_paths):
        print(f"[INFO] Processing image {i + 1}/{len(image_paths)}: {image_path}")
        
        # Extract person name from folder structure
        name = image_path.split(os.path.sep)[-2]
        
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"[WARNING] Failed to load image: {image_path}")
            continue
        
        # Convert BGR to RGB
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        boxes = face_recognition.face_locations(rgb, model=model)
        
        if not boxes:
            print(f"[WARNING] No faces detected in: {image_path}")
            continue
        
        # Get face encodings
        encodings = face_recognition.face_encodings(rgb, boxes)
        
        # Add each encoding to our dataset
        for encoding in encodings:
            known_encodings.append(encoding)
            known_names.append(name)
    
    # Save encodings
    print("[INFO] Serializing encodings...")
    data = {"encodings": known_encodings, "names": known_names}
    
    with open(output_path, "wb") as f:
        f.write(pickle.dumps(data))
    
    print(f"[INFO] Training complete!")
    print(f"[INFO] Encoded {len(known_encodings)} faces from {len(set(known_names))} people")
    print(f"[INFO] Encodings saved to '{output_path}'")
    
    return len(known_encodings)


if __name__ == "__main__":
    # Train model with images from dataset folder
    train_face_model()
