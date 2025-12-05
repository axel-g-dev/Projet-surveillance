import streamlit as st
import cv2
import numpy as np
import os
import time

# ===============================================================
# CONFIGURATION GLOBALE
# ===============================================================
DEBUG = True
DEBUG_MOTION = False
SAVE_FOLDER = "/Users/axel/Desktop/surveillance_camera/enregistrement"
THRESHOLD_VALUE = 30
MIN_AREA = 1000
BLUR_KERNEL = (11, 11)
CAM_INDEX = 1
MIN_TIME_BETWEEN_PHOTOS = 5

# ===============================================================
# CONFIGURATION DE LA PAGE
# ===============================================================
st.set_page_config(
    page_title="Surveillance Video",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================================================
# STYLES CSS PERSONNALISES
# ===============================================================
st.markdown("""
    <style>
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        text-align: center;
        margin-top: 0.5rem;
        font-size: 1.1rem;
    }
    
    /* Video frame */
    .stImage {
        border-radius: 10px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        border: 3px solid #667eea;
    }
    
    /* Boutons */
    .stButton button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 700;
    }
    
    /* Separateurs */
    hr {
        margin: 1.5rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(to right, transparent, #667eea, transparent);
    }
    
    /* Info boxes */
    .info-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ===============================================================
# CLASSE PRINCIPALE : GESTIONNAIRE DE SURVEILLANCE
# ===============================================================
class SurveillanceManager:
    """
    Gère la caméra, la détection de mouvement et l'enregistrement.
    """
    
    def __init__(self, cam_index=1, save_folder=SAVE_FOLDER):
        self.cam_index = cam_index
        self.save_folder = save_folder
        self.cap = None
        self.frame1 = None
        self.frame2 = None
        self.last_capture_time = 0
        self.total_detections = 0
        self.total_saved = 0
        
        self._ensure_save_folder()
    
    def _ensure_save_folder(self):
        """Crée le dossier de sauvegarde s'il n'existe pas."""
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)
            if DEBUG:
                print(f"Dossier cree : {self.save_folder}")
    
    def init_camera(self):
        """Initialise la caméra et capture les deux premières frames."""
        try:
            self.cap = cv2.VideoCapture(self.cam_index, cv2.CAP_AVFOUNDATION)
            
            if not self.cap.isOpened():
                raise RuntimeError("Impossible d'ouvrir la camera")
            
            ret1, self.frame1 = self.cap.read()
            ret2, self.frame2 = self.cap.read()
            
            if not ret1 or not ret2:
                raise RuntimeError("Impossible de lire les premieres images")
            
            if DEBUG:
                width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                print(f"Camera initialisee - Resolution: {width}x{height}")
            
            return True
            
        except Exception as e:
            print(f"Erreur initialisation camera: {e}")
            return False
    
    def release_camera(self):
        """Libère les ressources de la caméra."""
        if self.cap is not None:
            self.cap.release()
            if DEBUG:
                print("Camera liberee")
    
    def preprocess_frame(self, frame):
        """
        Convertit en niveaux de gris et applique un flou gaussien.
        Réduit le bruit pour une meilleure détection.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
        return blur
    
    def detect_motion(self, frame1, frame2):
        """
        Compare deux frames consécutives pour détecter un mouvement.
        Retourne les contours des zones en mouvement.
        """
        # Calcul de la différence absolue entre les deux frames
        diff = cv2.absdiff(frame1, frame2)
        
        # Seuillage binaire
        _, thresh = cv2.threshold(diff, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
        
        # Dilatation pour combler les trous
        dilated = cv2.dilate(thresh, None, iterations=2)
        
        # Détection des contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filtrage par surface minimale
        contours = [c for c in contours if cv2.contourArea(c) >= MIN_AREA]
        
        if DEBUG_MOTION and contours:
            print(f"Contours detectes: {len(contours)}")
        
        return contours
    
    def save_motion_picture(self, frame):
        """
        Sauvegarde une image si le délai minimum est respecté.
        """
        now = time.time()
        
        if now - self.last_capture_time < MIN_TIME_BETWEEN_PHOTOS:
            return False
        
        self.last_capture_time = now
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.save_folder, f"mouvement_{timestamp}.jpg")
        
        cv2.imwrite(filename, frame)
        self.total_saved += 1
        
        if DEBUG:
            print(f"Photo sauvegardee: {filename}")
        
        return True
    
    def draw_contours(self, frame, contours):
        """
        Dessine des rectangles verts autour des zones de mouvement.
        Ajoute un texte d'alerte si mouvement détecté.
        """
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        if contours:
            cv2.putText(frame, "MOUVEMENT DETECTE", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        
        return frame
    
    def process_frame(self):
        """
        Traite une frame complète:
        1. Prétraitement des deux frames
        2. Détection de mouvement
        3. Dessin des contours
        4. Sauvegarde si mouvement détecté
        5. Capture de la frame suivante
        
        Retourne: (frame_affichable, success, nb_contours)
        """
        if self.cap is None or self.frame1 is None or self.frame2 is None:
            return None, False, 0
        
        # Copie pour affichage
        display = self.frame1.copy()
        
        # Prétraitement
        f1_processed = self.preprocess_frame(self.frame1)
        f2_processed = self.preprocess_frame(self.frame2)
        
        # Détection de mouvement
        contours = self.detect_motion(f1_processed, f2_processed)
        
        if contours:
            self.total_detections += 1
        
        # Dessin des contours
        display = self.draw_contours(display, contours)
        
        # Sauvegarde si mouvement détecté
        if contours:
            self.save_motion_picture(self.frame1)
        
        # Capture de la frame suivante
        ret, next_frame = self.cap.read()
        if not ret:
            return display, False, len(contours)
        
        # Décalage des frames pour le prochain cycle
        self.frame1 = self.frame2
        self.frame2 = next_frame
        
        return display, True, len(contours)


# ===============================================================
# INTERFACE STREAMLIT
# ===============================================================
def main():
    """
    Point d'entrée principal de l'application Streamlit.
    Gère l'interface utilisateur et le flux vidéo.
    """
    
    # Header principal
    st.markdown("""
        <div class="main-header">
            <h1>Systeme de Surveillance Video</h1>
            <p>Detection automatique de mouvement en temps reel</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Initialisation du gestionnaire dans session_state
    if "manager" not in st.session_state:
        st.session_state.manager = SurveillanceManager(CAM_INDEX, SAVE_FOLDER)
        st.session_state.camera_initialized = False
        st.session_state.running = False
        st.session_state.start_time = None
    
    # ===============================================================
    # BARRE LATERALE - CONTROLES ET PARAMETRES
    # ===============================================================
    with st.sidebar:
        st.header("Panneau de Controle")
        st.markdown("---")
        
        # Section Controles
        st.subheader("Controles")
        
        if st.button("Demarrer la surveillance", type="primary", use_container_width=True):
            if not st.session_state.camera_initialized:
                with st.spinner("Initialisation de la camera..."):
                    if st.session_state.manager.init_camera():
                        st.session_state.camera_initialized = True
                        st.session_state.running = True
                        st.session_state.start_time = time.time()
                        st.success("Camera demarree avec succes")
                    else:
                        st.error("Erreur lors de l'initialisation")
            else:
                st.session_state.running = True
                if st.session_state.start_time is None:
                    st.session_state.start_time = time.time()
        
        if st.button("Arreter la surveillance", use_container_width=True):
            st.session_state.running = False
        
        if st.button("Liberer la camera", use_container_width=True):
            st.session_state.manager.release_camera()
            st.session_state.camera_initialized = False
            st.session_state.running = False
            st.session_state.start_time = None
            st.info("Camera liberee")
        
        st.markdown("---")
        
        # Section Statistiques
        st.subheader("Statistiques")
        
        if st.session_state.running and st.session_state.start_time:
            elapsed = int(time.time() - st.session_state.start_time)
            hours = elapsed // 3600
            minutes = (elapsed % 3600) // 60
            seconds = elapsed % 60
            st.metric("Duree surveillance", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            st.metric("Duree surveillance", "00:00:00")
        
        st.metric("Detections totales", st.session_state.manager.total_detections)
        st.metric("Images sauvegardees", st.session_state.manager.total_saved)
        
        st.markdown("---")
        
        # Section Parametres
        st.subheader("Parametres")
        
        st.markdown(f"""
        <div class="info-box">
            <strong>Sensibilite:</strong> {THRESHOLD_VALUE}<br>
            <strong>Surface min:</strong> {MIN_AREA} px<br>
            <strong>Delai capture:</strong> {MIN_TIME_BETWEEN_PHOTOS} sec<br>
            <strong>Camera:</strong> Index {CAM_INDEX}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Section Dossier
        st.subheader("Dossier de sauvegarde")
        st.text_input("Chemin", SAVE_FOLDER, disabled=True)
        
        if st.button("Ouvrir le dossier", use_container_width=True):
            os.system(f'open "{SAVE_FOLDER}"')
    
    # ===============================================================
    # ZONE PRINCIPALE - AFFICHAGE VIDEO
    # ===============================================================
    
    # Statut en temps réel
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.session_state.running:
            st.markdown("### Statut: <span style='color: #00ff00;'>EN COURS</span>", unsafe_allow_html=True)
        else:
            st.markdown("### Statut: <span style='color: #ff0000;'>ARRETE</span>", unsafe_allow_html=True)
    
    with col2:
        if st.session_state.running:
            st.markdown("### Surveillance active - Detection en temps reel")
        else:
            st.markdown("### Cliquez sur 'Demarrer' dans la barre laterale pour commencer")
    
    st.markdown("---")
    
    # Zone d'affichage vidéo (pleine largeur)
    frame_placeholder = st.empty()
    
    # Boucle de traitement vidéo
    if st.session_state.running and st.session_state.camera_initialized:
        while st.session_state.running:
            display, success, nb_contours = st.session_state.manager.process_frame()
            
            if not success or display is None:
                st.error("Erreur lors de la lecture du flux video")
                st.session_state.running = False
                break
            
            # Affichage de la frame en grand format
            frame_placeholder.image(display, channels="BGR", use_container_width=True)
            
            # Petite pause pour éviter une charge CPU excessive
            time.sleep(0.03)
    
    elif not st.session_state.running and st.session_state.camera_initialized:
        # Affichage d'un message quand la surveillance est en pause
        frame_placeholder.info("Surveillance en pause. Cliquez sur 'Demarrer' pour reprendre.")
    
    else:
        # Affichage d'un message quand la caméra n'est pas initialisée
        frame_placeholder.info("Camera non initialisee. Cliquez sur 'Demarrer' dans la barre laterale pour commencer la surveillance.")


# ===============================================================
# POINT D'ENTREE
# ===============================================================
if __name__ == "__main__":
    main()