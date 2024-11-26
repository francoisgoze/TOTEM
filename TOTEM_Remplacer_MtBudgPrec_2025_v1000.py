import streamlit as st
import xml.etree.ElementTree as ET
from io import StringIO, BytesIO
import os
from collections import defaultdict

# Fonction pour charger et parser un fichier XML
def parse_xml(uploaded_file):
    if uploaded_file is not None:
        try:
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            return tree, root, uploaded_file.name
        except ET.ParseError as e:
            st.error(f"Erreur de parsing du fichier XML : {e}")
    return None, None, None

# Fonction pour créer un nouveau fichier XML modifié
def create_modified_2025(tree_2024, root_2024, tree_2025, root_2025):
    ns = {'': 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire'}  # Gérer sans préfixe explicite
    ET.register_namespace('', 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire')

    ligne_2024 = {
        (ligne.find('Nature', ns).attrib['V'], ligne.find('ContNat', ns).attrib['V']): float(ligne.find('CredOuv', ns).attrib['V'])
        for ligne in root_2024.findall('.//LigneBudget', ns)
    }

    unmatched_lines_2025 = []
    matched_keys_2024 = set()

    for ligne in root_2025.findall('.//LigneBudget', ns):
        key = (
            ligne.find('Nature', ns).attrib['V'],
            ligne.find('ContNat', ns).attrib['V']
        )
        if key in ligne_2024:
            ligne.find('MtBudgPrec', ns).attrib['V'] = str(ligne_2024[key])
            matched_keys_2024.add(key)
        else:
            unmatched_lines_2025.append((key, ligne.find('CredOuv', ns).attrib['V']))

    unmatched_lines_2024 = [(key, cred_ouv) for key, cred_ouv in ligne_2024.items() if key not in matched_keys_2024]

    return tree_2025, unmatched_lines_2025, unmatched_lines_2024

# Fonction pour appliquer les corrections et sommer les valeurs
def apply_corrections_to_2025(tree_2025, unmatched_lines_2024, corrections):
    ns = {'': 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire'}
    summed_values = defaultdict(float)

    for (nature, contnat), cred_ouv in unmatched_lines_2024:
        if (nature, contnat) in corrections:
            corrected_nature = corrections[(nature, contnat)]
            summed_values[(corrected_nature, contnat)] += cred_ouv

    for (corrected_nature, contnat), total_cred_ouv in summed_values.items():
        for ligne in tree_2025.getroot().findall('.//LigneBudget', ns):
            ligne_nature = ligne.find('Nature', ns).attrib['V']
            ligne_contnat = ligne.find('ContNat', ns).attrib['V']

            if ligne_nature == corrected_nature and ligne_contnat == contnat:
                current_value = float(ligne.find('MtBudgPrec', ns).attrib['V'])
                ligne.find('MtBudgPrec', ns).attrib['V'] = str(current_value + total_cred_ouv)

    return tree_2025

# Fonction pour sauvegarder un fichier XML modifié dans le même répertoire que la source
def save_xml(tree, original_filename):
    base_name, _ = os.path.splitext(original_filename)
    new_filename = f"{base_name}_ajout_MtBudgPrec.xml"
    xml_bytes = BytesIO()
    tree.write(xml_bytes, encoding='utf-8', xml_declaration=True)
    return xml_bytes.getvalue(), new_filename

# Interface principale
st.title("Application de Gestion Budgétaire")

st.header("Charger les fichiers XML")

uploaded_file_2024 = st.file_uploader("Charger le fichier XML 2024", type="xml")
uploaded_file_2025 = st.file_uploader("Charger le fichier XML 2025", type="xml")

if uploaded_file_2024 is not None and uploaded_file_2025 is not None:
    tree_2024, root_2024, filename_2024 = parse_xml(uploaded_file_2024)
    tree_2025, root_2025, filename_2025 = parse_xml(uploaded_file_2025)

    if tree_2024 is not None and root_2024 is not None and tree_2025 is not None and root_2025 is not None:
        st.success("Les fichiers XML ont été chargés avec succès.")

        if "unmatched_lines_2024" not in st.session_state:
            modified_tree_2025, unmatched_lines_2025, unmatched_lines_2024 = create_modified_2025(tree_2024, root_2024, tree_2025, root_2025)
            st.session_state.unmatched_lines_2024 = unmatched_lines_2024
            st.session_state.unmatched_lines_2025 = unmatched_lines_2025
            st.session_state.modified_tree_2025 = modified_tree_2025

        unmatched_lines_2024 = st.session_state.unmatched_lines_2024
        unmatched_lines_2025 = st.session_state.unmatched_lines_2025

        st.subheader("Liste des anomalies")

        # Afficher les anomalies 2025
        if unmatched_lines_2025:
            st.warning("Lignes Budgétaires 2025 non trouvées dans le budget 2024 :")
            for line, cred_ouv in unmatched_lines_2025:
                st.write(f"Nature: {line[0]}, ContNat: {line[1]}, CredOuv: {cred_ouv}")

        # Afficher les anomalies 2024
        if unmatched_lines_2024:
            st.warning("Lignes Budgétaires 2024 non trouvées dans le budget 2025 :")
            for line, cred_ouv in unmatched_lines_2024:
                st.write(f"Nature: {line[0]}, ContNat: {line[1]}, CredOuv: {cred_ouv}")

            st.subheader("Proposer une correspondance pour les lignes de 2024 non rapprochées")

            # Extraire les natures disponibles dans le fichier 2025
            available_natures = sorted({
                ligne.find('Nature', {'': 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire'}).attrib['V']
                for ligne in root_2025.findall('.//LigneBudget', {'': 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire'})
            })

            corrections = {}
            for i, (line, cred_ouv) in enumerate(unmatched_lines_2024):
                # Proposer une correspondance par défaut
                default_suggestion = ""
                for nature in available_natures:
                    if line[0].startswith(nature):
                        default_suggestion = nature
                        break

                st.write(f"Nature: {line[0]}, ContNat: {line[1]}, CredOuv: {cred_ouv}")
                new_nature = st.selectbox(
                    f"Nouvelle Nature pour Nature {line[0]} et ContNat {line[1]}",
                    options=[""] + available_natures,
                    index=([""] + available_natures).index(default_suggestion) if default_suggestion else 0,
                    key=f"new_nature_{i}"
                )
                if new_nature:
                    corrections[(line[0], line[1])] = new_nature

            if st.button("Appliquer les corrections"):
                st.session_state.corrections = corrections
                st.session_state.modified_tree_2025 = apply_corrections_to_2025(
                    st.session_state.modified_tree_2025,
                    unmatched_lines_2024,
                    corrections
                )
                st.success("Corrections appliquées au fichier 2025.")

        # Télécharger le fichier modifié
        modified_xml, new_filename = save_xml(st.session_state.modified_tree_2025, filename_2025)
        st.download_button(
            label=f"Télécharger {new_filename}",
            data=modified_xml,
            file_name=new_filename,
            mime="application/xml"
        )
