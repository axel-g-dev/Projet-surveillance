import cv2
import numpy as np


# ===============================================================
# MODULE 1 : Initialisation de la caméra
# ===============================================================
def init_camera(cam_index=1):
    """
    Initialise la caméra sur macOS avec AVFoundation.
    """
    cap = cv2.VideoCapture(cam_index, cv2.CAP_AVFOUNDATION)

    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la caméra {cam_index}")

    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Caméra ouverte : {width}x{height}")
    return cap, width, height


# ===============================================================
# MODULE 2 : Prétraitement
# ===============================================================
def preprocess_frame(frame):
    """
    Convertit l'image en niveaux de gris et applique un flou pour réduire le bruit.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    return blur


# ===============================================================
# MODULE 3 : Détection de mouvement (sensibilité normale)
# ===============================================================
def detect_motion(f1, f2, threshold_value=30, min_area=1000):
    """
    Détection de mouvement avec sensibilité normale.
    - threshold_value ≈ 45
    - min_area ≈ 1500
    """
    diff = cv2.absdiff(f1, f2)
    _, thresh = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(c) >= min_area]

    return contours


# ===============================================================
# MODULE 4 : Dessin
# ===============================================================
def draw_motion(frame, contours):
    """
    Dessine les zones de mouvement détectées.
    """
    if contours:
        cv2.putText(frame, "MOUVEMENT DETECTE", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return frame


# ===============================================================
# MODULE 5 : Surveillance avec start/stop via touche ENTRÉE
# ===============================================================
def run_surveillance(cam_index=0):
    cap, width, height = init_camera(cam_index)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter("surveillance.mp4", fourcc, 5.0, (width, height))

    running = False  # Start = pause
    frame1 = frame2 = None

    print("\n🔵 Appuie sur ENTRÉE pour démarrer / arrêter la surveillance")
    print("🔴 Appuie sur ESC pour quitter\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Correction image miroir (Mac)
        frame = cv2.flip(frame, 1)

        display = frame.copy()

        if running:
            if frame1 is None:
                frame1 = frame
                continue

            frame2 = frame

            # Prétraitement
            f1 = preprocess_frame(frame1)
            f2 = preprocess_frame(frame2)

            # Détection (sensibilité normale)
            contours = detect_motion(f1, f2)

            # Dessin
            display = draw_motion(display, contours)

            # Enregistrement vidéo
            out.write(display)

            frame1 = frame2

        else:
            cv2.putText(display, "PAUSE - Appuyez sur ENTREE",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        (255, 255, 0), 2)

        cv2.imshow("Surveillance", display)

        key = cv2.waitKey(20)

        if key == 13:  # touche Entrée
            running = not running
            frame1 = None
            print("▶ Surveillance ACTIVE" if running else "⏸ Surveillance EN PAUSE")

        if key == 27:  # touche ESC
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()


# Lancement du programme
if __name__ == "__main__":
    run_surveillance()
