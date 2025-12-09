# PROJET : SURVEILLANCE ET CAPTURE PHOTO AUTOMATISÉE

## SOMMAIRE
1. Objectif du script
2. Architecture et Configuration
3. Fonctionnement de la sensibilité
4. Système de temporisation
5. Prérequis système
6. Utilisation et Démarrage
7. Rappel de la mise en place d'environnement virtuel

---

## 1. Objectif du script
Ce projet assure une vidéosurveillance en temps réel via la webcam d'un Mac.
Les fonctionnalités principales sont :
- Analyse du flux vidéo image par image.
- Détection de mouvement par différence de pixels (comparaison de frames).
- Prise de photo automatique (.jpg) lors d'une détection validée.
- Enregistrement des captures dans un dossier horodaté.

---

## 2. Architecture et Configuration

Le projet est structuré autour du script principal `code.py`.

### Chemins Absolus
Les chemins suivants sont configurés en dur dans le script pour l'environnement de production :

| Élément | Chemin configuré | Description |
| :--- | :--- | :--- |
| **Script principal** | `/Users/axel/Desktop/surveillance_camera/code.py` | Le code source Python. |
| **Dossier de sauvegarde** | `/Users/axel/Desktop/surveillance_camera/enregistrement` | Lieu de stockage des photos. |

### Paramètres Globaux
| Variable | Valeur | Description |
| :--- | :--- | :--- |
| **CAM_INDEX** | `0` | Index de la caméra (0 pour iPhone et 1 pour webcam interne). |
| **DEBUG** | `True` | Activation des logs dans la console. |

---

## 3. Fonctionnement de la sensibilité

La détection repose sur deux paramètres techniques modifiables dans le script pour filtrer les faux positifs.

### A. Seuil de différence (`THRESHOLD_VALUE`)
Définit la sensibilité au changement de lumière d'un pixel entre deux images consécutives.

| Valeur | Sensibilité | Cas d'usage |
| :--- | :--- | :--- |
| **10 - 20** | Très haute | Détecte les micro-mouvements et le bruit numérique. |
| **30** | **Normale** | **Configuration actuelle. Idéal pour intérieur.** |
| **50+** | Faible | Nécessite un mouvement franc et contrasté. |

### B. Surface minimale (`MIN_AREA`)
Définit la taille minimale (en pixels) de la zone en mouvement (le contour) pour déclencher une capture.

| Valeur | Cible type | Effet |
| :--- | :--- | :--- |
| **< 500** | Insecte / Main | Très sensible aux petits objets. |
| **1000** | **Objet / Visage** | **Configuration actuelle.** |
| **4000+** | Corps entier | Ignore les animaux de compagnie ou objets déplacés. |

---

## 4. Système de temporisation

Un mécanisme de délai (Timer) est implémenté pour éviter la saturation du stockage.

- **Variable :** `MIN_TIME_BETWEEN_PHOTOS`
- **Réglage actuel :** `5` secondes.
- **Logique :** Si un mouvement est détecté, le script vérifie l'heure de la dernière capture. Si moins de 5 secondes se sont écoulées, l'alerte est visuelle (écran) mais aucune image n'est sauvegardée sur le disque.

---

## 5. Prérequis système

- **Langage :** Python 3.9.6
- **OS :** macOS (Le script utilise le backend `cv2.CAP_AVFOUNDATION` spécifique aux Mac).
- **Librairies :** OpenCV (`opencv-python`), Numpy.

---

## 6. Utilisation et Démarrage

### Lancement
Ouvrir un terminal et exécuter la commande suivante :

```bash
streamlit run code.py 
```

## 7. Rappel de la mise en place d'environnement virtuel

**Aller dans le dossier du projet**

```bash
cd /Users/axel/Desktop/surveillance_camera/
```

**Créer l'environnement virtuel**

```bash
python3 -m venv venv
```

**Activer l'environnement**

```bash
source venv/bin/activate
```

*(Le terminal affichera `(venv)` au début de la ligne)*

**Installer les dépendances**

```bash
pip install opencv-python numpy
```

**Désactiver (quand fini)**

```bash
deactivate
```
