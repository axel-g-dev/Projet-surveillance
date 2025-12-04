import cv2
import numpy as np
import os
import time


# ===============================================================
# CONFIGURATION DU PROJET
# ===============================================================
DEBUG = True                  # Debug global (logs)
DEBUG_MOTION = False          # Logs spécifiques au mouvement
SAVE_FOLDER = "/Users/axel/Desktop/surveillance_camera/enregistrement"
THRESHOLD_VALUE = 30          # Sensibilité normale
MIN_AREA = 1000               # Surface minimale détectée
BLUR_KERNEL = (11, 11)        # Flou anti-bruit
CAM_INDEX = 0                # Webcam interne Mac

# TIMER : délai minimum entre deux photos
MIN_TIME_BETWEEN_PHOTOS = 5   # seconde
last_capture_time = 0         # timestamp de la dernière capture


# ===============================================================
# MODULE 1 : Initialisation
# ===============================================================
def init_camera(cam_index=1):
    """
    Initialise la caméra macOS (backend AVFoundation).
    """
    cap = cv2.VideoCapture(cam_index, cv2.CAP_AVFOUNDATION)

    if not cap.isOpened():
        raise RuntimeError("Impossible d'ouvrir la caméra.")

    if DEBUG:
        print("Camera initialisée avec succès.")
        print(f"Resolution: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)} x {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")

    return cap


def ensure_save_folder(path):
    """
    Vérifie que le dossier d'enregistrement existe.
    """
    if not os.path.exists(path):
        os.makedirs(path)
        if DEBUG:
            print(f"Dossier créé : {path}")
    else:
        if DEBUG:
            print(f"Dossier existant : {path}")


# ===============================================================
# MODULE 2 : Prétraitement
# ===============================================================
def preprocess_frame(frame):
    """
    Conversion en niveaux de gris + flou pour réduire le bruit.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
    return blur


# ===============================================================
# MODULE 3 : Détection de mouvement
# ===============================================================
def detect_motion(frameA, frameB, threshold_value, min_area):
    """
    Compare deux images consécutives pour détecter un mouvement.
    """
    diff = cv2.absdiff(frameA, frameB)
    _, thresh = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= min_area]

    if DEBUG_MOTION and contours:
        print(f"Contours détectés: {len(contours)}")

    return contours


# ===============================================================
# MODULE 4 : Sauvegarde des photos
# ===============================================================
def save_motion_picture(frame):
    """
    Sauvegarde une image dans le dossier ~/enregistrement/
    en respectant un délai minimum entre deux photos.
    """
    global last_capture_time
    now = time.time()

    # Timer : attendre au moins MIN_TIME_BETWEEN_PHOTOS
    if now - last_capture_time < MIN_TIME_BETWEEN_PHOTOS:
        return  # trop tôt → on ne sauvegarde pas

    last_capture_time = now

    timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")
    filename = os.path.join(SAVE_FOLDER, f"mouvement_{timestamp}.jpg")
    cv2.imwrite(filename, frame)

    if DEBUG:
        print(f"Mouvement détecté, photo sauvegardée : {filename}")


# ===============================================================
# MODULE 5 : Dessin des zones détectées
# ===============================================================
def draw_contours(frame, contours):
    """
    Dessine des rectangles autour des zones de mouvement.
    """
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    if contours:
        cv2.putText(frame, "MOUVEMENT", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    return frame


# ===============================================================
# MODULE 6 : Surveillance principale
# ===============================================================
def run_surveillance():
    """
    Surveillance active dès le démarrage.
    ESC permet d'arrêter le programme.
    """
    ensure_save_folder(SAVE_FOLDER)
    cap = init_camera(CAM_INDEX)

    ret, frame1 = cap.read()
    ret2, frame2 = cap.read()

    if not ret or not ret2:
        print("Erreur : impossible de lire les premières images.")
        cap.release()
        return

    if DEBUG:
        print("Surveillance active. Pression de la touche ESC pour arrêter.")

    while True:
        # Affichage sans inversion
        display = frame1.copy()

        # Prétraitements
        f1 = preprocess_frame(frame1)
        f2 = preprocess_frame(frame2)

        # Détection
        contours = detect_motion(f1, f2, THRESHOLD_VALUE, MIN_AREA)

        # Dessin
        display = draw_contours(display, contours)

        # Sauvegarde d'une image si mouvement (avec timer)
        if contours:
            save_motion_picture(frame1)

        # Affichage du flux vidéo
        cv2.imshow("Surveillance", display)

        # Mise à jour des frames
        frame1 = frame2
        ret, frame2 = cap.read()
        if not ret:
            break

        # Quitter avec ESC
        key = cv2.waitKey(20)
        if key == 27:
            if DEBUG:
                print("Arrêt demandé.")
            break

    cap.release()
    cv2.destroyAllWindows()


# ===============================================================
# Lancement
# ===============================================================
if __name__ == "__main__":
    run_surveillance()
