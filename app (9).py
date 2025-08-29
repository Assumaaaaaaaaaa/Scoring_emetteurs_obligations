import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import re
import os
# Configuration d'accès
PASSWORD = "1512"  # Changez ce mot de passe

# Vérification de l'authentification
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Accès Application")
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("auth_form"):
            password = st.text_input("Mot de passe d'accès:", type="password")
            if st.form_submit_button("🔓 Se connecter"):
                if password == PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Accès refusé")
    st.stop()

# Si authentifié, afficher l'application principale
st.sidebar.write(f"✅ Connecté")
if st.sidebar.button("🚪 Déconnexion"):
    st.session_state.authenticated = False
    st.rerun()
####
# Configuration de la page
st.set_page_config(page_title="Scoring Sectoriel des Émetteurs", layout="wide")
st.title(" Scoring Sectoriel des Émetteurs D'obligations Marocains")

# Dictionnaire des secteurs et émetteurs
SECTEURS_EMETTEURS = {
    "Matériaux de Construction": ["LafargeHolcimMaroc", "CIMENTSDUMAROC"],
    "BTP & Génie Civil": ["TGCC", "JETCONTRACTORS"],
    "Immobilier & Tourisme": ["ADDOHA", "ALOMRANE", "ALLIANCEDARNA", "RDS"],
    "Agroalimentaire": ["COSUMAR"],
    "Distribution & Consommation": ["LABELVIE", "MUTANDISSCA"],
    "Énergie & Utilities": ["TAQAMOROCCO", "AFRIQUIAGAZ"],
    "Finance & Services Financiers": ["DISWAY"],
    "Télécommunications": ["IAM"],
    "Transport & Infrastructures": ["ONCF", "ADM"],
    "Bancaire": ["ATW", "BCP", "BOA", "SGBM", "CDM", "BMCI", "CFG", "CIH", "CAM", "CDG"]
}

# Émetteurs de AL BARID BANK (portefeuille personnalisable)
AL_BARID_BANK_EMETTEURS = [
    "ADDOHA", "ALOMRANE", "ALLIANCEDARNA", "RDS", "COSUMAR",
    "LABELVIE", "MUTANDISSCA", "IAM", "DISWAY", "TAQAMOROCCO",
    "AFRIQUIAGAZ", "ONCF", "ADM", "LafargeHolcimMaroc", 
    "CIMENTSDUMAROC", "TGCC", "JETCONTRACTORS"
]

# Seuils de référence par secteur
SEUILS_SECTORIELS = {
    "default": {
        'ROA': {"danger": 0.03, "alert": 0.05, "satisfactory": 0.08, "excellent": 0.12},
        'ROE': {"danger": 0.05, "alert": 0.08, "satisfactory": 0.12, "excellent": 0.18},
        'Marge_operationnelle': {"danger": 0.08, "alert": 0.12, "satisfactory": 0.18, "excellent": 0.25},
        'CAPEX': {"danger": 0.15, "alert": 0.12, "satisfactory": 0.08, "excellent": 0.05},
        'GEARING': {"danger": 0.60, "alert": 0.45, "satisfactory": 0.30, "excellent": 0.20},
        'Ratio_liquidite': {"danger": 1.0, "alert": 1.2, "satisfactory": 1.5, "excellent": 2.0},
        'Ratio_levier': {"danger": 2.0, "alert": 1.5, "satisfactory": 1.0, "excellent": 0.5},
        'Taux d\'endettement': {"danger": 0.60, "alert": 0.45, "satisfactory": 0.30, "excellent": 0.15}
    },
    "Transport & Infrastructures": {
        'ROA': {"danger": 0.04, "alert": 0.06, "satisfactory": 0.08, "excellent": 0.10},
        'ROE': {"danger": 0.06, "alert": 0.09, "satisfactory": 0.12, "excellent": 0.15},
        'CAPEX': {"danger": 0.08, "alert": 0.12, "satisfactory": 0.15, "excellent": 0.18},
        'GEARING': {"danger": 0.70, "alert": 0.60, "satisfactory": 0.50, "excellent": 0.40}
    },
    "Bancaire": {
        'ROA': {"danger": 0.005, "alert": 0.008, "satisfactory": 0.012, "excellent": 0.018},
        'ROE': {"danger": 0.08, "alert": 0.10, "satisfactory": 0.12, "excellent": 0.15},
        'Ratio_efficience': {"danger": 0.70, "alert": 0.60, "satisfactory": 0.50, "excellent": 0.40},
        'Ratio_leverage': {"danger": 0.15, "alert": 0.12, "satisfactory": 0.10, "excellent": 0.08},
        'Ratio_NPL': {"danger": 0.08, "alert": 0.06, "satisfactory": 0.04, "excellent": 0.02},
        'Ratio_LDR': {"danger": 1.10, "alert": 1.00, "satisfactory": 0.90, "excellent": 0.80}
    }
}

# Initialisation de l'état
if 'df' not in st.session_state:
    st.session_state.df = None
if 'sector_data' not in st.session_state:
    st.session_state.sector_data = None
if 'selected_sector' not in st.session_state:
    st.session_state.selected_sector = None
if 'score_details' not in st.session_state:
    st.session_state.score_details = {}
if 'al_barid_selection' not in st.session_state:
    st.session_state.al_barid_selection = []
if 'banking_data' not in st.session_state:
    st.session_state.banking_data = None

# Fonction pour charger les données
# ... [Le code précédent reste inchangé jusqu'à la fonction load_and_prepare_data] ...

# Fonction pour charger les données

# Fonction pour charger les données (sans calcul automatique des ratios)
def load_and_prepare_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            st.error("Format de fichier non supporté. Veuillez uploader un fichier Excel (.xlsx) ou CSV (.csv)")
            return None
        
        # Vérification des colonnes nécessaires (maintenant seulement les colonnes de base)
        required_columns = ['Emmeteur', 'Resultat_net', 'Total_actif', 'Capitaux_propres', 
                           'Resulta_exploitation', 'Chiffre_affaires', 'DETTEDEFINANCIERS']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Colonnes manquantes dans le fichier: {', '.join(missing_columns)}")
            return None
        
        # Attribution des secteurs
        df['Secteur'] = ''
        for secteur, emetteurs in SECTEURS_EMETTEURS.items():
            for emetteur in emetteurs:
                df.loc[df['Emmeteur'].str.contains(emetteur, case=False), 'Secteur'] = secteur
        
        # NE PAS calculer les ratios automatiquement - on le fera avec un bouton
        st.info("📋 Données chargées avec succès! Cliquez sur 'Calculer les Ratios' pour générer les indicateurs financiers.")
        
        return df
        
    except Exception as e:
        st.error(f"Erreur lors du chargement: {str(e)}")
        return None

# Fonction pour calculer les ratios (appelée par le bouton)
def calculate_ratios(df):
    """Calcule tous les ratios financiers"""
    df_calculated = df.copy()
    
    st.info("📊 Calcul des ratios financiers en cours...")
    
    # 1. Ratios de rentabilité
    df_calculated['ROA(%)'] = (df_calculated['Resultat_net'] / df_calculated['Total_actif'])*100
    df_calculated['ROE(%)'] = (df_calculated['Resultat_net'] / df_calculated['Capitaux_propres'])*100
    
    # 2. Ratios de marge
    df_calculated['Marge_operationnelle(%)'] = (df_calculated['Resulta_exploitation'] / df_calculated['Chiffre_affaires'])*100
    df_calculated['Marge_nette(%)'] = (df_calculated['Resultat_net'] / df_calculated['Chiffre_affaires'])*100
    
    # 3. Ratios d'endettement
    df_calculated['GEARING(%)'] = (df_calculated['ENDETTEMENTNET'] / (df_calculated['ENDETTEMENTNET'] + df_calculated['Capitaux_propres']))*100
    
    # 4. Ratios de liquidité (si les données sont disponibles)
    if 'ACTIFCOURANT' in df_calculated.columns and 'PASSIFCOURANT' in df_calculated.columns:
        df_calculated['Ratio_liquidite(%)'] = (df_calculated['ACTIFCOURANT'] / df_calculated['PASSIFCOURANT'])*100
    
        df_calculated['Ratio_levier(%)'] = (df_calculated['dettes_total'] / df_calculated['Capitaux_propres'])*100
    
        if 'Chiffre_affaires' in df_calculated.columns:
            df_calculated['Marge_EBITDA(%)'] = (df_calculated['EBITDA'] / df_calculated['Chiffre_affaires'])*100
    
    # 6. Ratios d'investissement (si les données sont disponibles)
    if 'IMMOB INCO(n)' in df_calculated.columns and 'IMMOB INCO(n-1)' in df_calculated.columns and 'IMMOB CO(n)' in df_calculated.columns and 'IMMOB CO(n-1)' in df_calculated.columns and 'AMMORT INCO' in df_calculated.columns and 'AMMORT COR' in df_calculated.columns:
        df_calculated['CAPEX(en MMAD)'] = df_calculated['IMMOB INCO(n)'] - df_calculated['IMMOB INCO(n-1)'] + df_calculated['IMMOB CO(n)'] - df_calculated['IMMOB CO(n-1)'] + df_calculated['AMMORT INCO'] + df_calculated['AMMORT COR']
    
    st.success("✅ Tous les ratios financiers ont été calculés avec succès!")
    
    return df_calculated

# Fonction pour charger les données bancaires (également modifiée)
def load_banking_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            st.error("Format de fichier non supporté. Veuillez uploader un fichier Excel (.xlsx) or CSV (.csv)")
            return None
        
        # Renommer les colonnes pour correspondre à vos données
        df = df.rename(columns={
            'BANQUE': 'Emmeteur',
            'Chiffre_d_affaires': 'Produit_net_bancaire',
            'Resultat_d_exploitation': 'Resulta_exploitation',
            'dettes_total': 'DETTEDEFINANCIERS',
            'Total_actif ': 'Total_actif'  # Correction de l'espace en fin de nom
        })
        
        # Vérification des colonnes nécessaires pour le secteur bancaire
        required_columns = ['Emmeteur', 'Produit_net_bancaire', 'Resultat_net', 'Total_actif', 
                           'Capitaux_propres', 'EBITDA']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            st.error(f"Colonnes manquantes dans le fichier bancaire: {', '.join(missing_columns)}")
            return None
        
        # Nettoyer les valeurs numériques (enlever les pourcentages et convertir en float)
        for col in ['Resultat_net', 'Total_actif', 'Capitaux_propres', 'Produit_net_bancaire', 'EBITDA']:
            if col in df.columns:
                # Convertir les pourcentages en nombres décimaux si nécessaire
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.replace('%', '').str.replace(',', '.').str.strip()
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                else:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # CALCUL DES RATIOS BANCAIRES (NOUVEAU)
        st.info(" Calcul des ratios bancaires en cours...")
        
        # Calcul des ratios bancaires spécifiques
        df['ROA'] = df['Resultat_net'] / df['Total_actif']
        df['ROE'] = df['Resultat_net'] / df['Capitaux_propres']
        
        # Ratio d'efficience (charges/PNB)
        if 'EBITDA' in df.columns and 'Produit_net_bancaire' in df.columns:
            df['Ratio_efficience'] = df['EBITDA'] / df['Produit_net_bancaire']
        
        # Ratio de levier (Capitaux propres/Total actif)
        df['Ratio_leverage'] = df['Capitaux_propres'] / df['Total_actif']
        
        # Ratio de solvabilité (si les données sont disponibles)
        if 'Fonds_propres' in df.columns and 'Total_actif' in df.columns:
            df['Ratio_solvabilite'] = df['Fonds_propres'] / df['Total_actif']
        
        # Ratio de liquidité (si les données sont disponibles)
        if 'Depots' in df.columns and 'Credits' in df.columns:
            df['Ratio_LDR'] = df['Credits'] / df['Depots']
        
        # Ajouter une colonne secteur pour identifier comme bancaire
        df['Secteur'] = 'Bancaire'
        
        st.success("✅ Tous les ratios bancaires ont été calculés avec succès!")
        
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données bancaires: {str(e)}")
        return None

# ... [Le reste du code reste inchangé] ...

# Fonction pour ajouter un émetteur personnalisé
def add_custom_emetteur():
    """Ajoute un émetteur personnalisé avec saisie manuelle"""
    st.subheader("➕ Ajouter un nouvel émetteur")
    
    with st.form("custom_emetteur_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            emetteur_name = st.text_input("Nom de l'émetteur*")
            secteur = st.selectbox("Secteur*", list(SECTEURS_EMETTEURS.keys()))
            chiffre_affaires = st.number_input("Chiffre d'affaires (MAD)*", min_value=0.0, format="%.2f")
            resultat_net = st.number_input("Résultat net (MAD)*", format="%.2f")
            capitaux_propres = st.number_input("Capitaux propres (MAD)*", min_value=0.0, format="%.2f")
            total_actif = st.number_input("Total actif (MAD)*", min_value=0.0, format="%.2f")
        
        with col2:
            resultat_exploitation = st.number_input("Résultat d'exploitation (MAD)", value=0.0, format="%.2f")
            dette_financiere_brute = st.number_input("Dette financière brute (MAD)*", min_value=0.0, value=0.0, format="%.2f")
            tresorerie = st.number_input("Trésorerie (MAD)*", min_value=0.0, value=0.0, format="%.2f")
            dette_financiere_nette = st.number_input("Endettement net (MAD)", value=0.0, format="%.2f", 
                                                   help="Dette financière brute - Trésorerie")
            ebitda = st.number_input("EBITDA (MAD)", value=0.0, format="%.2f")
            capex = st.number_input("CAPEX (MAD)", min_value=0.0, value=0.0, format="%.2f")
        
        submitted = st.form_submit_button("Ajouter l'émetteur")
        
        if submitted:
            # Validation des champs obligatoires
            if not emetteur_name or not secteur:
                st.error("❌ Le nom et le secteur sont obligatoires")
                return None
            
            if (chiffre_affaires == 0 or resultat_net == 0 or capitaux_propres == 0 or 
                total_actif == 0 or dette_financiere_brute == 0 or tresorerie == 0):
                st.error("❌ Les champs marqués d'un * sont obligatoires")
                return None
            
            # Calcul automatique de l'endettement net si non saisi
            if dette_financiere_nette == 0:
                dette_financiere_nette = dette_financiere_brute - tresorerie
            
            # Création du nouvel émetteur
            new_emetteur = {
                'Emmeteur': emetteur_name,
                'Secteur': secteur,
                'Chiffre_affaires': chiffre_affaires,
                'Resultat_net': resultat_net,
                'Capitaux_propres': capitaux_propres,
                'Total_actif': total_actif,
                'Resulta_exploitation': resultat_exploitation if resultat_exploitation != 0 else np.nan,
                'DETTEDEFINANCIERS': dette_financiere_brute,
                'Trésorerie': tresorerie,
                'Endettement_net': dette_financiere_nette,
                'EBITDA': ebitda if ebitda != 0 else np.nan,
                'CAPEX': capex if capex != 0 else np.nan
            }
            
            # Calcul des ratios de base
            if total_actif and total_actif > 0:
                new_emetteur['ROA'] = resultat_net / total_actif
            else:
                new_emetteur['ROA'] = np.nan
            
            if capitaux_propres and capitaux_propres > 0:
                new_emetteur['ROE'] = resultat_net / capitaux_propres
            else:
                new_emetteur['ROE'] = np.nan
            
            if chiffre_affaires and chiffre_affaires > 0 and resultat_exploitation and resultat_exploitation != 0:
                new_emetteur['Marge_operationnelle'] = resultat_exploitation / chiffre_affaires
            else:
                new_emetteur['Marge_operationnelle'] = np.nan
            
            # Calcul des ratios d'endettement
            if dette_financiere_brute and capitaux_propres and capitaux_propres > 0:
                total_capital = dette_financiere_brute + capitaux_propres
                if total_capital > 0:
                    new_emetteur['GEARING'] = dette_financiere_nette / (dette_financiere_nette + capitaux_propres)
                    new_emetteur['Taux d\'endettement'] = dette_financiere_brute / capitaux_propres
                else:
                    new_emetteur['GEARING'] = np.nan
                    new_emetteur['Taux d\'endettement'] = np.nan
            else:
                new_emetteur['GEARING'] = np.nan
                new_emetteur['Taux d\'endettement'] = np.nan
            
            # Calcul des ratios de couverture
            if ebitda and ebitda != 0 and dette_financiere_nette:
                new_emetteur['Ratio_couverture_dette'] = ebitda / dette_financiere_nette
            else:
                new_emetteur['Ratio_couverture_dette'] = np.nan
            
            if ebitda and ebitda != 0 and dette_financiere_brute:
                new_emetteur['Ratio_couverture_dette_brute'] = ebitda / dette_financiere_brute
            else:
                new_emetteur['Ratio_couverture_dette_brute'] = np.nan
            
            st.success(f"✅ Émetteur '{emetteur_name}' créé avec succès!")
            return new_emetteur
    
    return None
# Fonctions de scoring avec détails
def calculate_threshold_score(value, ratio, secteur):
    """Calcule le score basé sur les seuils sectoriels (Méthode 1) et retourne les détails"""
    if pd.isna(value):
        return np.nan, {"valeur": np.nan, "seuils": {}, "score": np.nan, "niveau": "Non calculé"}
    
    # Vérifier si le ratio existe dans les seuils
    if secteur in SEUILS_SECTORIELS and ratio in SEUILS_SECTORIELS[secteur]:
        seuils = SEUILS_SECTORIELS[secteur][ratio]
    elif ratio in SEUILS_SECTORIELS["default"]:
        seuils = SEUILS_SECTORIELS["default"][ratio]
    else:
        # Si le ratio n'existe pas dans les seuils, retourner un score neutre
        return 2, {"valeur": value, "seuils": {}, "score": 2, "niveau": "Non défini"}
    
    # Logique inversée pour les ratios où une valeur basse est meilleure
    invert_ratios = ['CAPEX', 'GEARING', 'Ratio levier', 'Taux d\'endettement', 
                    'Ratio_efficience', 'Ratio_NPL', 'Ratio_LDR']
    
    details = {
        "valeur": value,
        "seuils": seuils.copy(),
        "score": 0,
        "niveau": ""
    }
    
    if ratio in invert_ratios:
        if value <= seuils["excellent"]:
            details["score"] = 4
            details["niveau"] = "Excellent"
        elif value <= seuils["satisfactory"]:
            details["score"] = 3
            details["niveau"] = "Satisfaisant"
        elif value <= seuils["alert"]:
            details["score"] = 2
            details["niveau"] = "Alerte"
        elif value <= seuils["danger"]:
            details["score"] = 1
            details["niveau"] = "Danger"
        else:
            details["score"] = 0
            details["niveau"] = "Critique"
    else:
        if value >= seuils["excellent"]:
            details["score"] = 4
            details["niveau"] = "Excellent"
        elif value >= seuils["satisfactory"]:
            details["score"] = 3
            details["niveau"] = "Satisfaisant"
        elif value >= seuils["alert"]:
            details["score"] = 2
            details["niveau"] = "Alerte"
        elif value >= seuils["danger"]:
            details["score"] = 1
            details["niveau"] = "Danger"
        else:
            details["score"] = 0
            details["niveau"] = "Critique"
    
    return details["score"], details
# Déplacer calculate_quantile_score AVANT calculate_final_score

def calculate_quantile_score(value, values_series, emetteur):
    """Calcule le score basé sur le quantile sectoriel (Méthode 6) et retourne les détails"""
    if pd.isna(value):
        return np.nan, {"valeur": np.nan, "quantile": np.nan, "score": np.nan, "position": "Non calculé"}
        
    if len(values_series) < 2:
        return 2, {"valeur": value, "quantile": 0.5, "score": 2, "position": "Médiane (secteur mono-émetteur)"}
    
    # Supprimer les valeurs NaN pour le calcul des quantiles
    clean_series = values_series.dropna()
    if len(clean_series) < 2:
        return 2, {"valeur": value, "quantile": 0.5, "score": 2, "position": "Médiane (données insuffisantes)"}
    
    # Calcul du quantile
    quantile = clean_series.rank(pct=True)[clean_series == value].values[0]
    score = quantile * 4
    
    # Détermination de la position
    if quantile >= 0.8:
        position = "Top 20%"
    elif quantile >= 0.6:
        position = "Top 40%"
    elif quantile >= 0.4:
        position = "Moyenne"
    elif quantile >= 0.2:
        position = "Bottom 40%"
    else:
        position = "Bottom 20%"
    
    details = {
        "valeur": value,
        "quantile": quantile,
        "score": score,
        "position": position,
        "classement": f"{int(quantile * 100)}ème percentile"
    }
    
    return score, details

def calculate_final_score(sector_data, secteur_type="standard"):
    """Calcule le score final hybride pour tous les émetteurs d'un secteur avec détails"""
    
    # Définir les ratios en fonction du type de secteur
    if secteur_type == "bancaire":
        ratios = ['ROA', 'ROE', 'Ratio_efficience', 'Ratio_leverage', 
                  'Ratio_NPL', 'Ratio_LDR', 'Ratio_Fonds_Propres', 'Ratio_Solvabilite']
    else:
        # Mapping des noms de ratios avec leurs variantes possibles
        ratio_patterns = {
            'ROA': ['ROA', 'ROA(%)'],
            'ROE': ['ROE', 'ROE(%)'],
            'Marge_operationnelle': ['Marge_operationnelle', 'Marge_operationnelle(%)'],
            'GEARING': ['GEARING', 'GEARING(%)'],
            'Ratio_liquidite': ['Ratio_liquidite(%)', 'Ratio liquidité'],
            'Ratio_levier': ['Ratio_levier(%)', 'Ratio levier'],
            'Taux_endettement': ['Taux_endettement', 'Taux d\'endettement'],
            'CAPEX': ['CAPEX', 'CAPEX(en MMAD)']
        }
        
        # Identifier les ratios disponibles dans les données
        ratios = []
        for ratio_name, patterns in ratio_patterns.items():
            for pattern in patterns:
                if pattern in sector_data.columns:
                    ratios.append(pattern)  # Utiliser le nom réel de la colonne
                    break
    
    scores_df = sector_data[['Emmeteur']].copy()
    score_details = {}
    
    for ratio in ratios:
        # Initialiser les colonnes de score
        scores_df[f'{ratio}_score1'] = np.nan
        scores_df[f'{ratio}_score2'] = np.nan
        scores_df[f'{ratio}_final'] = np.nan
        
        for idx, row in sector_data.iterrows():
            emetteur = row['Emmeteur']
            valeur = row[ratio]
            secteur = row['Secteur']
            
            if pd.isna(valeur):
                continue
                
            # Déterminer le nom du ratio pour les seuils (enlever les caractères spéciaux)
            ratio_name_for_thresholds = ratio
            if '(%)' in ratio:
                ratio_name_for_thresholds = ratio.replace('(%)', '')
            if '(en MMAD)' in ratio:
                ratio_name_for_thresholds = ratio.replace('(en MMAD)', '')
            
            # Score méthode 1 (seuils)
            score1, details1 = calculate_threshold_score(valeur, ratio_name_for_thresholds, secteur)
            
            # Score méthode 2 (quantiles)
            score2, details2 = calculate_quantile_score(valeur, sector_data[ratio], emetteur)
            
            # Score hybride (60% méthode 1, 40% méthode 2)
            score_final = 0.6 * score1 + 0.4 * score2
            
            # Utiliser les bonnes variables
            scores_df.at[idx, f'{ratio}_score1'] = score1
            scores_df.at[idx, f'{ratio}_score2'] = score2
            scores_df.at[idx, f'{ratio}_final'] = score_final
            
            # Stocker les détails
            if emetteur not in score_details:
                score_details[emetteur] = {}
            score_details[emetteur][ratio] = {
                "methode1": details1,
                "methode2": details2,
                "score_final": score_final
            }
    
    # Calcul du score global moyen (en ignorant les NaN)
    ratio_columns = [col for col in scores_df.columns if '_final' in col]
    
    # Vérifier que les colonnes existent
    valid_ratio_columns = [col for col in ratio_columns if col in scores_df.columns]
    
    if valid_ratio_columns:
        scores_df['Score_global'] = scores_df[valid_ratio_columns].mean(axis=1, skipna=True)
        scores_df['Score_normalisé'] = (scores_df['Score_global'] / 4 * 100).round(2)
    else:
        scores_df['Score_global'] = np.nan
        scores_df['Score_normalisé'] = np.nan
    
    # Stocker les détails dans session_state
    st.session_state.score_details = score_details
    
    return scores_df
# Barre latérale
st.sidebar.image("/content/Al_Barik_Bank_logo.png", use_container_width=True)
with st.sidebar:
    st.header(" Informations")
    st.markdown("""
    **👉 Système de Scoring Hybride:**
    - Méthode 1: Points de rupture (seuils sectoriels)
    - Méthode 2: Classement par quantiles sectoriels
    - Combinaison: 60% Méthode 1 + 40% Méthode 2
    """)
    
    st.markdown("""
    **👉 Secteurs couverts:**
    - Matériaux de Construction
    - BTP & Génie Civil  
    - Immobilier & Tourisme  
    - Agroalimentaire  
    - Distribution & Consommation  
    - Énergie & Utilities  
    - Finance & Services Financiers  
    - Télécommunications
    - Transport & Infrastructures
    - Bancaire (onglet spécifique)
    """)


# Création des onglets - AJOUT DE L'ONGLET BANCAIRE
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    " Secteurs non Financières", 
    " Analyse Secteur", 
    " Scoring Sectoriel", 
    " Secteur Bancaire",
    " AL BARID BANK", 
    "📤 Export Résultats",
])

# Onglet 1: Chargement des données
with tab1:
    st.header("📥 Secteurs non financiers - Chargement des données")
    
    # Paragraphe explicatif
    st.markdown("""
    ** Notre application de scoring des secteurs non financiers utilise ces ratios financiers :**
    
    - **ROA** : Return on Assets (Rentabilité des actifs)
    - **ROE** : Return on Equity (Rentabilité des capitaux propres)  
    - **Marge_operationnelle** : Marge opérationnelle
    - **GEARING** : Ratio d'endettement
    - **Ratio_liquidite** : Ratio de liquidité
    - **Ratio_levier** : Ratio de levier
    - **CAPEX** : Dépenses d'investissement
    """)
    
    # Uploader pour les données
    uploaded_file = st.file_uploader("Téléchargez votre fichier (Excel ou CSV)", 
                                   type=['xlsx', 'csv'],
                                   help="Le fichier doit contenir les colonnes de base ou les ratios pré-calculés")
    
    if uploaded_file is not None:
        df = load_and_prepare_data(uploaded_file)
        if df is not None:
            # Afficher les données brutes d'abord
            st.subheader("📋 Données chargées")
            st.dataframe(df.head(), use_container_width=True)
            
            st.write(f"**Dimensions:** {df.shape[0]} lignes × {df.shape[1]} colonnes")
            st.write(f"**Colonnes disponibles:** {', '.join(df.columns.tolist())}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Bouton 1: Utiliser les données telles quelles
                if st.button("📊 Utiliser les données existantes", key="use_existing_data", 
                           help="Utiliser les données telles qu'elles sont dans le fichier"):
                    st.session_state.df = df
                    st.session_state.ratios_source = "fichier"
                    st.session_state.data_loaded = True
                    st.success("✅ Données chargées avec succès!")
            
            with col2:
                # Bouton 2: Calculer les ratios à partir des données de base
                if st.button("🧮 Calculer les ratios financiers", key="calculate_ratios",
                           help="Calculer les ratios à partir des données financières de base"):
                    # Vérifier si on a les données nécessaires pour calculer les ratios
                    colonnes_requises = ['Resultat_net', 'Total_actif', 'Capitaux_propres', 
                                       'Resulta_exploitation', 'Chiffre_affaires', 'DETTEDEFINANCIERS']
                    
                    colonnes_manquantes = [col for col in colonnes_requises if col not in df.columns]
                    
                    if colonnes_manquantes:
                        st.error("**❌ Impossible de calculer les ratios. Colonnes manquantes:**")
                        for col in colonnes_manquantes:
                            st.write(f"• {col}")
                    else:
                        with st.spinner("Calcul des ratios financiers en cours..."):
                            df_calculated = calculate_ratios(df)
                            st.session_state.df = df_calculated
                            st.session_state.ratios_source = "calculés"
                            st.session_state.data_loaded = True
                            st.success("✅ Ratios calculés avec succès!")
            
            # Informations sur l'état actuel
            if 'df' in st.session_state and st.session_state.df is not None:
                current_df = st.session_state.df
                st.subheader("Données actuelles pour l'analyse")
                source = st.session_state.get('ratios_source', 'inconnue')
                st.info(f"**Source des ratios:** {source}")
                
                # Aperçu des données actuelles
                st.dataframe(current_df.head(), use_container_width=True)
                
                # Afficher toutes les colonnes disponibles pour le débogage
                st.write("**🔍 Toutes les colonnes disponibles:**")
                for col in current_df.columns:
                    st.write(f"• {col}")
                
                # Vérifier les ratios disponibles (en cherchant les noms réels)
                ratio_patterns = {
                    'ROA': ['ROA', 'ROA(%)', 'Return on Assets'],
                    'ROE': ['ROE', 'ROE(%)', 'Return on Equity'],
                    'Marge_operationnelle': ['Marge_operationnelle', 'Marge_operationnelle(%)', 'Marge opérationnelle'],
                    'GEARING': ['GEARING', 'GEARING(%)', 'Gearing'],
                    'Ratio_liquidite': ['Ratio_liquidite(%)', 'Ratio liquidité', 'Liquidité'],
                    'Ratio_levier': ['Ratio_levier(%)', 'Ratio levier', 'Levier'],
                    'CAPEX': ['CAPEX', 'CAPEX(en MMAD)', 'Investissements']
                }
                
                ratios_trouves = {}
                for ratio_name, patterns in ratio_patterns.items():
                    for pattern in patterns:
                        if pattern in current_df.columns:
                            ratios_trouves[ratio_name] = pattern
                            break
                
                if ratios_trouves:
                    st.success("**✅ Ratios disponibles pour le scoring:**")
                    for ratio_name, col_name in ratios_trouves.items():
                        st.write(f"• {ratio_name} (colonne: {col_name})")
                
                # Vérifier les ratios manquants
                ratios_manquants = [ratio for ratio in ratio_patterns.keys() if ratio not in ratios_trouves]
                if ratios_manquants:
                    st.warning("**⚠️ Ratios manquants pour le scoring complet:**")
                    for ratio in ratios_manquants:
                        st.write(f"• {ratio}")
                
                # Statistiques basiques
                st.subheader("📈 Statistiques des données")
                col_stats1, col_stats2, col_stats3 = st.columns(3)
                
                with col_stats1:
                    st.metric("Nombre d'émetteurs", len(current_df))
                
                with col_stats2:
                    secteurs_count = current_df['Secteur'].nunique() if 'Secteur' in current_df.columns else 0
                    st.metric("Nombre de secteurs", secteurs_count)
                
                with col_stats3:
                    ratios_count = len(ratios_trouves)
                    st.metric("Ratios disponibles", ratios_count)
    else:
        st.info("ℹ️ Veuillez télécharger un fichier Excel ou CSV contenant les données financières")
# Onglet 2: Analyse par secteur
with tab2:
    st.header("📊 Analyse par Secteur")
    
    if 'df' not in st.session_state or st.session_state.df is None:
        st.warning("⚠️ Veuillez d'abord charger les données dans l'onglet 'Chargement données'.")
    else:
        df = st.session_state.df
        
        # Sélection du secteur
        secteurs_disponibles = [s for s in df['Secteur'].unique() if s and s != '']
        if not secteurs_disponibles:
            st.warning("Aucun secteur disponible dans les données.")
        else:
            selected_sector = st.selectbox("Choisir un secteur", secteurs_disponibles)
            
            sector_data = df[df['Secteur'] == selected_sector].copy()
            st.session_state.sector_data = sector_data
            st.session_state.selected_sector = selected_sector
            
            st.subheader(f"Émetteurs du secteur {selected_sector}")
            
            # Afficher les données disponibles
            st.dataframe(sector_data.head(), use_container_width=True)
            
            # Analyse des ratios - CORRECTION COMPLÈTE ICI
            st.subheader("Analyse des ratios")
            
            # Chercher les ratios disponibles (avec différents noms possibles)
            ratio_patterns = {
                'ROA': ['ROA', 'ROA(%)'],
                'ROE': ['ROE', 'ROE(%)'],
                'Marge_operationnelle': ['Marge_operationnelle', 'Marge_operationnelle(%)'],
                'GEARING': ['GEARING', 'GEARING(%)'],
                'Ratio_liquidite': ['Ratio_liquidite(%)', 'Ratio liquidité'],
                'Ratio_levier': ['Ratio_levier(%)', 'Ratio levier'],
                
            }
            
            available_ratio_cols = []
            for ratio_name, patterns in ratio_patterns.items():
                for pattern in patterns:
                    if pattern in sector_data.columns:
                        available_ratio_cols.append(pattern)
                        break
            
            if available_ratio_cols:
                st.write(f"**Ratios disponibles:** {', '.join(available_ratio_cols)}")
                
                # CORRECTION CRITIQUE : Créer des valeurs par défaut qui existent VRAIMENT
                default_ratios = []
                
                # Essayer d'abord les noms avec pourcentage
                preferred_patterns = ['ROE(%)', 'Marge_operationnelle(%)', 'GEARING(%)', 
                                    'ROE', 'Marge_operationnelle', 'GEARING']
                
                for pattern in preferred_patterns:
                    if pattern in available_ratio_cols and pattern not in default_ratios:
                        default_ratios.append(pattern)
                        if len(default_ratios) >= 2:  # Seulement 2 par défaut pour être sûr
                            break
                
                # Si toujours rien, prendre les premiers disponibles
                if not default_ratios and available_ratio_cols:
                    default_ratios = available_ratio_cols[:min(2, len(available_ratio_cols))]
                
                # S'assurer que toutes les valeurs par défaut existent vraiment
                valid_default_ratios = [ratio for ratio in default_ratios if ratio in available_ratio_cols]
                
                if not valid_default_ratios and available_ratio_cols:
                    valid_default_ratios = [available_ratio_cols[0]]  # Prendre le premier disponible
                
                st.write(f"**Ratios sélectionnés par défaut:** {', '.join(valid_default_ratios)}")
                
                # MULTISELECT CORRIGÉ - valeurs par défaut garanties d'exister
                selected_ratios = st.multiselect(
                    "Sélection des ratios à comparer", 
                    available_ratio_cols,
                    default=valid_default_ratios
                )
                
                if selected_ratios and len(sector_data) > 0:
                    # Filtrer les données pour enlever les NaN
                    valid_data = sector_data[['Emmeteur'] + selected_ratios].dropna()
                    
                    if len(valid_data) > 0:
                        melt_df = valid_data.melt(id_vars=['Emmeteur'], value_vars=selected_ratios, 
                                                 var_name='Ratio', value_name='Valeur')
                        
                        fig, ax = plt.subplots(figsize=(12, 6))
                        sns.barplot(data=melt_df, x='Emmeteur', y='Valeur', hue='Ratio', ax=ax)
                        ax.set_title(f"Comparaison des ratios - {selected_sector}")
                        ax.tick_params(axis='x', rotation=45)
                        st.pyplot(fig)
                    else:
                        st.warning("Aucune donnée valide pour les ratios sélectionnés")
                else:
                    st.info("Veuillez sélectionner au moins un ratio à comparer")
            else:
                st.warning("Aucun ratio disponible pour l'analyse comparative")
                st.write("Colonnes disponibles:", list(sector_data.columns))

# Onglet 3: Scoring sectoriel
with tab3:
    st.header(" Scoring Sectoriel")
    
    if 'sector_data' not in st.session_state or st.session_state.sector_data is None:
        st.warning("⚠️ Veuillez d'abord sélectionner un secteur dans l'onglet 'Analyse Secteur'.")
    else:
        sector_data = st.session_state.sector_data
        selected_sector = st.session_state.selected_sector
        
        # DEBUG: Afficher les données du secteur pour vérifier
        st.write("📋 Données du secteur pour débogage:")
        st.dataframe(sector_data)
        
        # Vérifier quels ratios sont disponibles
        ratios_disponibles = [col for col in sector_data.columns if col in ['ROA', 'ROE', 'Marge_operationnelle', 'GEARING', 
                                                                          'Ratio_liquidite', 'Ratio_levier', 'CAPEX']]
        st.write(f"📊 Ratios disponibles: {ratios_disponibles}")
        
        # Calcul des scores
        scores_df = calculate_final_score(sector_data)
        
        # DEBUG: Afficher le résultat du calcul des scores
        st.write("📋 Résultat du calcul des scores:")
        st.dataframe(scores_df)
        
        # Vérifier si le scoring a fonctionné
        if 'Score_normalisé' not in scores_df.columns or scores_df['Score_normalisé'].isnull().all():
            st.error("❌ Le calcul des scores a échoué. Raisons possibles:")
            st.write("- Aucun ratio disponible pour le calcul")
            st.write("- Données manquantes dans les ratios")
            st.write("- Problème dans la fonction calculate_final_score")
            
            # Afficher les détails pour déboguer
            if 'score_details' in st.session_state:
                st.write("Détails des scores:", st.session_state.score_details)
        
        elif len(sector_data) == 1:
            st.info(f"ℹ️ Secteur {selected_sector} avec un seul émetteur - Affichage analytique détaillé")
            
            emetteur = sector_data.iloc[0]
            st.subheader(f"Analyse détaillée - {emetteur['Emmeteur']}")
            
            # Score global
            emetteur_score = scores_df['Score_normalisé'].values[0]
            st.metric("Score Global", f"{emetteur_score:.1f}/100")
            
            # Affichage des détails de calcul
            if emetteur['Emmeteur'] in st.session_state.score_details:
                details = st.session_state.score_details[emetteur['Emmeteur']]
                
                for ratio, ratio_details in details.items():
                    with st.expander(f"📊 Détails du calcul - {ratio}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**Méthode 1 (Seuils)**")
                            st.write(f"Valeur: {ratio_details['methode1']['valeur']:.4f}")
                            st.write(f"Score: {ratio_details['methode1']['score']}/4")
                            st.write(f"Niveau: {ratio_details['methode1']['niveau']}")
                            
                            # Affichage des seuils
                            st.markdown("**Seuils sectoriels:**")
                            for niveau, valeur in ratio_details['methode1']['seuils'].items():
                                st.write(f"{niveau}: {valeur}")
                        
                        with col2:
                            st.markdown("**Méthode 2 (Quantiles)**")
                            st.write(f"Valeur: {ratio_details['methode2']['valeur']:.4f}")
                            st.write(f"Score: {ratio_details['methode2']['score']:.2f}/4")
                            st.write(f"Position: {ratio_details['methode2']['position']}")
                            if 'classement' in ratio_details['methode2']:
                                st.write(f"Classement: {ratio_details['methode2']['classement']}")
                        
                        with col3:
                            st.markdown("**Score Final**")
                            st.metric(
                                label=f"Score {ratio}",
                                value=f"{ratio_details['score_final']:.2f}/4",
                                help="60% Méthode 1 + 40% Méthode 2"
                            )
                            st.write("**Pondération:** 60% Méthode 1 + 40% Méthode 2")
            else:
                st.warning("Aucun détail de score disponible pour cet émetteur")
            
        else:
            st.success(f" Secteur {selected_sector} - Scoring comparatif de {len(sector_data)} émetteurs")
            
            # Affichage du classement
            ranked_emetteurs = scores_df[['Emmeteur', 'Score_normalisé']].sort_values('Score_normalisé', ascending=False)
            
            st.subheader("Classement des émetteurs")
            st.dataframe(
                ranked_emetteurs.style.background_gradient(cmap='RdYlGn', subset=['Score_normalisé']),
                use_container_width=True
            )
            
            # Graphique de classement
            fig3, ax3 = plt.subplots(figsize=(10, 6))
            
            # Vérifier qu'il y a des scores valides
            if not ranked_emetteurs['Score_normalisé'].isnull().all():
                colors = ['gold' if x == ranked_emetteurs['Score_normalisé'].max() else 
                         'lightcoral' if x == ranked_emetteurs['Score_normalisé'].min() else 
                         'lightblue' for x in ranked_emetteurs['Score_normalisé']]
                
                bars = ax3.barh(ranked_emetteurs['Emmeteur'], ranked_emetteurs['Score_normalisé'], color=colors)
                ax3.set_xlabel('Score normalisé (0-100)')
                ax3.set_title(f"Classement - {selected_sector}")
                ax3.bar_label(bars, fmt='%.1f')
                st.pyplot(fig3)
            else:
                st.warning("Aucun score valide pour afficher le graphique")
            
            # Détails de calcul pour chaque émetteur
            st.subheader("🔍 Détails des calculs de scoring")
            
            selected_emetteur = st.selectbox(
                "Sélectionnez un émetteur pour voir les détails de calcul",
                options=ranked_emetteurs['Emmeteur'].tolist()
            )
            
            if selected_emetteur in st.session_state.score_details:
                details = st.session_state.score_details[selected_emetteur]
                
                # Score global
                emetteur_score = ranked_emetteurs[ranked_emetteurs['Emmeteur'] == selected_emetteur]['Score_normalisé'].values[0]
                st.metric("Score Global", f"{emetteur_score:.1f}/100")
                
                # Détails par ratio
                for ratio, ratio_details in details.items():
                    with st.expander(f"Ratio {ratio}", expanded=False):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.markdown("**Méthode 1 - Seuils Sectoriels**")
                            st.write(f"Valeur: {ratio_details['methode1']['valeur']:.4f}")
                            st.write(f"Score: {ratio_details['methode1']['score']}/4")
                            st.write(f"Niveau: {ratio_details['methode1']['niveau']}")
                            
                            # Affichage des seuils
                            st.markdown("**Seuils appliqués:**")
                            for niveau, valeur in ratio_details['methode1']['seuils'].items():
                                st.write(f"{niveau.capitalize()}: {valeur}")
                        
                        with col2:
                            st.markdown("**Méthode 2 - Position Relative**")
                            st.write(f"Valeur: {ratio_details['methode2']['valeur']:.4f}")
                            st.write(f"Score: {ratio_details['methode2']['score']:.2f}/4")
                            st.write(f"Position: {ratio_details['methode2']['position']}")
                            if 'classement' in ratio_details['methode2']:
                                st.write(f"Classement: {ratio_details['methode2']['classement']}")
                        
                        with col3:
                            st.markdown("**Score Final du Ratio**")
                            st.metric(
                                label=f"Score {ratio}",
                                value=f"{ratio_details['score_final']:.2f}/4",
                                help="Calculé comme: 60% × Score Méthode 1 + 40% × Score Méthode 2"
                            )
                            st.write("**Formule:** 0.6 × Méthode 1 + 0.4 × Méthode 2")
            else:
                st.warning(f"Aucun détail de score disponible pour {selected_emetteur}")
# Nouvel onglet 4: Secteur Bancaire
with tab4:
    st.header(" Secteur Bancaire - Analyse Spécifique")
    
    st.markdown("""
    **Chargement des données spécifiques au secteur bancaire**
    
    Les banques nécessitent des ratios spécifiques différents des autres secteurs.
    Veuillez charger un fichier contenant les données bancaires.
    
    **Ratios bancaires supportés:**
    - ROA (Return on Assets)
    - ROE (Return on Equity) 
    - Ratio d'efficience (EBITDA/Produit net bancaire)
    - Ratio de levier (Capitaux propres/Total actif)
    - Ratio NPL (Non-Performing Loans) - si disponible
    - Ratio LDR (Loan-to-Deposit Ratio) - si disponible
    - Ratio Fonds Propres - si disponible
    - Ratio Solvabilité - si disponible
    """)
    
    # Uploader pour les données bancaires
    banking_file = st.file_uploader("Téléchargez le fichier des données bancaires", 
                                  type=['xlsx', 'csv'],
                                  key="banking_uploader",
                                  help="Le fichier doit contenir au minimum: Emmeteur, Resultat_net, Total_actif, Capitaux_propres")
    
    if banking_file is not None:
        banking_data = load_banking_data(banking_file)
        if banking_data is not None:
            st.session_state.banking_data = banking_data
            st.success("✅ Données bancaires chargées avec succès!")
            
            # Aperçu des données bancaires
            st.subheader("Aperçu des données bancaires")
            st.dataframe(banking_data.head(), use_container_width=True)
            
            # Calcul automatique des scores bancaires
            st.subheader("🎯 Calcul du Scoring Bancaire")
            
            # Calcul des scores
            banking_scores = calculate_final_score(banking_data, "bancaire")
            st.session_state.banking_scores = banking_scores
            
            # Affichage des scores
            st.subheader("🏆 Classement des banques")
            
            ranked_banks = banking_scores[['Emmeteur', 'Score_normalisé']].sort_values('Score_normalisé', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.dataframe(
                    ranked_banks.style.background_gradient(cmap='RdYlGn', subset=['Score_normalisé']),
                    use_container_width=True
                )
            
            with col2:
                # Statistiques du secteur bancaire
                avg_score = ranked_banks['Score_normalisé'].mean()
                min_score = ranked_banks['Score_normalisé'].min()
                max_score = ranked_banks['Score_normalisé'].max()
                
                st.metric("Score Moyen", f"{avg_score:.1f}/100")
                st.metric("Score Minimum", f"{min_score:.1f}/100")
                st.metric("Score Maximum", f"{max_score:.1f}/100")
            
            # Graphique de classement
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = ['gold' if x == max_score else 
                     'lightcoral' if x == min_score else 
                     'lightblue' for x in ranked_banks['Score_normalisé']]
            
            bars = ax.barh(ranked_banks['Emmeteur'], ranked_banks['Score_normalisé'], color=colors)
            ax.set_xlabel('Score normalisé (0-100)')
            ax.set_title("Classement des banques")
            ax.bar_label(bars, fmt='%.1f')
            st.pyplot(fig)
            
            # Analyse détaillée des ratios bancaires
            st.subheader("📊 Analyse des ratios bancaires")
            
            # Sélection de la banque pour analyse détaillée
            selected_bank = st.selectbox(
                "Sélectionnez une banque pour voir les détails",
                options=ranked_banks['Emmeteur'].tolist()
            )
            
            if selected_bank in st.session_state.score_details:
                details = st.session_state.score_details[selected_bank]
                
                # Score global
                bank_score = ranked_banks[ranked_banks['Emmeteur'] == selected_bank]['Score_normalisé'].values[0]
                st.metric(f"Score Global - {selected_bank}", f"{bank_score}/100")
                
                # Détails des ratios bancaires
                banking_ratios = ['ROA', 'ROE', 'Ratio_efficience', 'Ratio_leverage', 
                                'Ratio_NPL', 'Ratio_LDR', 'Ratio_Fonds_Propres', 'Ratio_Solvabilite']
                
                for ratio in banking_ratios:
                    if ratio in details:
                        with st.expander(f"Ratio {ratio}", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown("**Méthode 1 - Seuils Sectoriels**")
                                st.write(f"Valeur: {details[ratio]['methode1']['valeur']:.4f}")
                                st.write(f"Score: {details[ratio]['methode1']['score']}/4")
                                st.write(f"Niveau: {details[ratio]['methode1']['niveau']}")
                                
                                # Affichage des seuils bancaires
                                st.markdown("**Seuils bancaires:**")
                                if 'Bancaire' in SEUILS_SECTORIELS and ratio in SEUILS_SECTORIELS['Bancaire']:
                                    for niveau, valeur in SEUILS_SECTORIELS['Bancaire'][ratio].items():
                                        st.write(f"{niveau.capitalize()}: {valeur}")
                            
                            with col2:
                                st.markdown("**Méthode 2 - Position Relative**")
                                st.write(f"Valeur: {details[ratio]['methode2']['valeur']:.4f}")
                                st.write(f"Score: {details[ratio]['methode2']['score']:.2f}/4")
                                st.write(f"Position: {details[ratio]['methode2']['position']}")
                                if 'classement' in details[ratio]['methode2']:
                                    st.write(f"Classement: {details[ratio]['methode2']['classement']}")
                            
                            with col3:
                                st.markdown("**Score Final du Ratio**")
                                st.metric(
                                    label=f"Score {ratio}",
                                    value=f"{details[ratio]['score_final']:.2f}/4",
                                    help="Calculé comme: 60% × Score Méthode 1 + 40% × Score Méthode 2"
                                )
            
            # Comparaison des ratios bancaires
            st.subheader("📈 Comparaison des ratios bancaires")
            
            banking_ratio_cols = ['ROA', 'ROE', 'Ratio_efficience', 'Ratio_leverage']
            available_banking_ratios = [col for col in banking_ratio_cols if col in banking_data.columns]
            
            if available_banking_ratios:
                selected_banking_ratios = st.multiselect(
                    "Sélectionnez les ratios à comparer", 
                    available_banking_ratios, 
                    default=['ROE', 'Ratio_efficience', 'Ratio_leverage']
                )
                
                if selected_banking_ratios:
                    melt_banking_df = banking_data.melt(
                        id_vars=['Emmeteur'], 
                        value_vars=selected_banking_ratios, 
                        var_name='Ratio', 
                        value_name='Valeur'
                    )
                    
                    fig2, ax2 = plt.subplots(figsize=(12, 6))
                    sns.barplot(data=melt_banking_df, x='Emmeteur', y='Valeur', hue='Ratio', ax=ax2)
                    ax2.set_title("Comparaison des ratios bancaires")
                    ax2.tick_params(axis='x', rotation=45)
                    st.pyplot(fig2)
            
            # Comparaison des ratios bancaires
            st.subheader("📈 Comparaison des ratios bancaires")
            
            banking_ratio_cols = ['ROA', 'ROE', 'Ratio_efficience', 'Ratio_leverage']
            available_banking_ratios = [col for col in banking_ratio_cols if col in banking_data.columns]
            
            if available_banking_ratios:
                selected_banking_ratios = st.multiselect(
                    "Sélectionnez les ratios à comparer", 
                    available_banking_ratios, 
                    default=['ROE', 'Ratio_efficience', 'Ratio_leverage']
                )
                
                if selected_banking_ratios:
                    melt_banking_df = banking_data.melt(
                        id_vars=['Emmeteur'], 
                        value_vars=selected_banking_ratios, 
                        var_name='Ratio', 
                        value_name='Valeur'
                    )
                    
                    fig2, ax2 = plt.subplots(figsize=(12, 6))
                    sns.barplot(data=melt_banking_df, x='Emmeteur', y='Valeur', hue='Ratio', ax=ax2)
                    ax2.set_title("Comparaison des ratios bancaires")
                    ax2.tick_params(axis='x', rotation=45)
                    st.pyplot(fig2)

# Les onglets suivants restent inchangés (AL BARID BANK, Analyse Comparative, Export, Résumé Tous Secteurs)
# ... [Le reste du code reste inchangé] ...

# Onglet 5: AL BARID BANK
# Onglet 5: AL BARID BANK
with tab5:
    st.header("🏦 AL BARID BANK - Analyse du Portefeuille")
    
    if 'df' not in st.session_state or st.session_state.df is None:
        st.warning("⚠️ Veuillez d'abord charger les données dans l'onglet 'Chargement données'.")
    else:
        df = st.session_state.df
        
        st.markdown("""
        **Sélectionnez les émetteurs du portefeuille de AL BARID BANK pour analyser leur performance**
        """)
        
        # Sélection des émetteurs
        selected_emetteurs = st.multiselect(
            "Sélectionnez les émetteurs du portefeuille",
            options=AL_BARID_BANK_EMETTEURS,
            default=st.session_state.al_barid_selection
        )
        
        # Bouton pour valider la sélection
        if st.button("✅ Valider la sélection", key="validate_selection"):
            st.session_state.al_barid_selection = selected_emetteurs
            st.success("Sélection validée avec succès!")
        
        if st.session_state.al_barid_selection:
            # Filtrer les données pour les émetteurs sélectionnés
            al_barid_data = df[df['Emmeteur'].isin(st.session_state.al_barid_selection)].copy()
            
            if not al_barid_data.empty:
                st.success(f"✅ {len(al_barid_data)} émetteurs sélectionnés")
                
                # Affichage des données
                st.subheader("📋 Données des émetteurs sélectionnés")
                
                # Colonnes à afficher
                display_columns = ['Emmeteur', 'Secteur', 'Chiffre_affaires', 'Resultat_net', 
                                 'ROA', 'ROE', 'Marge_operationnelle', 'GEARING', 'Taux d\'endettement']
                available_columns = [col for col in display_columns if col in al_barid_data.columns]
                
                st.dataframe(al_barid_data[available_columns], use_container_width=True)
                
                # Calcul des scores par secteur
                st.subheader("🎯 Scoring Sectoriel du Portefeuille")
                
                # Grouper par secteur et calculer les scores pour chaque secteur
                all_sector_scores = []
                
                for secteur in al_barid_data['Secteur'].unique():
                    if secteur:  # Vérifier que le secteur n'est pas vide
                        secteur_data = al_barid_data[al_barid_data['Secteur'] == secteur].copy()
                        if len(secteur_data) > 0:
                            # Calculer les scores pour ce secteur
                            scores_df = calculate_final_score(secteur_data)
                            
                            # Ajouter les scores au dataframe global
                            scores_df['Secteur'] = secteur
                            all_sector_scores.append(scores_df)
                
                if all_sector_scores:
                    # Combiner tous les scores
                    all_scores = pd.concat(all_sector_scores, ignore_index=True)
                    
                    # Classement SECTORIEL des émetteurs (modification ici)
                    st.subheader("🏆 Classement Sectoriel des Émetteurs")
                    
                    # Classer par secteur puis par score
                    ranked_emetteurs = all_scores.sort_values(['Secteur', 'Score_normalisé'], ascending=[True, False])
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.dataframe(
                            ranked_emetteurs[['Emmeteur', 'Secteur', 'Score_normalisé']].style.background_gradient(
                                cmap='RdYlGn', subset=['Score_normalisé']
                            ),
                            use_container_width=True
                        )
                    
                    with col2:
                        # Statistiques du portefeuille
                        avg_score = ranked_emetteurs['Score_normalisé'].mean()
                        min_score = ranked_emetteurs['Score_normalisé'].min()
                        max_score = ranked_emetteurs['Score_normalisé'].max()
                        
                        st.metric("Score Moyen", f"{avg_score:.1f}/100")
                        st.metric("Score Minimum", f"{min_score:.1f}/100")
                        st.metric("Score Maximum", f"{max_score:.1f}/100")
                    
                    # Graphique de classement par secteur
                    fig, ax = plt.subplots(figsize=(12, 8))
                    
                    # Couleur différente par secteur
                    unique_sectors = ranked_emetteurs['Secteur'].unique()
                    colors = plt.cm.Set3(np.linspace(0, 1, len(unique_sectors)))
                    color_map = dict(zip(unique_sectors, colors))
                    
                    for secteur in unique_sectors:
                        secteur_data = ranked_emetteurs[ranked_emetteurs['Secteur'] == secteur]
                        ax.barh(secteur_data['Emmeteur'], secteur_data['Score_normalisé'], 
                               color=color_map[secteur], label=secteur)
                    
                    ax.set_xlabel('Score normalisé (0-100)')
                    ax.set_title("Classement des émetteurs par secteur - AL BARID BANK")
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                    ax.set_xlim(0, 100)
                    st.pyplot(fig)
                    
                    # Analyse par secteur
                    st.subheader("📊 Analyse par Secteur")
                    
                    sector_analysis = al_barid_data.groupby('Secteur').agg({
                        'Emmeteur': 'count',
                        'ROA(%)': 'mean',
                        'ROE(%)': 'mean',
                        'Marge_operationnelle(%)': 'mean'
                    }).round(3)
                    
                    # Ajouter le score moyen par secteur
                    sector_scores = all_scores.groupby('Secteur')['Score_normalisé'].mean().round(2)
                    sector_analysis['Score moyen'] = sector_scores
                    
                    sector_analysis.columns = ['Nb Émetteurs', 'ROA(%) Moyen', 'ROE(%) Moyen', 'Marge(%) Moyenne', 'Score moyen']
                    st.dataframe(sector_analysis.style.background_gradient(cmap='RdYlGn', subset=['Score moyen']), 
                                use_container_width=True)
                    
                    # Graphique de répartition sectorielle
                    fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
                    
                    # Pie chart de répartition
                    sector_counts = al_barid_data['Secteur'].value_counts()
                    ax1.pie(sector_counts.values, labels=sector_counts.index, autopct='%1.1f%%')
                    ax1.set_title("Répartition sectorielle du portefeuille")
                    
                    # Bar chart des scores moyens par secteur
                    sector_avg_scores = all_scores.groupby('Secteur')['Score_normalisé'].mean().sort_values()
                    bars = ax2.barh(sector_avg_scores.index, sector_avg_scores.values, 
                                   color=sns.color_palette("RdYlGn", len(sector_avg_scores)))
                    ax2.set_xlabel('Score moyen')
                    ax2.set_title('Performance moyenne par secteur')
                    ax2.bar_label(bars, fmt='%.1f')
                    ax2.set_xlim(0, 100)
                    
                    st.pyplot(fig2)
                    
                    # Détails par émetteur avec scoring sectoriel
                    st.subheader("🔍 Détails par Émetteur (Avec Scoring Sectoriel)")
                    
                    selected_emetteur = st.selectbox(
                        "Sélectionnez un émetteur pour voir les détails",
                        options=ranked_emetteurs['Emmeteur'].tolist()
                    )
                    
                    if selected_emetteur in st.session_state.score_details:
                        details = st.session_state.score_details[selected_emetteur]
                        
                        # Trouver le secteur de l'émetteur
                        emetteur_secteur = al_barid_data[al_barid_data['Emmeteur'] == selected_emetteur]['Secteur'].values[0]
                        emetteur_score = ranked_emetteurs[ranked_emetteurs['Emmeteur'] == selected_emetteur]['Score_normalisé'].values[0]
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric(f"Score Global - {selected_emetteur}", f"{emetteur_score}/100")
                            st.metric("Secteur", emetteur_secteur)
                        
                        with col2:
                            # Score dans le secteur
                            secteur_scores = all_scores[all_scores['Secteur'] == emetteur_secteur]
                            secteur_avg = secteur_scores['Score_normalisé'].mean()
                            secteur_rank = secteur_scores[secteur_scores['Emmeteur'] == selected_emetteur]['Score_normalisé'].values[0]
                            secteur_position = secteur_scores[secteur_scores['Emmeteur'] == selected_emetteur].index[0] + 1
                            
                            st.metric("Score dans le secteur", f"{secteur_rank}/100")
                            st.metric("Position dans le secteur", f"{secteur_position}/{len(secteur_scores)}")
                        
                        # Détails des ratios
                        for ratio, ratio_details in details.items():
                            with st.expander(f"Ratio {ratio}", expanded=False):
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.markdown("**Méthode 1 - Seuils Sectoriels**")
                                    st.write(f"Valeur: {ratio_details['methode1']['valeur']:.4f}")
                                    st.write(f"Score: {ratio_details['methode1']['score']}/4")
                                    st.write(f"Niveau: {ratio_details['methode1']['niveau']}")
                                
                                with col2:
                                    st.markdown("**Méthode 2 - Position Relative**")
                                    st.write(f"Valeur: {ratio_details['methode2']['valeur']:.4f}")
                                    st.write(f"Score: {ratio_details['methode2']['score']:.2f}/4")
                                    st.write(f"Position: {ratio_details['methode2']['position']}")
                                    if 'classement' in ratio_details['methode2']:
                                        st.write(f"Classement: {ratio_details['methode2']['classement']}")
                                
                                with col3:
                                    st.markdown("**Score Final du Ratio**")
                                    st.metric(
                                        label=f"Score {ratio}",
                                        value=f"{ratio_details['score_final']:.2f}/4",
                                        help="Calculé comme: 60% × Score Méthode 1 + 40% × Score Méthode 2"
                                    )
                    
                    # Fonction pour générer le rapport PDF
                    def generate_pdf_report(all_scores, al_barid_data):
                        from fpdf import FPDF
                        import tempfile
                        import os
                        
                        class PDF(FPDF):
                            def header(self):
                                self.set_font('Arial', 'B', 16)
                                self.cell(0, 10, 'RAPPORT AL BARID BANK - Analyse du Portefeuille', 0, 1, 'C')
                                self.ln(5)
                            
                            def footer(self):
                                self.set_y(-15)
                                self.set_font('Arial', 'I', 8)
                                self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
                        
                        pdf = PDF()
                        pdf.add_page()
                        pdf.set_font('Arial', '', 12)
                        
                        # Informations générales
                        pdf.set_font('Arial', 'B', 14)
                        pdf.cell(0, 10, 'Résumé du Portefeuille', 0, 1)
                        pdf.set_font('Arial', '', 12)
                        
                        total_emetteurs = len(all_scores)
                        score_moyen = all_scores['Score_normalisé'].mean()
                        pdf.cell(0, 10, f'Nombre total d\'émetteurs: {total_emetteurs}', 0, 1)
                        pdf.cell(0, 10, f'Score moyen du portefeuille: {score_moyen:.2f}/100', 0, 1)
                        pdf.ln(10)
                        
                        # Détails par secteur
                        pdf.set_font('Arial', 'B', 14)
                        pdf.cell(0, 10, 'Analyse par Secteur', 0, 1)
                        pdf.set_font('Arial', '', 12)
                        
                        for secteur in all_scores['Secteur'].unique():
                            secteur_data = all_scores[all_scores['Secteur'] == secteur]
                            secteur_score = secteur_data['Score_normalisé'].mean()
                            
                            pdf.set_font('Arial', 'B', 12)
                            pdf.cell(0, 10, f'Secteur: {secteur}', 0, 1)
                            pdf.set_font('Arial', '', 12)
                            pdf.cell(0, 10, f'Nombre d\'émetteurs: {len(secteur_data)}', 0, 1)
                            pdf.cell(0, 10, f'Score moyen: {secteur_score:.2f}/100', 0, 1)
                            
                    # Classement des émetteurs dans le secteur - CORRECTION ICI
                            secteur_data_sorted = secteur_data.sort_values('Score_normalisé', ascending=False)
                            for i, (_, row) in enumerate(secteur_data_sorted.iterrows(), 1):  # Correction: secteur_data_sorted
                                pdf.cell(0, 10, f'{i}. {row["Emmeteur"]}: {row["Score_normalisé"]:.2f}/100', 0, 1)
                            
                            pdf.ln(5)
                        
                        # Détails complets de chaque émetteur
                        pdf.add_page()
                        pdf.set_font('Arial', 'B', 14)
                        pdf.cell(0, 10, 'Détails des Émetteurs', 0, 1)
                        
                        for _, emetteur in all_scores.iterrows():
                            pdf.set_font('Arial', 'B', 12)
                            pdf.cell(0, 10, f'Émetteur: {emetteur["Emmeteur"]}', 0, 1)
                            pdf.set_font('Arial', '', 10)
                            pdf.cell(0, 10, f'Secteur: {emetteur["Secteur"]}', 0, 1)
                            pdf.cell(0, 10, f'Score final: {emetteur["Score_normalisé"]:.2f}/100', 0, 1)
                            
                            # Ajouter les données financières si disponibles
                            emetteur_data = al_barid_data[al_barid_data['Emmeteur'] == emetteur['Emmeteur']]
                            if not emetteur_data.empty:
                                for col in ['ROA', 'ROE', 'Marge_operationnelle', 'GEARING']:
                                    if col in emetteur_data.columns:
                                        value = emetteur_data[col].values[0]
                                        pdf.cell(0, 10, f'{col}: {value:.2f}', 0, 1)
                            
                            pdf.ln(5)
                        
                        # Sauvegarder le PDF temporairement
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                        pdf.output(temp_file.name)
                        return temp_file.name
                    
                    # Bouton de téléchargement PDF
                    st.subheader("📄 Télécharger le Rapport Complet")
                    
                    if st.button("📥 Générer et Télécharger le Rapport PDF"):
                        with st.spinner("Génération du rapport PDF..."):
                            pdf_path = generate_pdf_report(all_scores, al_barid_data)
                            
                            with open(pdf_path, "rb") as pdf_file:
                                pdf_data = pdf_file.read()
                            
                            st.download_button(
                                label="⬇️ Télécharger le Rapport PDF",
                                data=pdf_data,
                                file_name="al_barid_bank_portfolio_analysis.pdf",
                                mime="application/pdf"
                            )
                            
                            # Nettoyer le fichier temporaire
                            os.unlink(pdf_path)
                
                else:
                    st.warning("Aucun score sectoriel disponible pour les émetteurs sélectionnés.")
            else:
                st.warning("⚠️ Aucun émetteur correspondant trouvé dans les données chargées.")
        else:
            st.info("ℹ️ Veuillez sélectionner au moins un émetteur et valider la sélection pour analyser le portefeuille.")
# Onglet 6: Export
with tab6:
    st.header("📤 Export des résultats")
    
    if 'df' not in st.session_state or st.session_state.df is None:
        st.warning("⚠️ Aucune donnée à exporter. Veuillez d'abord charger les données.")
    else:
        # Préparation des données pour export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Données complètes
            st.session_state.df.to_excel(writer, sheet_name='Donnees_completes', index=False)
            
            # Comparaison sectorielle
            if 'sector_comparison' in st.session_state:
                st.session_state.sector_comparison.to_excel(writer, sheet_name='Comparaison_sectorielle', index=False)
            
            # Données et scores du secteur sélectionné
            if 'sector_data' in st.session_state and st.session_state.sector_data is not None:
                secteur = st.session_state.selected_sector
                # Tronquer le nom du secteur pour qu'il ne dépasse pas 31 caractères
                sheet_name = f'Donnees_{secteur}'[:31]
                sector_df = st.session_state.sector_data
                scores_df = calculate_final_score(sector_df)
                
                # Feuille de détail du secteur
                sector_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Feuille de scores du secteur (tronquée également)
                scores_sheet_name = f'Scores_{secteur}'[:31]
                scores_df.to_excel(writer, sheet_name=scores_sheet_name, index=False)
            
            # Données bancaires si disponibles
            if st.session_state.banking_data is not None:
                banking_scores = calculate_final_score(st.session_state.banking_data, "bancaire")
                
                st.session_state.banking_data.to_excel(writer, sheet_name='Donnees_Bancaires', index=False)
                banking_scores.to_excel(writer, sheet_name='Scores_Bancaires', index=False)
            
            # Données AL BARID BANK
            if st.session_state.al_barid_selection:
                al_barid_data = st.session_state.df[st.session_state.df['Emmeteur'].isin(st.session_state.al_barid_selection)]
                if not al_barid_data.empty:
                    al_barid_scores = calculate_final_score(al_barid_data)
                    
                    al_barid_data.to_excel(writer, sheet_name='AL_BARID_Donnees', index=False)
                    al_barid_scores.to_excel(writer, sheet_name='AL_BARID_Scores', index=False)
        
        output.seek(0)
        
        st.download_button(
            label="📥 Télécharger les résultats Excel",
            data=output,
            file_name="resultats_scoring.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # Résumé des exportations
        st.subheader("Contenu du fichier exporté")
        st.markdown("""
        - 📋 **Donnees_completes** : Toutes les données financières avec ratios calculés
        - 📊 **Comparaison_sectorielle** : Scores moyens par secteur
        - 🎯 **Donnees_[Secteur]** : Données détaillées du secteur sélectionné
        - 🎯 **Scores_[Secteur]** : Scores détaillés du secteur sélectionné
        - 🏦 **Donnees_Bancaires** : Données des banques
        - 🏦 **Scores_Bancaires** : Scores des banques
        - 🏦 **AL_BARID_Donnees** : Données des émetteurs AL BARID BANK
        - 🏦 **AL_BARID_Scores** : Scores des émetteurs AL BARID BANK
        """)

