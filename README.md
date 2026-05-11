<div align="center">
  <h1>📸 Snapify Offline Attendance System</h1>
  <p><i>A smart, robust, and offline facial recognition system for seamless attendance tracking.</i></p>

  ![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
  ![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
  ![Dlib](https://img.shields.io/badge/Dlib-Face%20Recognition-orange.svg)
  ![Flask](https://img.shields.io/badge/Flask-Web%20Dashboard-lightgrey.svg)
</div>

---

## 📖 Overview

**Snapify** is a complete, end-to-end facial recognition attendance solution designed to run entirely offline. By leveraging the power of **OpenCV** and the **Dlib ResNet V1 Model**, Snapify accurately registers student faces, extracts high-dimensional facial features, and recognizes individuals in real-time to automatically log their attendance into a local SQLite database.

It features a unified **Tkinter Desktop Launcher** that guides you step-by-step through the process, and a beautiful **Flask Web Dashboard** to view, filter, and manage the attendance records.

## ✨ Features

- **🧑‍🎓 Easy Face Registration**: A guided UI to capture and safely crop student faces directly from your webcam.
- **🧠 Advanced Feature Extraction**: Converts captured faces into 128D mathematical feature vectors for highly accurate recognition.
- **⏱️ Real-Time Attendance**: Dynamically scans the camera feed, identifies registered students, draws bounding boxes, and records their presence automatically.
- **📊 Web Dashboard**: A built-in local web server to browse attendance records by Subject/Class and Date.
- **🔒 Fully Offline & Secure**: No internet connection required. All biometric data and attendance records stay safely on your local machine.

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have **Python 3.8+** installed on your system.

### 2. Installation
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/yourusername/Snapify-Offline-Attendance.git
cd Snapify-Offline-Attendance
pip install -r requirements.txt
```

### 3. Download the Dlib Models
For the facial recognition AI to work, download the pre-trained Dlib models:
1. Download the models from [this Google Drive Link](https://drive.google.com/drive/folders/12It2jeNQOxwStBxtagL1vvIJokoz-DL4?usp=sharing).
2. Place the downloaded `.dat` files inside the `data/data_dlib/` folder in this repository.

---

## 🛠️ How to Use Snapify

The entire system is managed through a single, easy-to-use Launcher interface.

Simply run the launcher from your terminal:
```bash
python launcher.py
```

From the Launcher dashboard, follow the **4-Step Workflow**:

### Step 1: Register Faces 📸
Click **Launch Camera** to open the registration window. Enter the student's details, face the camera, and press `N` to capture multiple angles of their face. The system will cleanly crop and save the images.

### Step 2: Extract Features ⚙️
Click **Extract** to process the newly captured images. Snapify will convert the photos into a mathematically readable `.csv` file. *(Note: You must click this every time you register a new student).*

### Step 3: Take Attendance ✅
Enter your class/subject name and click **Start**. The camera will open and instantly begin scanning for faces. When it recognizes a registered student, a bounding box will appear with their name, and they will be marked as "Present" in the database. 
- *Press `Q` on your keyboard to close the attendance camera.*

### Step 4: View Dashboard 📈
Click **Open Dashboard** to launch the local web server. Open your browser to view the attendance sheets, filter by date, and verify who attended which class.

---

## 📂 Project Structure

```text
Snapify_Offline_Attendance/
├── launcher.py                      # Main UI to manage the entire workflow
├── get_faces_from_camera_tkinter.py # Face registration & cropping module
├── features_extraction_to_csv.py    # Dlib 128D feature extraction script
├── attendance_taker.py              # Real-time webcam recognition module
├── app.py                           # Flask Web Dashboard server
├── attendance.db                    # SQLite database storing attendance records
├── data/
│   ├── data_dlib/                   # Directory for AI models (.dat files)
│   ├── data_faces_from_camera/      # Raw student photos saved here
│   └── features_all.csv             # Extracted facial signatures
└── requirements.txt                 # Python dependencies
```

## 🤝 Contributing

Contributions are always welcome! If you have ideas for improvements, new features, or find any bugs, please feel free to submit a **Pull Request** or open an **Issue**.

## 🛡️ License

This project is completely open-source and free to use.

<div align="center">
  <i>Built with ❤️ for hassle-free attendance management.</i>
</div>
