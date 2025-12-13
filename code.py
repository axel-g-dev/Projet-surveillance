import streamlit as st
import cv2
import numpy as np
import os
import time
import mysql.connector
from datetime import datetime

# ===============================================================
# CONFIG
# ===============================================================
DEBUG = True
DEBUG_MOTION = False

SAVE_FOLDER = "/Volumes/recordings"
CAM_INDEX = 1

THRESHOLD_VALUE = 30
MIN_AREA = 1000
BLUR_KERNEL = (11, 11)

MIN_TIME_BETWEEN_PHOTOS = 5  # secondes

# DB
DB_CONFIG = {
    'host': '192.168.4.1',
    'port': 3306,
    'user': 'presence',
    'password': '*9RSSFr5bD0WO64qurDY',
    'database': 'presence'
}

# ===============================================================
# STREAMLIT CONFIG
# ===============================================================
st.set_page_config(
    page_title="Surveillance",
    page_icon="⚫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS STYLE
st.markdown("""
<style>
header {visibility: hidden;}

.stImage {
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border: 1px solid #e5e5e7;
}

[data-testid="stSidebar"] {
    background-color: #fbfbfd;
    border-right: 1px solid #e5e5e7;
}

.status-indicator {
    display: inline-block; width: 8px; height: 8px;
    border-radius: 50%; margin-right: 8px;
}
.status-active { background-color: #30d158; }
.status-inactive { background-color: #ff3b30; }
</style>
""", unsafe_allow_html=True)

# ===============================================================
# DATABASE MANAGER 
# ===============================================================
class DatabaseManager:
    def __init__(self):
        self.conn = None

    def connect(self):
        if self.conn and self.conn.is_connected():
            return True
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            if DEBUG: print("[DB] Connexion OK.")
            return True
        except Exception as e:
            print("[DB] ERREUR:", e)
            return False

    def insert(self, event_type, path):
        if not self.connect():
            return False
        try:
            cursor = self.conn.cursor()
            query = "INSERT INTO enregistrement (type, file_path) VALUES (%s, %s)"
            cursor.execute(query, (event_type, path))
            self.conn.commit()
            cursor.close()

            if DEBUG: print(f"[DB] Ajout enregistrement OK → {path}")
            return True

        except Exception as e:
            print("[DB] ERREUR INSERT :", e)
            return False

    def close(self):
        if self.conn and self.conn.is_connected():
            self.conn.close()
            if DEBUG: print("[DB] Connexion fermée.")

# ===============================================================
# SURVEILLANCE MANAGER 
# ===============================================================
class SurveillanceManager:
    def __init__(self):
        self.cap = None
        self.frame_a = None
        self.frame_b = None

        self.last_capture = 0
        self.total_detections = 0
        self.total_saved = 0

        self.db = DatabaseManager()

        if not os.path.exists(SAVE_FOLDER):
            os.makedirs(SAVE_FOLDER)

    def init_camera(self):
        if DEBUG: print("[CAM] Opening camera...")
        self.cap = cv2.VideoCapture(CAM_INDEX)
        if not self.cap.isOpened():
            print("[CAM] ERREUR ouverture caméra.")
            return False

        ok1, f1 = self.cap.read()
        ok2, f2 = self.cap.read()

        if not (ok1 and ok2):
            print("[CAM] ERREUR frames")
            return False

        self.frame_a = f1
        self.frame_b = f2

        if DEBUG:
            print("[CAM] OK. Resolution:",
                  self.cap.get(cv2.CAP_PROP_FRAME_WIDTH),
                  "x",
                  self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        return True

    def release(self):
        if self.cap:
            self.cap.release()
        self.db.close()

    def preprocess(self, f):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(g, BLUR_KERNEL, 0)

    def detect_motion(self, fa, fb):
        diff = cv2.absdiff(fa, fb)
        _, th = cv2.threshold(diff, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
        dil = cv2.dilate(th, None, iterations=2)
        cnts, _ = cv2.findContours(dil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        return [c for c in cnts if cv2.contourArea(c) > MIN_AREA]

    def save_picture(self, frame):
        now = time.time()
        if now - self.last_capture < MIN_TIME_BETWEEN_PHOTOS:
            return False

        self.last_capture = now

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"mvt_{ts}.jpg"
        path = os.path.join(SAVE_FOLDER, filename)

        cv2.imwrite(path, frame)
        self.total_saved += 1

        # BDD
        self.db.insert("mouvement", path)

        if DEBUG: print("[SAVE] Photo:", path)
        return True

    def process(self):
        if self.cap is None:
            return None, False, 0

        fa = self.preprocess(self.frame_a)
        fb = self.preprocess(self.frame_b)

        contours = self.detect_motion(fa, fb)

        if contours:
            self.total_detections += 1
            self.save_picture(self.frame_a)

        # Dessin des contours
        display = self.frame_a.copy()
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(display, (x, y), (x+w, y+h), (48, 209, 88), 2)

        ok, next_frame = self.cap.read()
        if not ok:
            return display, False, len(contours)

        self.frame_a = self.frame_b
        self.frame_b = next_frame

        return display, True, len(contours)

# ===============================================================
# STREAMLIT APP
# ===============================================================
def main():

    if "manager" not in st.session_state:
        st.session_state.manager = SurveillanceManager()
        st.session_state.running = False
        st.session_state.start_time = None
        st.session_state.initialized = False

    manager = st.session_state.manager

    # SIDEBAR
    with st.sidebar:
        st.title("Surveillance")

        if not st.session_state.running:
            if st.button("Démarrer", type="primary"):
                if not st.session_state.initialized:
                    if manager.init_camera():
                        st.session_state.initialized = True
                        st.session_state.start_time = time.time()
                        st.session_state.running = True
                        st.rerun()
                    else:
                        st.error("Erreur caméra")
                else:
                    st.session_state.running = True
                    st.rerun()
        else:
            if st.button("Arrêter"):
                st.session_state.running = False
                manager.release()
                st.rerun()

        st.write("---")
        st.subheader("Statistiques")

        det = st.empty()
        cap = st.empty()
        timing = st.empty()

        st.write("---")
        if st.button("Ouvrir dossier"):
            os.system(f'open "{SAVE_FOLDER}"')

    # MAIN AREA
    if st.session_state.running:
        st.markdown('<span class="status-indicator status-active"></span>En cours', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-indicator status-inactive"></span>Inactif', unsafe_allow_html=True)

    viewer = st.empty()

    # LOOP
    if st.session_state.running:
        while st.session_state.running:
            frame, ok, nb = manager.process()

            if not ok:
                st.error("Erreur flux vidéo")
                st.session_state.running = False
                break

            # Resize (optional)
            h, w = frame.shape[:2]
            r = min(1200 / w, 675 / h)
            frame_resized = cv2.resize(frame, (int(w*r), int(h*r)))

            viewer.image(frame_resized, channels="BGR")

            # Stats
            det.metric("Détections", manager.total_detections)
            cap.metric("Captures", manager.total_saved)

            elapsed = int(time.time() - st.session_state.start_time)
            h_ = elapsed // 3600
            m_ = (elapsed % 3600) // 60
            s_ = elapsed % 60
            timing.metric("Durée", f"{h_:02d}:{m_:02d}:{s_:02d}")

            time.sleep(0.03)

    else:
        viewer.info("Cliquez sur Démarrer pour lancer la surveillance.")

if __name__ == "__main__":
    main()
