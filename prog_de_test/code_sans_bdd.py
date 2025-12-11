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
SAVE_FOLDER = "/Volumes/recordings"
THRESHOLD_VALUE = 30
MIN_AREA = 1000
BLUR_KERNEL = (11, 11)
CAM_INDEX = 1
MIN_TIME_BETWEEN_PHOTOS = 5

# ===============================================================
# CONFIGURATION DE LA PAGE
# ===============================================================
st.set_page_config(
    page_title="Surveillance",
    page_icon="⚫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================================================
# STYLES CSS MINIMALISTES STYLE APPLE
# ===============================================================
st.markdown("""
    <style>
    /* Style global minimaliste */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Cache le header Streamlit par défaut */
    header {visibility: hidden;}
    
    /* Video frame style Apple */
    .stImage {
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid #e5e5e7;
    }
    
    /* Sidebar minimaliste */
    [data-testid="stSidebar"] {
        background-color: #fbfbfd;
        border-right: 1px solid #e5e5e7;
    }
    
    [data-testid="stSidebar"] h2 {
        font-weight: 600;
        font-size: 1.3rem;
        color: #1d1d1f;
        margin-bottom: 1.5rem;
    }
    
    [data-testid="stSidebar"] h3 {
        font-weight: 500;
        font-size: 0.9rem;
        color: #6e6e73;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    
    /* Boutons style Apple */
    .stButton button {
        background-color: #0071e3;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 500;
        padding: 0.6rem 1.2rem;
        font-size: 0.95rem;
        transition: all 0.2s ease;
    }
    
    .stButton button:hover {
        background-color: #0077ed;
        transform: scale(1.02);
    }
    
    .stButton button:active {
        transform: scale(0.98);
    }
    
    /* Bouton secondaire */
    .stButton button[kind="secondary"] {
        background-color: transparent;
        color: #0071e3;
        border: 1px solid #0071e3;
    }
    
    .stButton button[kind="secondary"]:hover {
        background-color: #f5f5f7;
    }
    
    /* Metrics style Apple */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
        color: #1d1d1f;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #6e6e73;
        font-weight: 400;
    }
    
    /* Separateurs invisibles */
    hr {
        border: none;
        height: 1px;
        background-color: #e5e5e7;
        margin: 2rem 0;
    }
    
    /* Input fields */
    .stTextInput input {
        border-radius: 8px;
        border: 1px solid #d2d2d7;
        background-color: #f5f5f7;
        color: #1d1d1f;
        font-size: 0.9rem;
    }
    
    /* Info messages */
    .stInfo {
        background-color: #f5f5f7;
        border-left: 3px solid #0071e3;
        border-radius: 8px;
        color: #1d1d1f;
    }
    
    /* Zone principale */
    .main .block-container {
        padding: 2rem 3rem;
        max-width: 100%;
    }
    
    /* Status indicator */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-active {
        background-color: #30d158;
        box-shadow: 0 0 8px rgba(48, 209, 88, 0.5);
    }
    
    .status-inactive {
        background-color: #ff3b30;
    }
    </style>
""", unsafe_allow_html=True)

# ===============================================================
# CLASSE PRINCIPALE : GESTIONNAIRE DE SURVEILLANCE
# ===============================================================
class SurveillanceManager:
    """
    Gère la caméra, la détection de mouvement et l'enregistrement.
    Architecture modulaire pour faciliter le débogage.
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
        
        if DEBUG:
            print(f"[INIT] SurveillanceManager cree")
            print(f"[INIT] Dossier: {self.save_folder}")
    
    def _ensure_save_folder(self):
        """Crée le dossier de sauvegarde s'il n'existe pas."""
        if not os.path.exists(self.save_folder):
            os.makedirs(self.save_folder)
            if DEBUG:
                print(f"[FOLDER] Dossier cree: {self.save_folder}")
        else:
            if DEBUG:
                print(f"[FOLDER] Dossier existant: {self.save_folder}")
    
    def init_camera(self):
        """
        Initialise la caméra et capture les deux premières frames.
        Retourne True si succès, False sinon.
        """
        try:
            if DEBUG:
                print(f"[CAMERA] Tentative d'ouverture (index {self.cam_index})...")
            
            self.cap = cv2.VideoCapture(self.cam_index, cv2.CAP_AVFOUNDATION)
            
            if not self.cap.isOpened():
                if DEBUG:
                    print("[CAMERA] ERREUR: Impossible d'ouvrir la camera")
                raise RuntimeError("Impossible d'ouvrir la camera")
            
            ret1, self.frame1 = self.cap.read()
            ret2, self.frame2 = self.cap.read()
            
            if not ret1 or not ret2:
                if DEBUG:
                    print("[CAMERA] ERREUR: Impossible de lire les frames initiales")
                raise RuntimeError("Impossible de lire les premieres images")
            
            if DEBUG:
                width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                print(f"[CAMERA] OK - Resolution: {int(width)}x{int(height)}")
            
            return True
            
        except Exception as e:
            if DEBUG:
                print(f"[CAMERA] EXCEPTION: {e}")
            return False
    
    def release_camera(self):
        """
        Libère les ressources de la caméra.
        Important pour permettre à d'autres applications d'accéder à la caméra.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            if DEBUG:
                print("[CAMERA] Ressources liberees")
    
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
        Algorithme: différence absolue + seuillage + dilatation + contours.
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
            print(f"[MOTION] {len(contours)} zone(s) detectee(s)")
        
        return contours
    
    def save_motion_picture(self, frame):
        """
        Sauvegarde une image si le délai minimum est respecté.
        Evite de sauvegarder trop d'images lors d'un mouvement continu.
        """
        now = time.time()
        
        if now - self.last_capture_time < MIN_TIME_BETWEEN_PHOTOS:
            if DEBUG_MOTION:
                print(f"[SAVE] Delai non respecte ({now - self.last_capture_time:.1f}s)")
            return False
        
        self.last_capture_time = now
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = os.path.join(self.save_folder, f"mouvement_{timestamp}.jpg")
        
        cv2.imwrite(filename, frame)
        self.total_saved += 1
        
        if DEBUG:
            print(f"[SAVE] Image sauvegardee: {filename}")
        
        return True
    
    def draw_contours(self, frame, contours):
        """
        Dessine des rectangles autour des zones de mouvement.
        Style minimaliste avec bordure fine.
        """
        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            # Bordure verte fine style Apple
            cv2.rectangle(frame, (x, y), (x + w, y + h), (48, 209, 88), 2)
        
        # Indicateur discret en haut à gauche si mouvement
        if contours:
            cv2.circle(frame, (20, 20), 8, (48, 209, 88), -1)
        
        return frame
    
    def process_frame(self):
        """
        Pipeline complet de traitement d'une frame:
        1. Prétraitement (conversion + flou)
        2. Détection de mouvement
        3. Dessin des contours
        4. Sauvegarde conditionnelle
        5. Capture frame suivante
        
        Retourne: (frame_affichable, success, nb_contours)
        """
        if self.cap is None or self.frame1 is None or self.frame2 is None:
            if DEBUG:
                print("[PROCESS] ERREUR: Camera non initialisee")
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
            if DEBUG:
                print("[PROCESS] ERREUR: Impossible de lire la frame suivante")
            return display, False, len(contours)
        
        # Décalage des frames pour le prochain cycle
        self.frame1 = self.frame2
        self.frame2 = next_frame
        
        return display, True, len(contours)
    
    def reset_stats(self):
        """Réinitialise les statistiques."""
        self.total_detections = 0
        self.total_saved = 0
        if DEBUG:
            print("[STATS] Statistiques reinitialisees")


# ===============================================================
# INTERFACE STREAMLIT MINIMALISTE
# ===============================================================
def main():
    """
    Interface utilisateur minimaliste style Apple.
    Focus sur la vidéo avec contrôles essentiels.
    """
    
    # Initialisation du gestionnaire dans session_state
    if "manager" not in st.session_state:
        st.session_state.manager = SurveillanceManager(CAM_INDEX, SAVE_FOLDER)
        st.session_state.camera_initialized = False
        st.session_state.running = False
        st.session_state.start_time = None
        
        if DEBUG:
            print("[APP] Session Streamlit initialisee")
    
    # ===============================================================
    # BARRE LATERALE MINIMALISTE
    # ===============================================================
    with st.sidebar:
        st.markdown("## Surveillance")
        
        # Bouton principal
        if not st.session_state.running:
            if st.button("Demarrer", type="primary", use_container_width=True):
                if not st.session_state.camera_initialized:
                    if DEBUG:
                        print("[APP] Tentative de demarrage...")
                    
                    if st.session_state.manager.init_camera():
                        st.session_state.camera_initialized = True
                        st.session_state.running = True
                        st.session_state.start_time = time.time()
                        st.rerun()
                    else:
                        st.error("Erreur camera")
                else:
                    st.session_state.running = True
                    if st.session_state.start_time is None:
                        st.session_state.start_time = time.time()
                    st.rerun()
        else:
            if st.button("Arreter", use_container_width=True):
                if DEBUG:
                    print("[APP] Arret demande")
                st.session_state.running = False
                st.rerun()
        
        st.markdown("---")
        
        # Statistiques - Placeholders pour mise à jour en temps réel
        st.markdown("### Statistiques")
        
        stats_col1, stats_col2 = st.columns(2)
        with stats_col1:
            detections_placeholder = st.empty()
        with stats_col2:
            captures_placeholder = st.empty()
        
        duree_placeholder = st.empty()
        
        st.markdown("---")
        
        # Parametres
        st.markdown("### Parametres")
        st.text(f"Sensibilite: {THRESHOLD_VALUE}")
        st.text(f"Surface min: {MIN_AREA} px")
        st.text(f"Delai: {MIN_TIME_BETWEEN_PHOTOS}s")
        
        st.markdown("---")
        
        # Dossier
        if st.button("Ouvrir dossier", use_container_width=True):
            os.system(f'open "{SAVE_FOLDER}"')
    
    # ===============================================================
    # ZONE PRINCIPALE - VIDEO OPTIMISEE POUR 1920x1080
    # ===============================================================
    
    # Indicateur de statut minimaliste
    if st.session_state.running:
        st.markdown('<span class="status-indicator status-active"></span> En cours', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-indicator status-inactive"></span> Inactif', unsafe_allow_html=True)
    
    # Zone d'affichage vidéo avec taille optimisée
    frame_placeholder = st.empty()
    
    # Boucle de traitement vidéo
    if st.session_state.running and st.session_state.camera_initialized:
        while st.session_state.running:
            display, success, nb_contours = st.session_state.manager.process_frame()
            
            if not success or display is None:
                if DEBUG:
                    print("[APP] Erreur de lecture du flux")
                st.error("Erreur flux video")
                st.session_state.running = False
                break
            
            # Redimensionnement de la frame pour s'adapter à l'écran 1920x1080
            # Taille optimale: largeur max 1200px, hauteur max 675px (ratio 16:9)
            height, width = display.shape[:2]
            max_width = 1200
            max_height = 675
            
            # Calcul du ratio de redimensionnement
            ratio = min(max_width / width, max_height / height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            resized_display = cv2.resize(display, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
            
            # Affichage de la frame redimensionnée
            frame_placeholder.image(resized_display, channels="BGR", use_container_width=False)
            
            # Mise à jour des statistiques en temps réel
            detections_placeholder.metric("Detections", st.session_state.manager.total_detections)
            captures_placeholder.metric("Captures", st.session_state.manager.total_saved)
            
            if st.session_state.start_time:
                elapsed = int(time.time() - st.session_state.start_time)
                hours = elapsed // 3600
                minutes = (elapsed % 3600) // 60
                seconds = elapsed % 60
                duree_placeholder.metric("Duree", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Pause optimisée
            time.sleep(0.03)
    
    else:
        # Message d'accueil minimaliste
        frame_placeholder.info("Cliquez sur Demarrer pour lancer la surveillance")
        
        # Affichage des stats même quand arrêté
        detections_placeholder.metric("Detections", st.session_state.manager.total_detections)
        captures_placeholder.metric("Captures", st.session_state.manager.total_saved)
        duree_placeholder.metric("Duree", "00:00:00")


# ===============================================================
# POINT D'ENTREE
# ===============================================================
if __name__ == "__main__":
    if DEBUG:
        print("=" * 60)
        print("DEMARRAGE APPLICATION SURVEILLANCE")
        print("=" * 60)
    main()