import os
import pickle
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Polygon, Circle, Ellipse
import numpy as np
import speech_recognition as sr
import difflib
from nltk.stem import WordNetLemmatizer
import mediapipe as mp
import threading
import time

# ---------------- Configuration ----------------
DATA_FILE = "landmarks_data.pkl"
RECOGNITION_FILE = "recognition_data.pkl"

# ---------------- NLP Setup ----------------
lemmatizer = WordNetLemmatizer()
FILLER_WORDS = {"is", "am", "are", "the", "a", "an", "was", "were", "to", "of", "will", "has", "have", "been", "can", "could", "should", "would", "with"}

# ---------------- UI Theme ----------------
UI_COLORS = {
    "bg": "#1f1f24",
    "panel": "#2a2a33",
    "panel_alt": "#24242b",
    "text": "#f0f0f5",
    "muted": "#b9b9c6",
    "accent": "#ff69b4",
    "accent_2": "#00d1d1",
    "danger": "#ff5252",
    "success": "#44d07d",
    "warning": "#ffb300",
    "border": "#3a3a45",
}

UI_FONTS = {
    "title": ("Segoe UI", 18, "bold"),
    "h2": ("Segoe UI", 14, "bold"),
    "h3": ("Segoe UI", 12, "bold"),
    "body": ("Segoe UI", 11),
    "mono": ("Consolas", 10),
}

# ---------------- Visualization Constants (Reference Image Colors) ----------------
FINGER_LANDMARKS = {
    'thumb': [0, 1, 2, 3, 4],
    'index': [0, 5, 6, 7, 8],
    'middle': [0, 9, 10, 11, 12],
    'ring': [0, 13, 14, 15, 16],
    'pinky': [0, 17, 18, 19, 20]
}

SKIN_COLOR = '#fcdcc6'     # humanModel Palette
SKIN_SHADOW = '#eac3a5'
HAIR_COLOR = '#6d351d'
JACKET_COLOR = '#9cb1c2'
LAPEL_COLOR = '#4b5d6a'
SHIRT_COLOR = '#ff9800'
PANTS_COLOR = '#6d4c41'
SHOE_COLOR = '#bc5a3a'
NOSE_COLOR = '#f89a94'
EYE_COLOR = '#2e7d32' 

# ---------------- Global Data ----------------
LANDMARKS_DB = {}   # For Avatar (Text -> Sign)
RECOGNITION_DB = {} # For Webcam (Sign -> Text) - Contains Lists of Variations

def load_landmarks_data():
    global LANDMARKS_DB, RECOGNITION_DB
    
    # 1. Load Avatar Data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                LANDMARKS_DB = pickle.load(f)
            print("Loaded Avatar data.")
        except Exception as e:
            print(f"Error loading Avatar DB: {e}")
            
    # 2. Load Recognition Data (ST Dataset)
    if os.path.exists(RECOGNITION_FILE):
        try:
            with open(RECOGNITION_FILE, 'rb') as f:
                RECOGNITION_DB = pickle.load(f)
            print(f"Loaded Recognition data ({len(RECOGNITION_DB)} words).")
        except Exception as e:
            print(f"Error loading Recognition DB: {e}")
            RECOGNITION_DB = {}
    else:
        print("Recognition data not found. New signs will be saved to new file.")
        RECOGNITION_DB = {}

# ---------------- Utility Functions ----------------
def normalize_word(word):
    base = lemmatizer.lemmatize(word, pos='v') 
    return base

def isl_transform(sentence):
    words = sentence.lower().replace("?", "").split()
    clean_words = [normalize_word(w) for w in words if w not in FILLER_WORDS]
    return clean_words

# ---------------- Avatar Visualizer (Upgraded to match Image) ----------------
class AvatarVisualizer:
    def __init__(self, ax):
        self.ax = ax
        self.ax.set_facecolor(UI_COLORS["bg"])
        self.ax.set_xlim(0, 640)
        self.ax.set_ylim(480, 0)
        self.ax.axis('off')
        
        # --- Layers (Bottom to Top) ---
        
        # 1. Hair Background
        self.hair_bg = Ellipse((0,0), 60, 70, facecolor=HAIR_COLOR)
        self.hair_bg.set_zorder(1)
        self.ax.add_patch(self.hair_bg)

        # 2. Neck
        self.neck = Ellipse((0,0), 10, 15, facecolor=SKIN_COLOR)
        self.neck.set_zorder(5)
        self.ax.add_patch(self.neck)

        # 3. Lower Torso (Brown Pants area)
        self.torso_lower = Polygon([[0,0]], closed=True, facecolor=PANTS_COLOR)
        self.torso_lower.set_zorder(6)
        self.ax.add_patch(self.torso_lower)

        # 4. Torso (Jacket & Shirt)
        # Inner Shirt (Orange)
        self.shirt_center = Polygon([[0,0]], closed=True, facecolor=SHIRT_COLOR)
        self.shirt_center.set_zorder(10)
        self.ax.add_patch(self.shirt_center)
        
        # Jacket Sides
        self.jacket_L = Polygon([[0,0]], closed=True, facecolor=JACKET_COLOR)
        self.jacket_R = Polygon([[0,0]], closed=True, facecolor=JACKET_COLOR)
        self.lapel_L = Polygon([[0,0]], closed=True, facecolor=LAPEL_COLOR)
        self.lapel_R = Polygon([[0,0]], closed=True, facecolor=LAPEL_COLOR)
        for p in [self.jacket_L, self.jacket_R, self.lapel_L, self.lapel_R]:
            p.set_zorder(11)
            self.ax.add_patch(p)

        # 5. Sleeves
        self.sleeve_L = Ellipse((0,0), 18, 25, facecolor=JACKET_COLOR)
        self.sleeve_R = Ellipse((0,0), 18, 25, facecolor=JACKET_COLOR)
        self.sleeve_L.set_zorder(12)
        self.sleeve_R.set_zorder(12)
        self.ax.add_patch(self.sleeve_L)
        self.ax.add_patch(self.sleeve_R)

        # 6. Limbs
        self.limb_lines = []
        self.limb_definitions = [
            (11, 13, JACKET_COLOR, 10), (13, 15, JACKET_COLOR, 9), # Left Arm
            (12, 14, JACKET_COLOR, 10), (14, 16, JACKET_COLOR, 9), # Right Arm
            (25, 27, PANTS_COLOR, 9), (26, 28, PANTS_COLOR, 9),   # Lower Legs
        ]
        for start, end, col, width in self.limb_definitions:
            line, = self.ax.plot([], [], color=col, linewidth=width, solid_capstyle='round')
            line.set_zorder(13)
            self.limb_lines.append(line)

        # 7. Head & Face
        self.head_circle = Ellipse((0,0), 45, 50, facecolor=SKIN_COLOR)
        self.head_circle.set_zorder(15)
        self.ax.add_patch(self.head_circle)
        
        self.eye_L = Circle((0,0), 3, facecolor=EYE_COLOR)
        self.eye_R = Circle((0,0), 3, facecolor=EYE_COLOR)
        for e in [self.eye_L, self.eye_R]: e.set_zorder(19); self.ax.add_patch(e)
        
        self.nose = Ellipse((0,0), 6, 10, facecolor=NOSE_COLOR)
        self.nose.set_zorder(19)
        self.ax.add_patch(self.nose)
        
        self.mouth, = self.ax.plot([], [], color='#4e342e', linewidth=2)
        self.mouth.set_zorder(20)

        # 8. Hair Swoop
        self.hair_swoop = Polygon([[0,0]], closed=True, facecolor=HAIR_COLOR)
        self.hair_swoop.set_zorder(25)
        self.ax.add_patch(self.hair_swoop)
        
        # 9. Shoes
        self.shoe_L = Ellipse((0,0), 24, 12, facecolor=SHOE_COLOR)
        self.shoe_R = Ellipse((0,0), 24, 12, facecolor=SHOE_COLOR)
        self.shoe_L.set_zorder(30); self.shoe_R.set_zorder(30)
        self.ax.add_patch(self.shoe_L); self.ax.add_patch(self.shoe_R)

        # 10. Hands (5 Fingers)
        self.hand_L_palm = Ellipse((0,0), 9, 8, facecolor=SKIN_COLOR)
        self.hand_R_palm = Ellipse((0,0), 9, 8, facecolor=SKIN_COLOR)
        self.hand_L_fingers = [Ellipse((0,0), 2, 7, facecolor=SKIN_COLOR) for _ in range(5)]
        self.hand_R_fingers = [Ellipse((0,0), 2, 7, facecolor=SKIN_COLOR) for _ in range(5)]
        
        for p in [self.hand_L_palm, self.hand_R_palm]: 
            p.set_zorder(40); self.ax.add_patch(p)
        for f_list in [self.hand_L_fingers, self.hand_R_fingers]:
            for f in f_list: f.set_zorder(41); self.ax.add_patch(f)

        # 11. Skeleton Points and Lines
        self.skeleton_lines = []
        self.skeleton_connections = [
            (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
            (11, 23), (12, 24), (23, 24), (23, 25), (25, 27),
            (24, 26), (26, 28)
        ]
        for _ in range(len(self.skeleton_connections)):
            line, = self.ax.plot([], [], color='#00e5ff', linewidth=1, alpha=0.5, zorder=49)
            self.skeleton_lines.append(line)

        self.point_patches = []
        for _ in range(33):
            p = Circle((0,0), 1.2, facecolor='white', edgecolor='#00e5ff', linewidth=0.5, zorder=50)
            self.point_patches.append(p)
            self.ax.add_patch(p)
            
        self.hand_lines = []
        for _ in range(12): 
             line, = self.ax.plot([], [], color=SKIN_COLOR, linewidth=3, solid_capstyle='round')
             line.set_zorder(31)
             self.hand_lines.append(line)

        self.hand_joints, = self.ax.plot([], [], 'o', color='white', markersize=1.5)
        self.hand_joints.set_zorder(32)

        # 12. Caption Text
        self.caption_text = self.ax.text(620, 450, "", color=UI_COLORS["accent"], 
                                         fontsize=16, fontweight='bold', ha='right', 
                                         va='center', zorder=100)

    def update(self, points, caption=""):
        if not points or len(points) < 75:
            return

        points = np.array(points)
        points[:, 0] *= 640
        points[:, 1] *= 480
        
        def get_valid_pt(idx):
             if idx >= len(points): return None
             p = points[idx]
             if p[0] <= 1.0 and p[1] <= 1.0: return None
             return p

        nose = get_valid_pt(0)
        p11, p12 = get_valid_pt(11), get_valid_pt(12) # Shoulders
        p23, p24 = get_valid_pt(23), get_valid_pt(24) # Hips
        p25, p26 = get_valid_pt(25), get_valid_pt(26) # Knees
        p27, p28 = get_valid_pt(27), get_valid_pt(28) # Ankles
        
        # Fallbacks for missing knee points (25, 26) to prevent crashes
        if p25 is None and p23 is not None: p25 = p23 + [0, 40]
        if p26 is None and p24 is not None: p26 = p24 + [0, 40]
        
        # --- Update Visuals ---
        shoulder_dist = np.linalg.norm(p11 - p12) if p11 is not None and p12 is not None else 60
        head_r = shoulder_dist * 0.45

        # 1. Head & Face Details
        if nose is not None:
            self.head_circle.center = (nose[0], nose[1])
            self.head_circle.width = head_r * 2.1
            self.head_circle.height = head_r * 2.3
            
            # Refined Hair Swoop (Raised to clear eyes)
            cx, cy = nose[0], nose[1]
            s_pts = np.array([
                [cx - head_r*1.1, cy - head_r*0.35], [cx - head_r*0.9, cy - head_r*0.9],
                [cx + head_r*0.2, cy - head_r*1.1], [cx + head_r*1.1, cy - head_r*0.8],
                [cx + head_r*1.0, cy - head_r*0.2], [cx + head_r*0.2, cy - head_r*0.4],
                [cx - head_r*0.6, cy - head_r*0.1]
            ])
            self.hair_swoop.set_xy(s_pts)
            
            self.hair_bg.center = (nose[0], nose[1] - head_r*0.2)
            self.hair_bg.width = head_r * 2.4
            self.hair_bg.height = head_r * 2.6
            
            # Eyes, Nose, Mouth
            e_x, e_y = head_r * 0.45, head_r * 0.1
            self.eye_L.center = (nose[0] - e_x, nose[1] - e_y)
            self.eye_R.center = (nose[0] + e_x, nose[1] - e_y)
            self.nose.center = (nose[0], nose[1] + head_r * 0.15)
            self.mouth.set_data([nose[0] - 8, nose[0] + 8], [nose[1] + head_r * 0.55, nose[1] + head_r * 0.55])
        
        # 2. Neck
        if nose is not None and p11 is not None:
            mid_shoulder = (p11 + p12) / 2
            self.neck.center = (nose[0], (nose[1] + mid_shoulder[1]) / 2)
            self.neck.width = head_r * 0.5
            self.neck.height = abs(nose[1] - mid_shoulder[1]) * 0.7

        # 3. Torso (Jacket & Shirt)
        if all(p is not None for p in [p11, p12, p23, p24]):
            mid_s = (p11 + p12) / 2
            neck_bottom = mid_s + [0, shoulder_dist * 0.1]
            waist_L, waist_R = p23 + [-10, 0], p24 + [10, 0]
            hip_mid = (p23 + p24) / 2
            
            # Orange Shirt Center
            p_w = shoulder_dist * 0.2
            self.shirt_center.set_xy([neck_bottom + [-p_w, 0], neck_bottom + [p_w, 0], hip_mid + [p_w, 0], hip_mid + [-p_w, 0]])
            
            # Jacket Sides
            self.jacket_L.set_xy([p11, neck_bottom + [-p_w*0.8, 0], hip_mid + [-p_w*0.8, 0], waist_L])
            self.jacket_R.set_xy([p12, neck_bottom + [p_w*0.8, 0], hip_mid + [p_w*0.8, 0], waist_R])
            
            # Lapels
            l_w, l_h = shoulder_dist * 0.25, shoulder_dist * 0.5
            self.lapel_L.set_xy([neck_bottom + [-p_w*0.8, 0], neck_bottom + [-p_w*0.8-l_w, l_h], neck_bottom + [-p_w*0.8, l_h*0.3]])
            self.lapel_R.set_xy([neck_bottom + [p_w*0.8, 0], neck_bottom + [p_w*0.8+l_w, l_h], neck_bottom + [p_w*0.8, l_h*0.3]])

            # Lower Torso (Pants top)
            self.torso_lower.set_xy([waist_L, waist_R, p24 + [0, 20], p23 + [0, 20]])
            
            # Sleeves
            self.sleeve_L.center = (p11[0], p11[1] + 12)
            self.sleeve_R.center = (p12[0], p12[1] + 12)

        # --- Limbs & Shoes ---
        for i, (start, end, _, _) in enumerate(self.limb_definitions):
            pS, pE = get_valid_pt(start), get_valid_pt(end)
            if pS is not None and pE is not None:
                self.limb_lines[i].set_data([pS[0], pE[0]], [pS[1], pE[1]])
            else:
                self.limb_lines[i].set_data([], [])
            
        # Shoes
        if p27 is not None: self.shoe_L.center = (p27[0], p27[1] + 5); self.shoe_L.set_visible(True)
        else: self.shoe_L.set_visible(False)
        if p28 is not None: self.shoe_R.center = (p28[0], p28[1] + 5); self.shoe_R.set_visible(True)
        else: self.shoe_R.set_visible(False)

        # --- Hands (5 Fingers) ---
        wrist_L, wrist_R = get_valid_pt(15), get_valid_pt(16)
        if wrist_L is not None:
            self.hand_L_palm.center = wrist_L
            offsets = [(-4, -7), (-1.5, -7.5), (1, -7.5), (3.5, -7), (-4.5, -2)]
            angles = [0, 0, 0, 0, 45]
            for i, f in enumerate(self.hand_L_fingers):
                f.center = wrist_L + offsets[i]
                f.angle = angles[i]
        
        if wrist_R is not None:
            self.hand_R_palm.center = wrist_R
            offsets = [(-3.5, -7), (-1, -7.5), (1.5, -7.5), (4, -7), (4.5, -2)]
            angles = [0, 0, 0, 0, -45]
            for i, f in enumerate(self.hand_R_fingers):
                f.center = wrist_R + offsets[i]
                f.angle = angles[i]

        # --- Skeleton Rigging ---
        for i, (idx1, idx2) in enumerate(self.skeleton_connections):
            p1, p2 = get_valid_pt(idx1), get_valid_pt(idx2)
            if p1 is not None and p2 is not None:
                self.skeleton_lines[i].set_data([p1[0], p2[0]], [p1[1], p2[1]])
                self.skeleton_lines[i].set_visible(True)
            else:
                self.skeleton_lines[i].set_visible(False)

        # --- Visibility of Landmarks ---
        for i, p in enumerate(self.point_patches):
            v_pt = get_valid_pt(i)
            if v_pt is not None:
                p.center = v_pt
                p.set_visible(True)
            else:
                p.set_visible(False)

        # 5. Hand Landmark logic (Rigging lines)
        valid_hands = []
        for start_idx in [33, 54]:
            root_pt = get_valid_pt(start_idx)
            if root_pt is not None:
                valid_hands.append({'start_idx': start_idx, 'root': root_pt})

        assignments = [] 
        if len(valid_hands) == 1:
            h = valid_hands[0]
            dist_L = np.linalg.norm(h['root'] - wrist_L) if wrist_L is not None else 1e6
            dist_R = np.linalg.norm(h['root'] - wrist_R) if wrist_R is not None else 1e6
            target = wrist_L if dist_L < dist_R else wrist_R
            if target is not None: assignments.append((h, target))
        elif len(valid_hands) == 2:
            h0, h1 = valid_hands[0], valid_hands[1]
            cost_A = np.linalg.norm(h0['root'] - wrist_L) + np.linalg.norm(h1['root'] - wrist_R) if wrist_L is not None and wrist_R is not None else 1e6
            cost_B = np.linalg.norm(h0['root'] - wrist_R) + np.linalg.norm(h1['root'] - wrist_L) if wrist_L is not None and wrist_R is not None else 1e6
            if cost_A < cost_B:
                if wrist_L is not None: assignments.append((h0, wrist_L))
                if wrist_R is not None: assignments.append((h1, wrist_R))
            else:
                if wrist_R is not None: assignments.append((h0, wrist_R))
                if wrist_L is not None: assignments.append((h1, wrist_L))

        line_idx = 0
        all_hand_points = []
        for hand_obj, wrist_pt in assignments:
            start_idx = hand_obj['start_idx']
            root_pt = hand_obj['root']
            if line_idx < len(self.hand_lines):
                self.hand_lines[line_idx].set_data([wrist_pt[0], root_pt[0]], [wrist_pt[1], root_pt[1]])
                line_idx += 1
            for finger_name, ids in FINGER_LANDMARKS.items():
                if line_idx >= len(self.hand_lines): break
                indices = [start_idx + k for k in ids]
                pts = [get_valid_pt(ix) for ix in indices]
                valid_pts_arr = [p for p in pts if p is not None]
                if len(valid_pts_arr) > 1:
                    arr = np.array(valid_pts_arr)
                    self.hand_lines[line_idx].set_data(arr[:, 0], arr[:, 1])
                    all_hand_points.extend(valid_pts_arr)
                else:
                    self.hand_lines[line_idx].set_data([], [])
                line_idx += 1
        
        while line_idx < len(self.hand_lines):
            self.hand_lines[line_idx].set_data([], [])
            line_idx += 1
        if all_hand_points:
             arr = np.array(all_hand_points)
             self.hand_joints.set_data(arr[:, 0], arr[:, 1])
        else: self.hand_joints.set_data([], [])

        # Update Caption
        self.caption_text.set_text(caption.upper())

# ---------------- Sign Recognition Logic (Restored) ----------------
class SignMatcher:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands
        self.pose = self.mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.hands = self.mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5)

    def extract_frame_landmarks(self, image):
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results_pose = self.pose.process(image_rgb)
        results_hands = self.hands.process(image_rgb)
        frame_data = [(0.0, 0.0)] * 75
        if results_pose.pose_landmarks:
            for i, lm in enumerate(results_pose.pose_landmarks.landmark):
                frame_data[i] = (lm.x, lm.y)
        if results_hands.multi_hand_landmarks and results_hands.multi_handedness:
            for hand_landmarks, handedness in zip(results_hands.multi_hand_landmarks, results_hands.multi_handedness):
                label = handedness.classification[0].label 
                start_index = 33 if label == 'Left' else 54
                for i, lm in enumerate(hand_landmarks.landmark):
                    if start_index + i < 75:
                        frame_data[start_index + i] = (lm.x, lm.y)
        return frame_data

    def normalize_sequence(self, sequence):
        normalized_seq = []
        for frame in sequence:
            pts = np.array(frame)
            if np.max(pts) == 0: continue
            p11, p12 = pts[11], pts[12]
            if p11[0] == 0 and p12[0] == 0:
                center = np.mean(pts[pts[:,0]!=0], axis=0) if np.any(pts[:,0]!=0) else np.array([0.5, 0.5])
                scale = 1.0
            else:
                center = (p11 + p12) / 2.0
                scale = np.linalg.norm(p11 - p12)
                if scale < 0.01: scale = 1.0
            centered = (pts - center) / scale
            relevant_indices = [11,12,13,14,15,16] + list(range(33, 75))
            features = centered[relevant_indices]
            normalized_seq.append(features.flatten()) 
        return np.array(normalized_seq)

    def get_motion_features(self, sequence):
        seq_norm = self.normalize_sequence(sequence)
        if len(seq_norm) < 2: return np.array([])
        smoothed = []
        w = 3
        for i in range(len(seq_norm)):
            start = max(0, i - w + 1)
            avg = np.mean(seq_norm[start:i+1], axis=0)
            smoothed.append(avg)
        return np.diff(np.array(smoothed), axis=0)

    def dtw_distance(self, s1, s2):
        n, m = len(s1), len(s2)
        if abs(n - m) > 25 and min(n,m) < 10: return float('inf')
        dtw = np.full((n+1, m+1), float('inf'))
        dtw[0, 0] = 0
        w = max(10, abs(n-m)) 
        for i in range(1, n+1):
            for j in range(max(1, i-w), min(m+1, i+w)):
                cost = np.linalg.norm(s1[i-1] - s2[j-1])
                dtw[i, j] = cost + min(dtw[i-1, j], dtw[i, j-1], dtw[i-1, j-1])
        return dtw[n, m]

    def match_sign(self, input_sequence, language):
        if not input_sequence or len(input_sequence) < 10: return "Too Short", 0.0
        if not RECOGNITION_DB: return "DB Empty", 0.0
        input_motion = self.get_motion_features(input_sequence)
        if len(input_motion) < 5: return "No Motion", 0.0
        candidates = []
        for word, templates_list in RECOGNITION_DB.items():
            if not isinstance(templates_list, list) or not isinstance(templates_list[0], (list, tuple, np.ndarray)):
                 templates_list = [templates_list]
            best_word_dist = float('inf')
            for template in templates_list:
                if len(template) < 5: continue
                temp_motion = self.get_motion_features(template)
                if len(temp_motion) < 5: continue
                dist = self.dtw_distance(input_motion, temp_motion)
                norm_dist = dist / (len(input_motion) + len(temp_motion))
                if norm_dist < best_word_dist: best_word_dist = norm_dist
            candidates.append((best_word_dist, word))
        candidates.sort(key=lambda x: x[0])
        if not candidates: return None, 0.0
        best_dist, best_word = candidates[0]
        confidence = max(0.0, 1.0 - best_dist * 2) * 100
        return best_word, confidence

# ---------------- Main App ----------------
class AvatarApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sign Language System (Upgraded Visuals)")
        self.root.geometry("1280x760")
        self.root.configure(bg=UI_COLORS["bg"])
        self.running = True
        self.recording = False
        self.training_mode = False
        self.recorded_frames = []
        self.webcam_job = None

        load_landmarks_data()
        self.sign_matcher = SignMatcher()

        # Tabs
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=UI_COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=UI_COLORS["panel"], foreground=UI_COLORS["text"], padding=[16, 6])
        style.map("TNotebook.Tab", background=[("selected", UI_COLORS["accent"])])

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab1 = tk.Frame(self.notebook, bg=UI_COLORS["bg"])
        self.tab2 = tk.Frame(self.notebook, bg=UI_COLORS["bg"])
        self.notebook.add(self.tab1, text="Text to Sign (Avatar)")
        self.notebook.add(self.tab2, text="Sign to Text (Webcam)")
        
        self.setup_avatar_tab()
        self.setup_webcam_tab()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        if self.webcam_job: self.root.after_cancel(self.webcam_job)
        if hasattr(self, 'cap'): self.cap.release()
        self.root.destroy()

    def setup_avatar_tab(self):
        body = tk.Frame(self.tab1, bg=UI_COLORS["bg"])
        body.pack(fill=tk.BOTH, expand=True)
        left = tk.Frame(body, width=350, bg=UI_COLORS["panel"])
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = tk.Frame(body, bg="black")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(left, text="Avatar Controls", bg=UI_COLORS["panel"], fg=UI_COLORS["accent"], font=UI_FONTS["h2"]).pack(pady=20)
        self.lang_var = tk.StringVar(value="ISL")
        ttk.Combobox(left, textvariable=self.lang_var, values=["ISL", "ASL"], state="readonly").pack(pady=5)
        self.txt_input = tk.Text(left, height=4, width=30, bg=UI_COLORS["panel_alt"], fg="white", font=UI_FONTS["body"], insertbackground="white")
        self.txt_input.pack(pady=10, padx=15)
        self.txt_input.insert("1.0", "Type here...")
        
        tk.Button(left, text="🎤 SPEECH", command=self.start_speech_threads, bg=UI_COLORS["accent_2"], fg="white", font=UI_FONTS["h3"], width=15).pack(pady=5)
        
        self.avatar_status = tk.Label(left, text="Ready", bg=UI_COLORS["panel"], fg=UI_COLORS["muted"])
        self.avatar_status.pack(pady=5)
        
        tk.Button(left, text="PLAY", command=self.play_sign, bg=UI_COLORS["accent"], fg="white", font=UI_FONTS["h3"], width=15).pack(pady=10)

        self.fig, self.ax = plt.subplots(figsize=(5,5))
        self.fig.patch.set_facecolor(UI_COLORS["bg"])
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self.visualizer = AvatarVisualizer(self.ax)

    def play_sign(self):
        sentence = self.txt_input.get("1.0", tk.END).strip()
        lang = self.lang_var.get()
        if not sentence or sentence == "Type here...": return
        words = isl_transform(sentence)
        word_frames = []
        if lang in LANDMARKS_DB:
            for w in words:
                if w in LANDMARKS_DB[lang]: 
                    word_frames.append((w, LANDMARKS_DB[lang][w]))
        
        if word_frames: 
            self.avatar_status.config(text=f"Playing {len(words)} words", fg=UI_COLORS["success"])
            self.run_anim(word_frames)

    def start_speech_threads(self):
        self.avatar_status.config(text="Listening...", fg=UI_COLORS["accent_2"])
        threading.Thread(target=self.analyze_speech, daemon=True).start()

    def analyze_speech(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                text = r.recognize_google(audio)
                self.root.after(0, lambda: self.update_speech_text(text))
            except Exception as e:
                self.root.after(0, lambda: self.avatar_status.config(text="Speech Error", fg=UI_COLORS["danger"]))

    def update_speech_text(self, text):
        self.txt_input.delete("1.0", tk.END)
        self.txt_input.insert("1.0", text)
        self.avatar_status.config(text="Ready", fg=UI_COLORS["muted"])

    def run_anim(self, word_frames):
        self.word_idx = 0
        self.frame_idx = 0
        
        def step():
            if not self.running: return
            
            if self.word_idx < len(word_frames):
                current_word, frames = word_frames[self.word_idx]
                
                if self.frame_idx < len(frames):
                    self.visualizer.update(frames[self.frame_idx], caption=current_word)
                    self.canvas.draw_idle()
                    self.frame_idx += 1
                    self.root.after(30, step)
                else:
                    self.word_idx += 1
                    self.frame_idx = 0
                    self.root.after(10, step) # Small gap between words
            else: 
                self.visualizer.update(None, caption="") # Clear caption
                self.canvas.draw_idle()
                self.avatar_status.config(text="Ready", fg=UI_COLORS["muted"])
        step()

    def setup_webcam_tab(self):
        left = tk.Frame(self.tab2, width=320, bg=UI_COLORS["panel"])
        left.pack(side=tk.LEFT, fill=tk.Y)
        self.cam_panel = tk.Label(self.tab2, bg="black")
        self.cam_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(left, text="Sign Recognition", bg=UI_COLORS["panel"], fg=UI_COLORS["accent_2"], font=UI_FONTS["h2"]).pack(pady=20)
        self.btn_rec = tk.Button(left, text="Start Recording", command=self.toggle_rec, bg=UI_COLORS["panel_alt"], fg="white", width=20, height=2)
        self.btn_rec.pack(pady=10)
        self.lbl_result = tk.Label(left, text="IDLE", bg=UI_COLORS["panel"], fg="yellow", font=UI_FONTS["h2"])
        self.lbl_result.pack(pady=10)
        
        tk.Label(left, text="Teach Word", bg=UI_COLORS["panel"], fg=UI_COLORS["accent"]).pack(pady=(20, 0))
        self.txt_train = tk.Entry(left, font=UI_FONTS["body"])
        self.txt_train.pack(pady=5)
        self.btn_train = tk.Button(left, text="Learn Sign", command=self.toggle_train, bg=UI_COLORS["panel_alt"], fg="white", width=20)
        self.btn_train.pack(pady=10)

        self.cap = cv2.VideoCapture(0)
        self.update_cam()

    def update_cam(self):
        if not self.running: return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            if self.recording:
                lms = self.sign_matcher.extract_frame_landmarks(frame)
                self.recorded_frames.append(lms)
                cv2.circle(frame, (30,30), 15, (0,0,255), -1)
            img = cv2.cvtColor(cv2.resize(frame, (854, 480)), cv2.COLOR_BGR2RGB)
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(img))
            self.cam_panel.imgtk = imgtk
            self.cam_panel.config(image=imgtk)
        self.webcam_job = self.root.after(30, self.update_cam)

    def toggle_rec(self):
        if self.recording: self.stop_rec()
        else: self.recording = True; self.recorded_frames = []; self.btn_rec.config(text="STOP", bg="red")

    def toggle_train(self):
        word = self.txt_train.get().strip()
        if not word: return
        if self.recording: self.stop_rec()
        else: self.recording = True; self.training_mode = True; self.recorded_frames = []; self.btn_train.config(text="STOP", bg="green")

    def stop_rec(self):
        self.recording = False
        self.btn_rec.config(text="Start Recording", bg=UI_COLORS["panel_alt"])
        self.btn_train.config(text="Learn Sign", bg=UI_COLORS["panel_alt"])
        if len(self.recorded_frames) < 15: return
        if self.training_mode:
            self.training_mode = False
            word = self.txt_train.get().strip().lower()
            if word not in RECOGNITION_DB: RECOGNITION_DB[word] = []
            RECOGNITION_DB[word].append(self.recorded_frames)
            with open(RECOGNITION_FILE, 'wb') as f: pickle.dump(RECOGNITION_DB, f)
            messagebox.showinfo("Success", f"Learned {word}")
        else:
            threading.Thread(target=self.analyze).start()

    def analyze(self):
        word, score = self.sign_matcher.match_sign(self.recorded_frames, self.lang_var.get())
        if word and score > 20: self.lbl_result.config(text=f"{word.upper()} ({int(score)}%)")
        else: self.lbl_result.config(text="Not Found")

if __name__ == "__main__":
    root = tk.Tk()
    app = AvatarApp(root)
    root.mainloop()

# nurse works at hospital
# borther buys laptop
# train is late today