import streamlit as st
import cv2
import tempfile
import mediapipe as mp
import numpy as np
import collections

GOOD_COLOR = (0, 215, 255)
BAD_COLOR = (255, 0, 0)
CIRCLE_COLOR = (255, 255, 255)
FONT_SCALE = 0.5
FONT_COLOR = (255, 215, 0)
FONT = cv2.FONT_HERSHEY_SIMPLEX

angle_buffer = {
    'l_knee': collections.deque(maxlen=15),
    'r_knee': collections.deque(maxlen=15),
    'back': collections.deque(maxlen=15),
    'l_arm': collections.deque(maxlen=15),
    'r_arm': collections.deque(maxlen=15)
}

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(static_image_mode=False, model_complexity=1, enable_segmentation=False)
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
st.subheader("Your AI-powered coach for perfect passes!")
st.sidebar.title("🏐 Volleyball Mode")
st.sidebar.markdown("**Tip:** Use a side view for best tracking!")

mode = st.radio("🏐 Choose Input Mode:", ["📁 Upload Video", "📷 Use Webcam"])

uploaded_file = None
if mode == "📁 Upload Video":
    uploaded_file = st.file_uploader("📁 Upload a video", type=["mp4"])

stframe = st.empty()

if mode == "📷 Use Webcam" or uploaded_file is not None:
    if mode == "📷 Use Webcam":
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

            def pt(idx):
                return [landmarks[idx].x * w, landmarks[idx].y * h]

            l_hip, l_knee, l_ankle = pt(23), pt(25), pt(27)
            r_hip, r_knee, r_ankle = pt(24), pt(26), pt(28)
            l_shoulder, l_elbow, l_wrist = pt(11), pt(13), pt(15)
            r_shoulder, r_elbow, r_wrist = pt(12), pt(14), pt(16)

            l_knee_angle = calculate_angle(l_hip, l_knee, l_ankle)
            r_knee_angle = calculate_angle(r_hip, r_knee, r_ankle)
            l_arm_bend = calculate_angle(l_shoulder, l_elbow, l_wrist)
            r_arm_bend = calculate_angle(r_shoulder, r_elbow, r_wrist)
            back_angle = calculate_back_angle(l_shoulder, l_hip)

            angle_buffer['l_knee'].append(l_knee_angle)
            angle_buffer['r_knee'].append(r_knee_angle)
            angle_buffer['back'].append(back_angle)
            angle_buffer['l_arm'].append(l_arm_bend)
            angle_buffer['r_arm'].append(r_arm_bend)

            avg_l_knee = np.mean(angle_buffer['l_knee'])
            avg_r_knee = np.mean(angle_buffer['r_knee'])
            avg_back = np.mean(angle_buffer['back'])
            avg_l_arm = np.mean(angle_buffer['l_arm'])
            avg_r_arm = np.mean(angle_buffer['r_arm'])

            if avg_l_knee > 120 and avg_r_knee > 120:
                feedback.append("Bend knees more")
                correction_parts.append("LEG")
            if avg_back < 30:
                feedback.append("Lean forward more")
                correction_parts.append("TORSO")
            if avg_l_arm < 150 and avg_r_arm < 150:
                feedback.append("Straighten arms")
                correction_parts.append("ARM")

            for start_idx, end_idx in mp_pose.POSE_CONNECTIONS:
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                color = (0, 255, 0)

                if (
                    ("LEG" in correction_parts and start_idx in [23,24,25,26,27,28] and end_idx in [23,24,25,26,27,28]) or
                    ("TORSO" in correction_parts and start_idx in [11,12,23,24] and end_idx in [11,12,23,24]) or
                    ("ARM" in correction_parts and start_idx in [11,12,13,14,15,16] and end_idx in [11,12,13,14,15,16])
                ):
                    color = BAD_COLOR

                cv2.line(
                    image,
                    (int(start.x * w), int(start.y * h)),
                    (int(end.x * w), int(end.y * h)),
                    color,
                    2
                )

            for lm in landmarks:
                cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 2, CIRCLE_COLOR, -1)

        y_pos = 30
        for f in feedback:
            cv2.putText(image, f, (10, y_pos), FONT, FONT_SCALE, FONT_COLOR, 1, cv2.LINE_AA)
            y_pos += 20

        stframe.image(image, channels="RGB")

    cap.release()