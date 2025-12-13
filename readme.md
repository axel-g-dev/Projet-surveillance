# Surveillance et Capture Photo Automatisée

## Sommaire

1. Objectif du projet
2. Matériel et environnement
3. Architecture du système
4. Classes et structure du code
5. Paramètres de détection
6. Base de données
7. Installation et configuration
8. Utilisation

---

## 1. Objectif du projet

Système de vidéosurveillance temps réel pour PC portable intégré dans une architecture de surveillance distribuée. Le système capture automatiquement des images lors de détections de mouvement et synchronise les données avec un serveur Raspberry Pi 5 centralisé.

**Contexte:** Mini-Projet 1 - Tâche 1 (Vidéosurveillance)

**Fonctionnalités principales:**
- Analyse du flux vidéo par différence de frames
- Détection de mouvement par seuillage et contours
- Capture automatique avec horodatage
- Stockage sur dossier partagé SMB/NFS
- Enregistrement des métadonnées en base MySQL distante
- Interface de monitoring Streamlit

---

## 2. Matériel et environnement

**Client (PC Portable):**
- MacBook Pro
- Python 3.13.5
- macOS (backend AVFoundation pour OpenCV)

**Serveur:**
- Raspberry Pi 5
- 4 Go RAM
- 32 Go stockage
- Adresse IP: 192.168.4.1
- Dossier partagé monté sur `/Volumes/recordings`

**Caméras disponibles:**
- Index 0: iPhone (via Continuity Camera)
- Index 1: Webcam interne MacBook (configuration actuelle)

---

## 3. Architecture du système

### Flux de données

```
[PC Portable - Webcam]
    |
    |--> Détection mouvement (OpenCV)
    |--> Capture image sur dossier partagé
    |--> Envoi métadonnées vers serveur
            |
            v
    [Raspberry Pi 5 - 192.168.4.1]
            |
            |--> Stockage image: /var/www/recordings/
            |--> Base MySQL: presence.enregistrement
```

### Structure des chemins

| Élément | Chemin Mac | Chemin Raspberry | Description |
|---------|------------|------------------|-------------|
| Dossier partagé | `/Volumes/recordings/` | `/var/www/recordings/` | Point de montage SMB/NFS |
| Format fichier | `mouvement_YYYYMMDD-HHMMSS.jpg` | Identique | Horodatage précis |
| Base distante | - | `192.168.4.1:3306` | MySQL sur Raspberry |

### Authentification dossier partagé

**Utilisateur:** `axel`  
**Mot de passe:** `fi27^#COi5mlK##ZB3T4`

Le dossier `/Volumes/recordings` doit être monté avec ces identifiants avant le démarrage du script. Seul cet utilisateur dispose des droits d'écriture sur le partage réseau.

---

## 4. Base de données

### Schéma MySQL

```sql
DROP TABLE IF EXISTS enregistrement;

CREATE TABLE enregistrement (
    id_log INT(11) NOT NULL AUTO_INCREMENT,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    type VARCHAR(50) DEFAULT NULL,
    file_path VARCHAR(255) DEFAULT NULL,
    PRIMARY KEY (id_log)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

### Configuration de connexion

```python
DB_CONFIG = {
    'host': '192.168.4.1',
    'port': 3306,
    'user': 'presence',
    'password': '*9RSSFr5bD0WO64qurDY',
    'database': 'presence'
}
```

### Exemple d'enregistrement

```
id_log: 1452
timestamp: 2025-12-02 14:32:04
type: mouvement
file_path: /Volumes/recordings/mouvement_20251202-143204.jpg
```

**Particularités:**
- `timestamp`: Mise à jour automatique à chaque modification (`ON UPDATE CURRENT_TIMESTAMP`)
- `type`: Toujours "mouvement" pour les détections webcam
- `file_path`: Chemin absolu tel que vu depuis le Mac
- Moteur InnoDB pour la fiabilité transactionnelle
- Charset utf8mb4 pour compatibilité internationale

---

## 5. Classes et structure du code

### A. DatabaseManager

Gère la connexion et les opérations avec la base MySQL distante sur le Raspberry Pi.

**Méthodes:**

**`connect()`**
- Établit la connexion TCP vers 192.168.4.1:3306
- Vérifie l'état de connexion avant tentative
- Retourne `True` si connexion active ou établie avec succès

**`insert(event_type, path)`**
- Prépare une requête paramétrée pour éviter l'injection SQL
- Insère un enregistrement avec `type` et `file_path`
- Exécute `commit()` pour validation transactionnelle
- Retourne `True` en cas de succès

**`close()`**
- Ferme proprement la connexion MySQL
- Libère les ressources réseau

**Particularités:**
- Vérification systématique de `is_connected()` avant chaque opération
- Gestion des erreurs avec logs console (si DEBUG activé)
- Pas de pool de connexions (une seule connexion persistante pour l'application)

### B. SurveillanceManager

Classe principale gérant le cycle complet de surveillance et de capture.

**Attributs:**
- `cap`: Objet `cv2.VideoCapture` pour l'acquisition vidéo
- `frame_a`, `frame_b`: Buffer circulaire pour comparaison temporelle
- `last_capture`: Timestamp Unix de la dernière sauvegarde
- `total_detections`: Compteur de tous les mouvements détectés
- `total_saved`: Compteur des images effectivement sauvegardées
- `db`: Instance de `DatabaseManager`

**Méthodes principales:**

**`init_camera()`**
- Ouvre la caméra avec `cv2.VideoCapture(CAM_INDEX)`
- `CAM_INDEX = 1` pour la webcam interne MacBook
- Lit 2 frames successives pour initialiser le buffer de comparaison
- Affiche la résolution du flux (via `CAP_PROP_FRAME_WIDTH/HEIGHT`)
- Retourne `False` si échec d'ouverture ou de lecture

**`preprocess(frame)`**
- Conversion BGR vers niveaux de gris: réduit 3 canaux couleur à 1 canal intensité
- Flou gaussien 11x11: élimine le bruit haute fréquence de la webcam
- Retourne une matrice numpy uint8 (0-255) exploitable pour la différence

**`detect_motion(frame_a, frame_b)`**
- `cv2.absdiff()`: Calcule la valeur absolue de la différence pixel par pixel
- `cv2.threshold()`: Binarise à `THRESHOLD_VALUE = 30` (noir/blanc strict)
- `cv2.dilate()`: Opération morphologique pour combler les discontinuités (2 itérations)
- `cv2.findContours()`: Extrait les contours fermés des zones blanches
- Filtre les contours dont l'aire est inférieure à `MIN_AREA = 1000` pixels
- Retourne une liste de contours valides

**`save_picture(frame)`**
- Vérifie que `MIN_TIME_BETWEEN_PHOTOS = 5` secondes se sont écoulées
- Génère un nom de fichier: `mouvement_YYYYMMDD-HHMMSS.jpg`
- Construit le chemin complet: `/Volumes/recordings/mouvement_...jpg`
- Écrit l'image avec `cv2.imwrite()` (format JPEG, qualité par défaut 95%)
- Appelle `db.insert("mouvement", path)` pour enregistrer dans MySQL
- Retourne `False` si délai non respecté, `True` si sauvegarde effectuée

**`process()`**
- Prétraite les 2 frames du buffer
- Détecte les contours en mouvement
- Incrémente `total_detections` si au moins un contour valide
- Sauvegarde l'image et enregistre en BDD
- Dessine des rectangles verts autour des contours sur une copie de `frame_a`
- Lit une nouvelle frame pour avancer le buffer circulaire
- Retourne: `(image_annotée, statut_ok, nombre_contours)`

**`release()`**
- Libère la ressource caméra avec `cap.release()`
- Ferme la connexion base de données
- Appelé lors de l'arrêt de la surveillance

---

## 6. Paramètres de détection

### A. Seuil de différence (THRESHOLD_VALUE = 30)

Définit la sensibilité au changement de luminosité entre pixels consécutifs.

| Valeur | Sensibilité | Justification |
|--------|-------------|---------------|
| 10-20 | Très haute | Détecte le bruit numérique du capteur, faux positifs constants |
| **30** | **Normale** | **Équilibre optimal pour environnement intérieur avec éclairage stable** |
| 50+ | Faible | Nécessite contraste élevé, risque de manquer mouvements lents |

**Choix actuel (30):** Sur une échelle de différence 0-255, un seuil à 30 filtre les variations d'ombres et de compression JPEG tout en capturant les déplacements humains. Adapté à un bureau avec lampes LED ou lumière naturelle indirecte.

### B. Surface minimale (MIN_AREA = 1000)

Taille minimale du contour en pixels² pour valider une détection.

| Valeur | Objet type | Impact |
|--------|------------|--------|
| < 500 | Main, insecte | Déclenchements parasites fréquents |
| **1000** | **Visage, torse** | **Cible principale: présence humaine à distance moyenne** |
| 4000+ | Corps entier | Risque de manquer intrusions partielles dans le champ |

**Choix actuel (1000):** 
- Résolution typique webcam MacBook: 1280x720 = 921600 pixels totaux
- 1000 pixels représentent environ 0.1% de l'image
- Correspond à un visage de 30x30 pixels minimum
- À 2-3 mètres de la caméra, filtre les mouvements d'objets < 15cm

### C. Noyau de flou (BLUR_KERNEL = 11x11)

**Justification technique:**
- Matrice gaussienne 11x11 applique un filtre passe-bas
- Supprime les artefacts de compression H.264 du flux webcam
- Valeur impaire obligatoire (centre du noyau doit être défini)
- 11x11 optimal: 5x5 insuffisant pour webcam, 21x21 dégrade les contours humains

### D. Délai anti-rafale (MIN_TIME_BETWEEN_PHOTOS = 5)

**Justification:**
- Un mouvement continu génère des détections à chaque frame (30 fps = 30 détections/seconde)
- Sans filtrage: 1800 images quasi-identiques par minute
- 5 secondes permettent de capturer 12 phases distinctes d'un déplacement d'une minute
- Évite la saturation du stockage 32 Go du Raspberry Pi
- Réduit la charge d'écriture sur le dossier partagé SMB

---

## 7. Librairies utilisées

### streamlit (2.x)

**Justification:**
- Framework web Python pur, sans HTML/CSS/JavaScript requis
- Mise en place rapide d'interfaces de monitoring avec widgets natifs
- Rechargement à chaud du code pour le développement itératif
- Gestion automatique de l'état entre rechargements (`st.session_state`)
- Affichage natif des images numpy sans conversion manuelle
- Documentation exhaustive et communauté active

**Usage dans le projet:**
- Boutons de contrôle Start/Stop
- Affichage du flux vidéo en temps réel
- Métriques statistiques dynamiques
- Configuration de la mise en page (sidebar, colonnes)

### opencv-python (4.x)

**Justification:**
- Bibliothèque open source de référence pour la vision par ordinateur
- Support natif macOS via backend AVFoundation (pas de dépendance externe)
- Documentation très complète avec exemples pour chaque fonction
- Performance optimisée en C++ avec bindings Python
- Écosystème de tutoriels massif (Stack Overflow, GitHub, blogs)
- Fonctions de traitement d'image de bas niveau accessibles

**Usage dans le projet:**
- `VideoCapture()`: Acquisition flux webcam
- `cvtColor()`: Conversion colorimétrique
- `GaussianBlur()`: Prétraitement anti-bruit
- `absdiff()`, `threshold()`, `dilate()`: Pipeline de détection
- `findContours()`: Extraction des zones en mouvement
- `rectangle()`: Annotation visuelle
- `imwrite()`: Sauvegarde JPEG

### numpy (1.x)

**Justification:**
- Manipulation efficace des matrices d'images (tableaux multidimensionnels)
- OpenCV retourne nativement des arrays numpy
- Opérations vectorisées (100x plus rapides que boucles Python natives)
- Calculs mathématiques sur pixels sans conversion de type
- Intégration transparente avec Streamlit et OpenCV

**Usage dans le projet:**
- Représentation interne des frames (height, width, channels)
- Calculs de différence pixel par pixel (opérateur `-` vectorisé)
- Manipulation des masques binaires issus du seuillage

### mysql-connector-python (8.x)

**Justification:**
- Connecteur officiel Oracle pour MySQL
- Implémentation pure Python (pas de dépendance C)
- Support des requêtes paramétrées (protection injection SQL)
- Gestion automatique du pool de connexions
- Compatible avec MariaDB (moteur du Raspberry Pi)

**Usage dans le projet:**
- Connexion TCP vers le serveur MySQL du Raspberry Pi
- Insertion transactionnelle des métadonnées de capture
- Gestion des erreurs réseau et de timeout

---

## 8. Installation et configuration

### A. Montage du dossier partagé

**Via Finder (interface graphique):**
1. Finder > Aller > Se connecter au serveur (Cmd+K)
2. Saisir: `smb://192.168.4.1/recordings`
3. Utilisateur: `axel`
4. Mot de passe: `fi27^#COi5mlK##ZB3T4`
5. Le dossier apparaît dans `/Volumes/recordings`

**Via terminal (persistant):**
```bash
mkdir -p /Volumes/recordings
mount -t smbfs //axel:fi27^#COi5mlK##ZB3T4@192.168.4.1/recordings /Volumes/recordings
```

**Vérification:**
```bash
ls -la /Volumes/recordings
touch /Volumes/recordings/test.txt && rm /Volumes/recordings/test.txt
```

### B. Création de l'environnement virtuel

```bash
cd /Users/axel/Desktop/surveillance_camera/
python3 -m venv venv
source venv/bin/activate
```

### C. Installation des dépendances

```bash
pip install streamlit opencv-python numpy mysql-connector-python
```

**Versions recommandées:**
- `streamlit>=1.28.0`
- `opencv-python>=4.8.0`
- `numpy>=1.24.0`
- `mysql-connector-python>=8.0.33`

### D. Test de la connexion base de données

```bash
mysql -h 192.168.4.1 -u presence -p
# Mot de passe: *9RSSFr5bD0WO64qurDY
```

```sql
USE presence;
SELECT * FROM enregistrement ORDER BY id_log DESC LIMIT 5;
```

---

## 9. Utilisation

### Démarrage du système

**Prérequis:**
1. Dossier partagé monté sur `/Volumes/recordings`
2. Connexion réseau active vers 192.168.4.1
3. Environnement virtuel activé

**Lancement:**
```bash
cd /Users/axel/Desktop/surveillance_camera/
source venv/bin/activate
streamlit run code.py
```

**Accès interface:**
- URL automatique: `http://localhost:8501`
- Ouverture navigateur automatique

### Interface web

**Barre latérale (Sidebar):**

**Contrôles:**
- Bouton "Démarrer": Initialise `cv2.VideoCapture(1)`, charge le buffer, lance la boucle d'analyse
- Bouton "Arrêter": Appelle `release()`, ferme la caméra et la connexion MySQL
- Bouton "Ouvrir dossier": Exécute `open "/Volumes/recordings"` (Finder)

**Statistiques temps réel:**
- Détections: Incrémenté à chaque frame contenant un contour valide
- Captures: Incrémenté uniquement si sauvegarde effectuée (délai respecté)
- Durée: Format HH:MM:SS depuis `session_state.start_time`

**Zone principale:**

**Indicateur d'état:**
- Badge vert "En cours" si `session_state.running == True`
- Badge gris "Inactif" sinon

**Affichage vidéo:**
- Flux en direct avec rectangles verts sur zones en mouvement
- Redimensionnement automatique (max 1200x675 pixels)
- Rafraîchissement: 33ms (`time.sleep(0.03)` = ~30 fps)

### Arrêt propre

**Via interface:**
- Clic sur "Arrêter" dans la sidebar

**Via terminal:**
- `Ctrl+C` dans le terminal exécutant Streamlit

**Désactivation environnement:**
```bash
deactivate
```

---

## 10. Configuration DEBUG

**Variables de débogage dans le code:**

```python
DEBUG = True          # Logs connexion DB, sauvegardes, résolution caméra
DEBUG_MOTION = False  # Logs verbeux de chaque détection (désactivé par défaut)
```

**Sortie console avec DEBUG=True:**
```
[CAM] Opening camera...
[CAM] OK. Resolution: 1280.0 x 720.0
[DB] Connexion OK.
[SAVE] Photo: /Volumes/recordings/mouvement_20251213-142317.jpg
[DB] Ajout enregistrement OK → /Volumes/recordings/mouvement_20251213-142317.jpg
```

Les messages apparaissent dans le terminal exécutant Streamlit, pas dans l'interface web.

---

## 11. Structure des fichiers générés

**Format de nom:**
```
mouvement_YYYYMMDD-HHMMSS.jpg
```

**Exemples:**
```
mouvement_20251213-093042.jpg  → 13 décembre 2025, 09h30m42s
mouvement_20251213-152318.jpg  → 13 décembre 2025, 15h23m18s
```

**Propriétés JPEG:**
- Qualité: 95% (défaut OpenCV)
- Résolution: Identique au flux source (1280x720 pour webcam MacBook)
- Taille fichier: 150-300 Ko selon complexité de la scène