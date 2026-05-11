import dlib
import numpy as np
import cv2
import os
import pandas as pd
import time
import logging
import sqlite3
import datetime
import argparse
import sys


# Dlib  / Use frontal face detector of Dlib
detector = dlib.get_frontal_face_detector()

# Dlib landmark / Get face landmarks
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

# Dlib Resnet Use Dlib resnet50 model to get 128D face descriptor
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")

# Create a connection to the database
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()

# ── Migrate students table: add teacher_email if missing ──
cursor.execute("PRAGMA table_info(students)")
student_cols = [col[1] for col in cursor.fetchall()]
if student_cols and 'teacher_email' not in student_cols:
    cursor.execute("ALTER TABLE students RENAME TO students_old")
    cursor.execute("CREATE TABLE students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")
    cursor.execute("INSERT OR IGNORE INTO students (roll_number, name, phone, email, teacher_email) SELECT roll_number, name, phone, email, '' FROM students_old")
    cursor.execute("DROP TABLE students_old")
    conn.commit()
else:
    cursor.execute("CREATE TABLE IF NOT EXISTS students (roll_number TEXT, name TEXT, phone TEXT, email TEXT, teacher_email TEXT DEFAULT '', PRIMARY KEY (roll_number, teacher_email))")

# ── Database migration: ensure attendance table has correct schema ──
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='attendance'")
result = cursor.fetchone()

needs_migration = False
if result:
    table_sql = result[0]
    if 'roll_number' not in table_sql or 'teacher_email' not in table_sql:
        needs_migration = True
    
    if needs_migration:
        cursor.execute("PRAGMA table_info(attendance)")
        columns = [col[1] for col in cursor.fetchall()]
        has_class_col = 'class_name' in columns
        has_roll_col = 'roll_number' in columns

        cursor.execute("ALTER TABLE attendance RENAME TO attendance_old")
        cursor.execute("CREATE TABLE attendance (roll_number TEXT DEFAULT '', name TEXT, class_name TEXT DEFAULT '', time TEXT, date DATE, teacher_email TEXT DEFAULT '', UNIQUE(roll_number, date, class_name, teacher_email))")
        
        if has_roll_col and has_class_col:
            cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT COALESCE(roll_number, ''), name, COALESCE(class_name, ''), time, date FROM attendance_old")
        elif has_class_col:
            cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT '', name, COALESCE(class_name, ''), time, date FROM attendance_old")
        else:
            cursor.execute("INSERT OR IGNORE INTO attendance (roll_number, name, class_name, time, date) SELECT '', name, '', time, date FROM attendance_old")
        cursor.execute("DROP TABLE attendance_old")
        conn.commit()
        print("Database migrated: updated schema with teacher_email support")
else:
    cursor.execute("CREATE TABLE IF NOT EXISTS attendance (roll_number TEXT DEFAULT '', name TEXT, class_name TEXT DEFAULT '', time TEXT, date DATE, teacher_email TEXT DEFAULT '', UNIQUE(roll_number, date, class_name, teacher_email))")

# Commit changes and close the connection
conn.commit()
conn.close()


class Face_Recognizer:
    def __init__(self, class_name="", teacher_email=""):
        self.class_name = class_name
        self.teacher_email = teacher_email
        self.font = cv2.FONT_ITALIC

        # Roll number to name mapping (loaded from students table)
        self.roll_to_name = {}

        # FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0
        self.fps_show = 0
        self.start_time = time.time()

        # cnt for frame
        self.frame_cnt = 0

        #  Save the features of faces in the database
        self.face_features_known_list = []
        # / Save the name of faces in the database
        self.face_name_known_list = []

        #  List to save centroid positions of ROI in frame N-1 and N
        self.last_frame_face_centroid_list = []
        self.current_frame_face_centroid_list = []

        # List to save names of objects in frame N-1 and N
        self.last_frame_face_name_list = []
        self.current_frame_face_name_list = []

        #  cnt for faces in frame N-1 and N
        self.last_frame_face_cnt = 0
        self.current_frame_face_cnt = 0

        # Save the e-distance for faceX when recognizing
        self.current_frame_face_X_e_distance_list = []

        # Save the positions and names of current faces captured
        self.current_frame_face_position_list = []
        #  Save the features of people in current frame
        self.current_frame_face_feature_list = []

        # e distance between centroid of ROI in last and current frame
        self.last_current_frame_centroid_e_distance = 0

        #  Reclassify after 'reclassify_interval' frames
        self.reclassify_interval_cnt = 0
        self.reclassify_interval = 10

    #  "features_all.csv"  / Get known faces from "features_all.csv"
    def get_face_database(self):
        # Teacher-specific features CSV
        if self.teacher_email:
            csv_path = f"data/features_{self.teacher_email}.csv"
        else:
            csv_path = "data/features_all.csv"

        if os.path.exists(csv_path):
            path_features_known_csv = csv_path
            csv_rd = pd.read_csv(path_features_known_csv, header=None)
            for i in range(csv_rd.shape[0]):
                features_someone_arr = []
                # Convert identifier to clean string (pandas may read numbers as float)
                raw_id = csv_rd.iloc[i][0]
                clean_id = str(int(raw_id)) if isinstance(raw_id, float) and raw_id == int(raw_id) else str(raw_id)
                self.face_name_known_list.append(clean_id)  # roll_number (or name for old data)
                for j in range(1, 129):
                    if csv_rd.iloc[i][j] == '':
                        features_someone_arr.append('0')
                    else:
                        features_someone_arr.append(csv_rd.iloc[i][j])
                self.face_features_known_list.append(features_someone_arr)
            logging.info("Faces in Database: %d", len(self.face_features_known_list))

            # Load roll_number → name mapping from students table
            try:
                conn = sqlite3.connect("attendance.db")
                cursor = conn.cursor()
                cursor.execute("SELECT roll_number, name FROM students WHERE teacher_email = ?", (self.teacher_email,))
                for row in cursor.fetchall():
                    self.roll_to_name[str(row[0])] = row[1]
                conn.close()
            except Exception:
                pass

            return 1
        else:
            logging.warning("'features_all.csv' not found!")
            logging.warning("Please run 'get_faces_from_camera.py' "
                            "and 'features_extraction_to_csv.py' before 'face_reco_from_camera.py'")
            return 0

    def update_fps(self):
        now = time.time()
        # Refresh fps per second
        if str(self.start_time).split(".")[0] != str(now).split(".")[0]:
            self.fps_show = self.fps
        self.start_time = now
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

    @staticmethod
    # / Compute the e-distance between two 128D features
    def return_euclidean_distance(feature_1, feature_2):
        feature_1 = np.array(feature_1)
        feature_2 = np.array(feature_2)
        dist = np.sqrt(np.sum(np.square(feature_1 - feature_2)))
        return dist

    # / Use centroid tracker to link face_x in current frame with person_x in last frame
    def centroid_tracker(self):
        for i in range(len(self.current_frame_face_centroid_list)):
            e_distance_current_frame_person_x_list = []
            #  For object 1 in current_frame, compute e-distance with object 1/2/3/4/... in last frame
            for j in range(len(self.last_frame_face_centroid_list)):
                self.last_current_frame_centroid_e_distance = self.return_euclidean_distance(
                    self.current_frame_face_centroid_list[i], self.last_frame_face_centroid_list[j])

                e_distance_current_frame_person_x_list.append(
                    self.last_current_frame_centroid_e_distance)

            last_frame_num = e_distance_current_frame_person_x_list.index(
                min(e_distance_current_frame_person_x_list))
            self.current_frame_face_name_list[i] = self.last_frame_face_name_list[last_frame_num]

    #  cv2 window / putText on cv2 window
    def draw_note(self, img_rd):
        #  / Add some info on windows
        cv2.putText(img_rd, "Face Recognizer with Deep Learning", (20, 40), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "Frame:  " + str(self.frame_cnt), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:    " + str(self.fps.__round__(2)), (20, 130), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Faces:  " + str(self.current_frame_face_cnt), (20, 160), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Q: Quit", (20, 450), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

        for i in range(len(self.current_frame_face_name_list)):
            img_rd = cv2.putText(img_rd, "Face_" + str(i + 1), tuple(
                [int(self.current_frame_face_centroid_list[i][0]), int(self.current_frame_face_centroid_list[i][1])]),
                                 self.font,
                                 0.8, (255, 190, 0),
                                 1,
                                 cv2.LINE_AA)
    # insert data in database

    def attendance(self, roll_or_name):
        """Record attendance using roll_number. Look up name from students table."""
        roll_number = str(roll_or_name)
        # Look up the display name from roll→name mapping
        display_name = self.roll_to_name.get(roll_number, roll_number)

        current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        conn = sqlite3.connect("attendance.db")
        cursor = conn.cursor()
        # Check if already marked for this class today
        cursor.execute("SELECT * FROM attendance WHERE roll_number = ? AND date = ? AND class_name = ? AND teacher_email = ?", (roll_number, current_date, self.class_name, self.teacher_email))
        existing_entry = cursor.fetchone()

        if existing_entry:
            print(f"{display_name} (Roll: {roll_number}) is already marked as present for {self.class_name} on {current_date}")
        else:
            current_time = datetime.datetime.now().strftime('%H:%M:%S')
            cursor.execute("INSERT INTO attendance (roll_number, name, class_name, time, date, teacher_email) VALUES (?, ?, ?, ?, ?, ?)",
                           (roll_number, display_name, self.class_name, current_time, current_date, self.teacher_email))
            conn.commit()
            print(f"{display_name} (Roll: {roll_number}) marked as present for {self.class_name} on {current_date} at {current_time}")

        conn.close()

    #  Face detection and recognition wit OT from input video stream
    def process(self, stream):
        # 1.  Get faces known from "features.all.csv"
        if self.get_face_database():
            while stream.isOpened():
                self.frame_cnt += 1
                logging.debug("Frame " + str(self.frame_cnt) + " starts")
                flag, img_rd = stream.read()
                
                # Check if frame was captured
                if not flag or img_rd is None:
                    logging.warning("Failed to capture frame")
                    continue
                
                kk = cv2.waitKey(1)

                # 2.  Detect faces for frame X
                try:
                    faces = detector(img_rd, 0)
                except Exception as e:
                    logging.error(f"Error in face detection: {e}")
                    continue

                # 3.  Update cnt for faces in frames
                self.last_frame_face_cnt = self.current_frame_face_cnt
                self.current_frame_face_cnt = len(faces)

                # 4.  Update the face name list in last frame
                self.last_frame_face_name_list = self.current_frame_face_name_list[:]

                # 5.  update frame centroid list
                self.last_frame_face_centroid_list = self.current_frame_face_centroid_list
                self.current_frame_face_centroid_list = []

                # 6.1  if cnt not changes
                if (self.current_frame_face_cnt == self.last_frame_face_cnt) and (
                        self.reclassify_interval_cnt != self.reclassify_interval):
                    logging.debug("scene 1:   No face cnt changes in this frame!!!")

                    self.current_frame_face_position_list = []

                    if "unknown" in self.current_frame_face_name_list:
                        self.reclassify_interval_cnt += 1

                    if self.current_frame_face_cnt != 0:
                        for k, d in enumerate(faces):
                            self.current_frame_face_position_list.append(tuple(
                                [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))
                            self.current_frame_face_centroid_list.append(
                                [int(faces[k].left() + faces[k].right()) / 2,
                                 int(faces[k].top() + faces[k].bottom()) / 2])

                            img_rd = cv2.rectangle(img_rd,
                                                   tuple([d.left(), d.top()]),
                                                   tuple([d.right(), d.bottom()]),
                                                   (255, 255, 255), 2)

                    #  Multi-faces in current frame, use centroid-tracker to track
                    if self.current_frame_face_cnt != 1:
                        self.centroid_tracker()

                    for i in range(self.current_frame_face_cnt):
                        # 6.2 Write names under ROI — show student name instead of roll number
                        roll_id = str(self.current_frame_face_name_list[i])
                        display_name = self.roll_to_name.get(roll_id, roll_id)
                        img_rd = cv2.putText(img_rd, display_name,
                                             self.current_frame_face_position_list[i], self.font, 0.8, (0, 255, 255), 1,
                                             cv2.LINE_AA)
                    self.draw_note(img_rd)

                # 6.2  If cnt of faces changes, 0->1 or 1->0 or ...
                else:
                    logging.debug("scene 2: / Faces cnt changes in this frame")
                    self.current_frame_face_position_list = []
                    self.current_frame_face_X_e_distance_list = []
                    self.current_frame_face_feature_list = []
                    self.reclassify_interval_cnt = 0

                    # 6.2.1  Face cnt decreases: 1->0, 2->1, ...
                    if self.current_frame_face_cnt == 0:
                        logging.debug("  / No faces in this frame!!!")
                        # clear list of names and features
                        self.current_frame_face_name_list = []
                    # 6.2.2 / Face cnt increase: 0->1, 0->2, ..., 1->2, ...
                    else:
                        logging.debug("  scene 2.2  Get faces in this frame and do face recognition")
                        self.current_frame_face_name_list = []
                        for i in range(len(faces)):
                            shape = predictor(img_rd, faces[i])
                            self.current_frame_face_feature_list.append(
                                face_reco_model.compute_face_descriptor(img_rd, shape))
                            self.current_frame_face_name_list.append("unknown")

                        # 6.2.2.1 Traversal all the faces in the database
                        for k in range(len(faces)):
                            logging.debug("  For face %d in current frame:", k + 1)
                            self.current_frame_face_centroid_list.append(
                                [int(faces[k].left() + faces[k].right()) / 2,
                                 int(faces[k].top() + faces[k].bottom()) / 2])

                            self.current_frame_face_X_e_distance_list = []

                            # 6.2.2.2  Positions of faces captured
                            self.current_frame_face_position_list.append(tuple(
                                [faces[k].left(), int(faces[k].bottom() + (faces[k].bottom() - faces[k].top()) / 4)]))

                            # 6.2.2.3 
                            # For every faces detected, compare the faces in the database
                            for i in range(len(self.face_features_known_list)):
                                # 
                                if str(self.face_features_known_list[i][0]) != '0.0':
                                    e_distance_tmp = self.return_euclidean_distance(
                                        self.current_frame_face_feature_list[k],
                                        self.face_features_known_list[i])
                                    logging.debug("      with person %d, the e-distance: %f", i + 1, e_distance_tmp)
                                    self.current_frame_face_X_e_distance_list.append(e_distance_tmp)
                                else:
                                    #  person_X
                                    self.current_frame_face_X_e_distance_list.append(999999999)

                            # 6.2.2.4 / Find the one with minimum e distance
                            similar_person_num = self.current_frame_face_X_e_distance_list.index(
                                min(self.current_frame_face_X_e_distance_list))

                            if min(self.current_frame_face_X_e_distance_list) < 0.45:
                                # Store roll_number as clean string
                                roll_id = str(self.face_name_known_list[similar_person_num])
                                self.current_frame_face_name_list[k] = roll_id
                                display_name = self.roll_to_name.get(roll_id, roll_id)
                                logging.debug("  Face recognition result: %s (%s)", display_name, roll_id)
                                
                                # Insert attendance record
                                self.attendance(roll_id)
                            else:
                                logging.debug("  Face recognition result: Unknown person")

                        # Draw rectangles and names in the else block too
                        for k, d in enumerate(faces):
                            img_rd = cv2.rectangle(img_rd,
                                                   tuple([d.left(), d.top()]),
                                                   tuple([d.right(), d.bottom()]),
                                                   (255, 255, 255), 2)
                        
                        for i in range(self.current_frame_face_cnt):
                            roll_id = str(self.current_frame_face_name_list[i])
                            display_name = self.roll_to_name.get(roll_id, roll_id)
                            img_rd = cv2.putText(img_rd, display_name,
                                                 self.current_frame_face_position_list[i], self.font, 0.8, (0, 255, 255), 1,
                                                 cv2.LINE_AA)

                        # 7.  / Add note on cv2 window
                        self.draw_note(img_rd)

                # 8.  'q'  / Press 'q' to exit
                if kk == ord('q'):
                    break

                self.update_fps()
                cv2.namedWindow("Snapify - Face Recognition System", 1)
                cv2.imshow("Snapify - Face Recognition System", img_rd)

                logging.debug("Frame ends\n\n")

    


    def run(self):
        logging.info("Starting run() method")
        # Try multiple indices and backends
        cap = None
        for index in [0, 1]:
            for backend in [None, cv2.CAP_DSHOW, cv2.CAP_MSMF]:
                logging.info(f"Attempting to open camera index {index} with backend {backend}")
                if backend is None:
                    cap = cv2.VideoCapture(index)
                else:
                    cap = cv2.VideoCapture(index, backend)
                
                if cap.isOpened():
                    logging.info(f"Successfully opened camera {index} with backend {backend}")
                    break
                else:
                    if cap: cap.release()
            if cap and cap.isOpened():
                break
            
        if not cap or not cap.isOpened():
            logging.error("Could not open any camera index (tried 0 and 1)")
            print("\u274c Error: Could not open webcam.")
            print("Please ensure your camera is connected and not being used by another app.")
            sys.exit(1) # Return non-zero to show Error in launcher

        try:
            self.process(cap)
        except Exception as e:
            logging.error(f"Process crashed with error: {e}", exc_info=True)
            sys.exit(1)

        cap.release()
        cv2.destroyAllWindows()
    
   


def main():
    # File-based logging for debugging
    log_file = "attendance_taker_debug.log"
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Starting Attendance Taker...")
    
    parser = argparse.ArgumentParser(description='Face Recognition Attendance Taker')
    parser.add_argument('--class_name', type=str, default='General', help='Class or period name (e.g. Maths, English)')
    parser.add_argument('--teacher', type=str, default='', help='Teacher email for data isolation')
    args = parser.parse_args()
    print(f"Taking attendance for: {args.class_name}")
    Face_Recognizer_con = Face_Recognizer(class_name=args.class_name, teacher_email=args.teacher)
    Face_Recognizer_con.run()


if __name__ == '__main__':
    main()
