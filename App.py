import streamlit as st
import cv2
import tempfile
import numpy as np
import collections
import mediapipe as mp

from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core import base_options
from mediapipe.framework.formats import landmark_pb2

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE = 0.5
FONT_COLOR = (255, 215, 0)
BAD_COLOR = (255, 0, 0)
GOOD_COLOR = (0, 255, 0)

angle_buffer = {
    'l_knee': collections.deque(maxlen=15),
    'r_knee': collections.deque(maxlen=15),
    'back': collections.deque(maxlen=15),
    'l_arm': collections.deque(maxlen=15),
    'r_arm': collections.deque(maxlen=15),
}

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180 / np.pi)
    return 360 - angle if angle > 180 else angle

def calculate_back_angle(shoulder, hip):
    vertical = [hip[0], hip[1] - 100]
    return calculate_angle(shoulder, hip, vertical)

options = vision.PoseLandmarkerOptions(
    base_options=base_options.BaseOptions(model_asset_path="pose_landmarker.task"),
    running_mode=vision.RunningMode.VIDEO,
    num_poses=1
)
landmarker = vision.PoseLandmarker.create_from_options(options)

st.title("🏐 Volleyball Receive Analyzer")
mode = st.radio("Choose Mode", ["Upload Video", "Webcam"])
stframe = st.empty()

uploaded_file = None
if mode == "Upload Video":
    uploaded_file = st.file_uploader("Upload video", type=["mp4"])

if mode == "Webcam" or uploaded_file:
    if mode == "Webcam":
        cap = cv2.VideoCapture(0)
    else:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        cap = cv2.VideoCapture(tfile.name)

    frame_id = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (800, 450))
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect_for_video(mp_image, frame_id)
        frame_id += 1

        feedback = []

        if result.pose_landmarks:
            lm = result.pose_landmarks[0]
            h, w, _ = frame.shape

            def pt(i):
                return [lm[i].x * w, lm[i].y * h]

            l_hip, l_knee, l_ankle = pt(23), pt(25), pt(27)
            r_hip, r_knee, r_ankle = pt(24), pt(26), pt(28)
            l_sh, l_el, l_wr = pt(11), pt(13), pt(15)
            r_sh, r_el, r_wr = pt(12), pt(14), pt(16)

            angle_buffer['l_knee'].append(calculate_angle(l_hip, l_knee, l_ankle))
            angle_buffer['r_knee'].append(calculate_angle(r_hip, r_knee, r_ankle))
            angle_buffer['l_arm'].append(calculate_angle(l_sh, l_el, l_wr))
            angle_buffer['r_arm'].append(calculate_angle(r_sh, r_el, r_wr))
            angle_buffer['back'].append(calculate_back_angle(l_sh, l_hip))

            if np.mean(angle_buffer['l_knee']) > 120 and np.mean(angle_buffer['r_knee']) > 120:
                feedback.append("Bend knees more")
            if np.mean(angle_buffer['back']) < 30:
                feedback.append("Lean forward more")
            if np.mean(angle_buffer['l_arm']) < 150 and np.mean(angle_buffer['r_arm']) < 150:
                feedback.append("Straighten arms")

            proto = landmark_pb2.NormalizedLandmarkList()
            proto.landmark.extend(lm)
            mp.solutions.drawing_utils.draw_landmarks(
                frame,
                proto,
                mp.solutions.pose.POSE_CONNECTIONS
            )

        y = 30
        for f in feedback:
            cv2.putText(frame, f, (10, y), FONT, FONT_SCALE, FONT_COLOR, 1)
            y += 20

        stframe.image(frame, channels="BGR")

    cap.release()