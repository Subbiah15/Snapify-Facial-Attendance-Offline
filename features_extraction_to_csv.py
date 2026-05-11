# Extract features from images and save into teacher-specific CSV

import os
import dlib
import csv
import numpy as np
import logging
import cv2
import argparse

#  Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

#  Get face landmarks
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

#  Use Dlib resnet50 model to get 128D face descriptor
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")


#  Return 128D features for single image

def return_128d_features(path_img):
    img_rd = cv2.imread(path_img)
    faces = detector(img_rd, 1)

    logging.info("%-40s %-20s", " Image with faces detected:", path_img)

    # For photos of faces saved, we need to make sure that we can detect faces from the cropped images
    if len(faces) != 0:
        shape = predictor(img_rd, faces[0])
        face_descriptor = face_reco_model.compute_face_descriptor(img_rd, shape)
    else:
        face_descriptor = 0
        logging.warning("no face")
    return face_descriptor


#   Return the mean value of 128D face descriptor for person X

def return_features_mean_personX(path_face_personX):
    features_list_personX = []
    photos_list = os.listdir(path_face_personX)
    if photos_list:
        for i in range(len(photos_list)):
            #  return_128d_features()  128D  / Get 128D features for single image of personX
            logging.info("%-40s %-20s", " / Reading image:", path_face_personX + "/" + photos_list[i])
            features_128d = return_128d_features(path_face_personX + "/" + photos_list[i])
            #  Jump if no face detected from image
            if features_128d == 0:
                i += 1
            else:
                features_list_personX.append(features_128d)
    else:
        logging.warning(" Warning: No images in%s/", path_face_personX)

   
    if features_list_personX:
        features_mean_personX = np.array(features_list_personX, dtype=object).mean(axis=0)
    else:
        features_mean_personX = np.zeros(128, dtype=object, order='C')
    return features_mean_personX


def main():
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description='Feature Extraction')
    parser.add_argument('--teacher', type=str, default='', help='Teacher email for data isolation')
    args = parser.parse_args()

    # Teacher-specific paths
    if args.teacher:
        path_images = f"data/data_faces_from_camera/{args.teacher}/"
        csv_output = f"data/features_{args.teacher}.csv"
    else:
        path_images = "data/data_faces_from_camera/"
        csv_output = "data/features_all.csv"

    if not os.path.isdir(path_images) or not os.listdir(path_images):
        logging.warning("No face data found in %s", path_images)
        return

    #  Get the order of latest person
    person_list = os.listdir(path_images)
    person_list.sort()

    with open(csv_output, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        for person in person_list:
            # Get the mean/average features of face/personX, it will be a list with a length of 128D
            logging.info("%s%s", path_images, person)
            features_mean_personX = return_features_mean_personX(path_images + person)

            parts = person.split('_')
            # New format: "person_X_ROLL_Name" → parts = ['person', 'X', 'ROLL', 'Name']
            # Old format: "person_X_Name"      → parts = ['person', 'X', 'Name']
            # Bare format: "person_X"           → parts = ['person', 'X']
            if len(parts) >= 4:
                # New format with roll number: use roll_number as identifier
                person_identifier = parts[2]  # roll_number
            elif len(parts) == 3:
                # Old format: use name as identifier
                person_identifier = parts[2]
            else:
                # Bare format
                person_identifier = person

            features_mean_personX = np.insert(features_mean_personX, 0, person_identifier, axis=0)
            # features_mean_personX will be 129D, identifier (roll_number) + 128 features
            writer.writerow(features_mean_personX)
            logging.info('\n')
        logging.info("Save all the features of faces registered into: %s", csv_output)


if __name__ == '__main__':
    main()