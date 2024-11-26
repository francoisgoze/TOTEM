import streamlit as st
import xml.etree.ElementTree as ET
from io import StringIO, BytesIO

# Fonction pour charger et parser un fichier XML
def parse_xml(uploaded_file):
    if uploaded_file is not None:
        try:
            tree = ET.parse(uploaded_file)
            root = tree.getroot()
            return tree, root
        except ET.ParseError as e:
            st.error(f"Erreur de parsing du fichier XML : {e}")
    return None, None

# Fonction pour créer un nouveau fichier XML modifié
def create_modified_2025(tree_2024, root_2024, tree_2025, root_2025):
    ns = {'ns': 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire'}
    ligne_2024 = {
        (ligne.find('ns:Nature', ns).attrib['V'], ligne.find('ns:ContNat', ns).attrib['V']): ligne.find('ns:CredOuv', ns).attrib['V']
        for ligne in root_2024.findall('.//ns:LigneBudget', ns)
    }

    unmatched_lines = []

    for ligne in root_2025.findall('.//ns:LigneBudget', ns):
        key = (
            ligne.find('ns:Nature', ns).attrib['V'],
            ligne.find('ns:ContNat', ns).attrib['V']
        )
        if key in ligne_2024:
            ligne.find('ns:MtBudgPrec', ns).attrib['V'] = ligne_2024[key]
        else:
            unmatched_lines.append(key)

    return tree_2025, unmatched_lines

# Fonction pour sauvegarder un fichier XML modifié
def save_xml(tree):
    xml_bytes = BytesIO()
    tree.write(xml_bytes, encoding='utf-8', xml_declaration=True)
    return xml_bytes.getvalue()

# Interface principale
st.title("Application de Gestion Budgétaire")

st.header("Charger les fichiers XML")

uploaded_file_2024 = st.file_uploader("Charger le fichier XML 2024", type="xml")
uploaded_file_2025 = st.file_uploader("Charger le fichier XML 2025", type="xml")

if uploaded_file_2024 and uploaded_file_2025:
    tree_2024, root_2024 = parse_xml(uploaded_file_2024)
    tree_2025, root_2025 = parse_xml(uploaded_file_2025)

    if tree_2024 and root_2024 and tree_2025 and root_2025:
        st.success("Les fichiers XML ont été chargés avec succès.")

        if st.button("Générer le fichier XML 2025 modifié"):
            modified_tree_2025, unmatched_lines = create_modified_2025(tree_2024, root_2024, tree_2025, root_2025)

            if unmatched_lines:
                st.warning("Certaines lignes du fichier 2024 n'ont pas été rapprochées :")
                for line in unmatched_lines:
                    st.write(f"Nature: {line[0]}, ContNat: {line[1]}")

            modified_xml = save_xml(modified_tree_2025)
            st.download_button(
                label="Télécharger le fichier XML 2025 modifié",
                data=modified_xml,
                file_name="fichier_2025_modifie.xml",
                mime="application/xml"
            )
