import streamlit as st
import cv2
import tempfile
import mediapipe as mp
import numpy as np

mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    if angle > 180:
        angle = 360 - angle
    return angle

def calculate_back_angle(shoulder, hip):
    vertical = [hip[0], hip[1] - 100]
    return calculate_angle(shoulder, hip, vertical)

st.title("🏐 Volleyball Receive Analyzer")

mode = st.radio("Choose Input Mode:", ["Upload Video", "Use Webcam"])

uploaded_file = None
if mode == "Upload Video":
    uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov"])

stframe = st.empty()

if mode == "Use Webcam" or uploaded_file is not None:
    if mode == "Use Webcam":
        cap = cv2.VideoCapture(0)
    else:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        cap = cv2.VideoCapture(tfile.name)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (800, 450))
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)

        h, w, _ = image.shape
        feedback = []
        correction_parts = []

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x * w,
                   landmarks[mp_pose.PoseLandmark.LEFT_HIP].y * h]
            knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x * w,
                    landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y * h]
            ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].x * w,
                     landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y * h]

            shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x * w,
                        landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y * h]
            elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].x * w,
                     landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].y * h]
            wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST].x * w,
                     landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y * h]

            knee_angle = calculate_angle(hip, knee, ankle)
            back_angle = calculate_back_angle(shoulder, hip)
            arm_bend = calculate_angle(shoulder, elbow, wrist)

            # print("Arm bend:", arm_bend)

            if knee_angle > 120:
                feedback.append("Bend knees more")
                correction_parts.append("LEG")
            if back_angle < 30:
                feedback.append("Lean forward more")
                correction_parts.append("TORSO")
            if arm_bend < 150:
                feedback.append("Straighten arms")
                correction_parts.append("ARM")

            for connection in mp_pose.POSE_CONNECTIONS:
                start_idx, end_idx = connection
                start, end = landmarks[start_idx], landmarks[end_idx]
                color = (0, 255, 0)

                if (
                    ("LEG" in correction_parts and start_idx in [23, 25, 27] and end_idx in [23, 25, 27]) or
                    ("TORSO" in correction_parts and start_idx in [11, 23] and end_idx in [11, 23]) or
                    ("ARM" in correction_parts and start_idx in [11, 13, 15] and end_idx in [11, 13, 15])
                ):
                    color = (255, 0, 0)

                start_point = (int(start.x * w), int(start.y * h))
                end_point = (int(end.x * w), int(end.y * h))
                cv2.line(image, start_point, end_point, color, thickness = 2)

            for lm in landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(image, (cx, cy), 1, (255, 255, 255), thickness = 2)

        y_pos = 30
        for f in feedback:
            cv2.putText(image, f, (10, y_pos), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (243, 218, 11), 1, cv2.LINE_AA)
            y_pos += 20

        stframe.image(image, channels="RGB")

    cap.release()
