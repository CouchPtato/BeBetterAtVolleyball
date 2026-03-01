import streamlit as st
import cv2
import tempfile
import mediapipe as mp
import numpy as np
import collections

# Page configuration
st.set_page_config(
    page_title="Be Better at Volleyball",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        border: none;
        color: white;
        text-align: center;
    }
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        display: block;
    }
    .feedback-card {
        background: white;
        border-radius: 8px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        border-left: 5px solid #ef4444;
    }
    .feedback-good {
        border-left-color: #10b981;
    }
    .info-box {
        background: linear-gradient(135deg, #e0f2fe 0%, #bfdbfe 100%);
        border-left: 4px solid #0284c7;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .header-box {
        text-align: center;
        color: white;
        padding: 2.5rem;
        border-radius: 15px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        margin-bottom: 2rem;
        box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
    }
    .header-box h1 {
        margin: 0;
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .header-box p {
        margin: 0.8rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.95;
        font-weight: 300;
    }
    </style>
""", unsafe_allow_html=True)

# Colors for pose visualization
GOOD_COLOR = (16, 185, 129)  # Green
CAUTION_COLOR = (245, 158, 11)  # Amber
BAD_COLOR = (239, 68, 68)  # Red
CIRCLE_COLOR = (255, 255, 255)  # White
FONT_SCALE = 0.7
FONT_COLOR = (255, 255, 255)
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

def get_performance_rating(avg_l_knee, avg_r_knee, avg_back, avg_l_arm, avg_r_arm):
    """Calculate overall performance rating"""
    issues = 0
    if avg_l_knee > 120 and avg_r_knee > 120:
        issues += 1
    if avg_back < 30:
        issues += 1
    if avg_l_arm < 150 and avg_r_arm < 150:
        issues += 1
    
    if issues == 0:
        return "🌟 Excellent", "#10b981"
    elif issues == 1:
        return "✨ Good", "#3b82f6"
    elif issues == 2:
        return "⚠️ Needs Work", "#f59e0b"
    else:
        return "❌ Poor Form", "#ef4444"

# Header
st.markdown("""
    <div class="header-box">
        <h1>🏐 Be Better at Volleyball</h1>
        <p>AI-Powered Form Analysis & Real-Time Coaching</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("")

# Sidebar Configuration
with st.sidebar:
    st.markdown("### ⚙️ Settings & Guidelines")
    
    st.markdown("**📹 Input Mode**")
    mode = st.radio("Select your input:", ["📁 Upload Video", "📷 Live Webcam"], label_visibility="collapsed")
    
    st.markdown("**🎯 Track Movement**")
    track_mode = st.radio("Select skill to analyze:", ["🤝 Receiving", "💥 Spiking"], label_visibility="collapsed")
    
    st.divider()
    
    st.markdown("**💡 Best Practices**")
    st.info("""
    📍 **Position**: Film from the side  
    💡 **Lighting**: Good lighting required  
    📏 **Distance**: 6-8 feet from camera  
    👕 **Clothing**: Fitted clothes work best
    """)
    
    st.divider()
    
    st.markdown("**📋 Form Standards**")
    
    if track_mode == "🤝 Receiving":
        st.markdown("""
        **✅ Excellent Form:**
        - Knees: 90-120° bend
        - Back: Lean forward 30°+
        - Arms: Extended 150°+
        
        **⚠️ Areas to Improve:**
        - Knees bending too little
        - Standing too upright
        - Arms too bent or tucked
        """)
    else:  # Spiking
        st.markdown("""
        **✅ Excellent Form:**
        - Approach: Explosive jump
        - Arm swing: Full extension
        - Wrist snap: Crisp follow-through
        
        **⚠️ Areas to Improve:**
        - Weak arm extension
        - Poor jump timing
        - Inconsistent contact point
        """)

# Main content
uploaded_file = None
if mode == "📁 Upload Video":
    st.markdown("### 📁 Upload Your Video")
    st.markdown(f"**Analyzing: {track_mode}**", help="Selected skill from sidebar settings")
    uploaded_file = st.file_uploader("Choose a volleyball video (MP4)", type=["mp4"], label_visibility="collapsed", key="video_upload")

if mode == "📷 Live Webcam" or uploaded_file is not None:
    st.markdown(f"### 📹 Live Analysis - {track_mode}")
    st.divider()
    
    if mode == "📷 Live Webcam":
        cap = cv2.VideoCapture(0)
    else:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        cap = cv2.VideoCapture(tfile.name)
    
    # Create placeholders
    video_col, stats_col = st.columns([3, 1], gap="medium")
    
    with video_col:
        st.markdown("**📸 Video Feed**")
        video_placeholder = st.empty()
    
    with stats_col:
        st.markdown("**📊 Metrics**")
        stats_placeholder = st.empty()
    
    st.markdown("**🎯 Feedback**")
    feedback_placeholder = st.empty()
    
    frame_count = 0
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
        issues = []

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

            # Feedback generation based on tracking mode
            if track_mode == "🤝 Receiving":
                # Receiving form checks
                if avg_l_knee > 120 and avg_r_knee > 120:
                    feedback.append("Bend knees more")
                    correction_parts.append("LEG")
                    issues.append(("Knees", f"{(avg_l_knee + avg_r_knee) / 2:.1f}° (Target: <120°)", False))
                else:
                    issues.append(("Knees", f"{(avg_l_knee + avg_r_knee) / 2:.1f}°", True))
                
                if avg_back < 30:
                    feedback.append("Lean forward more")
                    correction_parts.append("TORSO")
                    issues.append(("Back Angle", f"{avg_back:.1f}° (Target: >30°)", False))
                else:
                    issues.append(("Back Angle", f"{avg_back:.1f}°", True))
                
                if avg_l_arm < 150 and avg_r_arm < 150:
                    feedback.append("Straighten arms")
                    correction_parts.append("ARM")
                    issues.append(("Arms", f"{(avg_l_arm + avg_r_arm) / 2:.1f}° (Target: >150°)", False))
                else:
                    issues.append(("Arms", f"{(avg_l_arm + avg_r_arm) / 2:.1f}°", True))
            
            else:  # Spiking mode
                # Get arm heights (lower y value = higher position)
                l_elbow_y = landmarks[13].y
                r_elbow_y = landmarks[14].y
                l_wrist_y = landmarks[15].y
                r_wrist_y = landmarks[16].y
                l_shoulder_y = landmarks[11].y
                r_shoulder_y = landmarks[12].y
                
                # Check arm height (elbows should be above shoulders for spiking)
                avg_elbow_y = (l_elbow_y + r_elbow_y) / 2
                avg_shoulder_y = (l_shoulder_y + r_shoulder_y) / 2
                arm_height_good = avg_elbow_y < avg_shoulder_y * 0.9  # Elbows should be higher
                
                if not arm_height_good:
                    feedback.append("Raise arms higher")
                    correction_parts.append("ARM")
                    issues.append(("Arm Height", "Too Low ⬇️ (Target: Above Shoulder)", False))
                else:
                    issues.append(("Arm Height", "Adequate ⬆️", True))
                
                # Check arm extension (arm bend angle should be high for full extension)
                avg_arm_bend = (avg_l_arm + avg_r_arm) / 2
                if avg_arm_bend < 120:
                    feedback.append("Extend arm fully when hitting")
                    correction_parts.append("ARM")
                    issues.append(("Arm Extension", f"{avg_arm_bend:.1f}° (Target: >120°)", False))
                else:
                    issues.append(("Arm Extension", f"{avg_arm_bend:.1f}°", True))
                
                # Check knee bend for power
                avg_knee = (avg_l_knee + avg_r_knee) / 2
                if avg_knee > 130:
                    feedback.append("Less knee bend for faster spike")
                    correction_parts.append("LEG")
                    issues.append(("Knee Bend", f"{avg_knee:.1f}° (Lower = Better)", False))
                else:
                    issues.append(("Knee Bend", f"{avg_knee:.1f}°", True))

            # Draw skeleton
            for start_idx, end_idx in mp_pose.POSE_CONNECTIONS:
                start = landmarks[start_idx]
                end = landmarks[end_idx]
                color = GOOD_COLOR

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
                    3
                )

            for lm in landmarks:
                cv2.circle(image, (int(lm.x * w), int(lm.y * h)), 3, CIRCLE_COLOR, -1)

        # Add feedback text overlay
        for idx, f in enumerate(feedback):
            cv2.putText(image, f"⚠️ {f}", (10, 30 + idx * 25), FONT, FONT_SCALE, BAD_COLOR, 2)

        frame_count += 1
        
        # Display video
        with video_col:
            video_placeholder.image(image, channels="RGB")
        
        # Display stats
        if results.pose_landmarks and frame_count % 3 == 0:
            with stats_col:
                for metric_name, metric_value, is_good in issues:
                    color_class = "feedback-good" if is_good else ""
                    status = "✅" if is_good else "⚠️"
                    st.markdown(f"""
                        <div class="metric-card">
                            <span class="metric-label">{status} {metric_name}</span>
                            <span class="metric-value">{metric_value.split('°')[0]}°</span>
                        </div>
                    """, unsafe_allow_html=True)
            
            with feedback_placeholder.container():
                if feedback:
                    cols = st.columns(len(feedback)) if feedback else [st.empty()]
                    for idx, msg in enumerate(feedback):
                        with cols[idx] if len(feedback) > 1 else st.container():
                            st.error(f"⚠️ {msg}")

    cap.release()
    st.success("✅ Analysis Complete!")