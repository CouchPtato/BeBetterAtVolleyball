import streamlit as st
import cv2
import tempfile
import mediapipe as mp
import numpy as np
import collections

GOOD_COLOR = (0, 215, 255)   # Volleyball yellow-blue
BAD_COLOR = (255, 0, 0)      # Red for corrections
CIRCLE_COLOR = (255, 255, 255)  # White joints

FONT_SCALE = 0.5
FONT_COLOR = (255, 215, 0)   # Yellow text
FONT = cv2.FONT_HERSHEY_SIMPLEX

angle_buffer = {
    'l_knee': collections.deque(maxlen=15),
    'r_knee': collections.deque(maxlen=15),
    'back': collections.deque(maxlen=15),
    'l_arm': collections.deque(maxlen=15),
    'r_arm': collections.deque(maxlen=15)
}
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


# UI DESIGN


st.title("🏐 Volleyball Receive Analyzer")
st.subheader("Your AI-powered coach for perfect passes!")
st.sidebar.title("🏐 Volleyball Mode")
st.sidebar.markdown("**Tip:** Use a side view for best tracking!")


mode = st.radio("🏐 Choose Input Mode:", ["📁 Upload Video", "📷 Use Webcam"])


uploaded_file = None
if mode == "📁 Upload Video":
    uploaded_file = st.file_uploader("📁 Upload a video", type=["mp4"])

stframe = st.empty()


# VIDEO LOOP


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

            
            l_hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP].x * w,
                     landmarks[mp_pose.PoseLandmark.LEFT_HIP].y * h]
            l_knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE].x * w,
                      landmarks[mp_pose.PoseLandmark.LEFT_KNEE].y * h]
            l_ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].x * w,
                       landmarks[mp_pose.PoseLandmark.LEFT_ANKLE].y * h]

            
            r_hip = [landmarks[mp_pose.PoseLandmark.RIGHT_HIP].x * w,
                     landmarks[mp_pose.PoseLandmark.RIGHT_HIP].y * h]
            r_knee = [landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].x * w,
                      landmarks[mp_pose.PoseLandmark.RIGHT_KNEE].y * h]
            r_ankle = [landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].x * w,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ANKLE].y * h]

            
            l_shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x * w,
                          landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y * h]
            l_elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].x * w,
                       landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].y * h]
            l_wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST].x * w,
                       landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y * h]

            
            r_shoulder = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x * w,
                          landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y * h]
            r_elbow = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW].x * w,
                       landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW].y * h]
            r_wrist = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].x * w,
                       landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].y * h]


            l_knee_angle = calculate_angle(l_hip, l_knee, l_ankle)
            r_knee_angle = calculate_angle(r_hip, r_knee, r_ankle)

            l_arm_bend = calculate_angle(l_shoulder, l_elbow, l_wrist)
            r_arm_bend = calculate_angle(r_shoulder, r_elbow, r_wrist)

            back_angle = calculate_back_angle(l_shoulder, l_hip)

            # print("Arm bend:", arm_bend)

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

            # if avg_l_knee > 120 and avg_r_knee > 120 and avg_back < 30 and avg_l_arm < 150 and avg_r_arm < 150:
            #     feedback.append("Perfect Form, Well Done!!")

            for connection in mp_pose.POSE_CONNECTIONS:
                start_idx, end_idx = connection
                start, end = landmarks[start_idx], landmarks[end_idx]
                color = (0, 255, 0)

                if (
                    ("LEG" in correction_parts and start_idx in [23, 24, 25, 26, 27, 28] and end_idx in [23, 24, 25, 26, 27, 28]) or
                    ("TORSO" in correction_parts and start_idx in [11, 12, 23, 24] and end_idx in [11, 12, 23, 24]) or
                    ("ARM" in correction_parts and start_idx in [11, 12, 13, 14, 15, 16] and end_idx in [11, 12, 13, 14, 15, 16])
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
            cv2.putText(image, f, (10, y_pos), FONT, FONT_SCALE, FONT_COLOR, 1, cv2.LINE_AA)
            y_pos += 20

        stframe.image(image, channels="RGB")

    cap.release()