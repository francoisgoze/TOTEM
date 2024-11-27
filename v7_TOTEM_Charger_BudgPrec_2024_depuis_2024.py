import streamlit as st
import xml.etree.ElementTree as ET
from io import StringIO, BytesIO
import os
from collections import defaultdict
import streamlit.components.v1 as components  # Import du module pour les composants HTML personnalisés



#v1 : on charge les fichiers, on analyse les différences, si le compte 2024 n'est pas mappé il peut être mappé automatiquement et alimenté le montant BudgPrev de 2025
#     limite : si le compte n'es pas mappé on ne crée pas une nouvelle entrée.
#v6 : on corrige correctement le fichier xml, aussi bien les lignes mappées automatiquement que les lignes avec une correction dans l'ihm
#     limite : pour les lignes sans correction on affiche dans la page web les lignes à reporter dans le xml à la main 
#v7 : on s'améliore le xml à ajouter peut etre récupérer par un bouton copier, il suffit de le coller ensuite dans le fichier xml.
#
#
#



import xml.etree.ElementTree as ET

def remove_namespace_from_tree(element):

    # Si l'élément a un namespace, on l'enlève
    if '}' in element.tag:
        element.tag = element.tag.split('}', 1)[1]  # Supprime le namespace dans la balise

    # Récurse sur tous les enfants
    for child in element:
        remove_namespace_from_tree(child)  # Appliquer la même suppression sur les enfants

    
    
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
st.title("Application de correction des fichiers TOTEM du Budget 2025 pour charger les crédits 2024 en tant que Budget précédent")

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
        #if unmatched_lines_2025:
        #    st.warning("Lignes Budgétaires 2025 non trouvées dans le budget 2024 :")
        #    for line, cred_ouv in unmatched_lines_2025:
        #        st.write(f"Nature: {line[0]}, ContNat: {line[1]}, CredOuv: {cred_ouv}")

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

        # Après que l'utilisateur ait appliqué les corrections
        ns = {'': 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire'}
        ET.register_namespace('', 'http://www.minefi.gouv.fr/cp/demat/docbudgetaire')
        
        # Initialiser st.session_state.corrections si nécessaire
        if 'corrections' not in st.session_state:
            st.session_state.corrections = {}
    
        # Fonction pour afficher les lignes non utilisées de 2024 sans nouvelle nature
        if st.button("Afficher les lignes non utilisées de 2024"):
            if unmatched_lines_2024:
                st.subheader("Lignes Budgétaires 2024 non utilisées dans 2025")
                
                # Stocker toutes les lignes XML dans une variable pour export
                all_xml_lines = []
                
                # Filtrer les lignes pour ne garder que celles qui n'ont pas été corrigées (sans nouvelle nature)
                for line, cred_ouv in unmatched_lines_2024:
                    # Vérifier si cette ligne a une correction appliquée (nouvelle nature)
                    if (line not in st.session_state.corrections):
                        # Si la ligne n'a pas été corrigée, afficher la ligne correspondante
                        for ligne in root_2024.findall('.//LigneBudget', ns):
                            ligne_nature = ligne.find('Nature', ns).attrib['V']
                            ligne_contnat = ligne.find('ContNat', ns).attrib['V']
                            
                            # Si cette ligne correspond à celle qui n'a pas été corrigée
                            if (ligne_nature, ligne_contnat) == line:
                                # Supprimer le namespace dans la ligne
                                remove_namespace_from_tree(ligne)
                                
                                # Trouver la balise <CredOuv> et vérifier son existence, mettre sa valeur à 0
                                cred_ouv_elem = ligne.find('CredOuv')
                                if cred_ouv_elem is not None:
                                    cred_ouv_value = cred_ouv_elem.attrib['V']
                                    cred_ouv_elem.attrib['V'] = "0"

                                    # Remplacer la valeur de <MtBudgPrec> par celle de <CredOuv>
                                    mtbudgprec_elem = ligne.find('MtBudgPrec')
                                    if mtbudgprec_elem is not None:
                                        mtbudgprec_elem.attrib['V'] = cred_ouv_value
                                        
                                # Trouver la balise <MtRARPrec> et vérifier son existence, mettre sa valeur à 0
                                rar_prec_elem = ligne.find('MtRARPrec')
                                if rar_prec_elem is not None:
                                    rar_prec_elem.attrib['V'] = "0"
                                    
                                # Trouver la balise <MtPropNouv> et vérifier son existence, mettre sa valeur à 0
                                prop_nouv_elem = ligne.find('MtPropNouv')
                                if prop_nouv_elem is not None:
                                    prop_nouv_elem.attrib['V'] = "0"
                                    
                                # Trouver la balise <MtPropNouv> et vérifier son existence, mettre sa valeur à 0
                                prev_elem = ligne.find('MtPrev')
                                if prev_elem is not None:
                                    prev_elem.attrib['V'] = "0"

                                # Convertir la ligne nettoyée en chaîne et afficher
                                xml_string = ET.tostring(ligne, encoding='unicode')
                                all_xml_lines.append(xml_string)
                                #st.text(xml_string)
                                
                # Joindre toutes les lignes en un seul bloc XML
                full_xml_content = "\n".join(all_xml_lines) 

                # Afficher un bouton pour copier le XML dans le presse-papiers
                st.code(full_xml_content, language="xml")

                # Ajouter du JavaScript pour copier le contenu
                copy_js = f"""
                <script>
                function copyToClipboard() {{
                    const content = `{full_xml_content}`;
                    navigator.clipboard.writeText(content).then(() => {{
                        alert("Contenu copié dans le presse-papiers !");
                    }}).catch(err => {{
                        console.error("Échec de la copie : ", err);
                    }});
                }}
                </script>
                <button onclick="copyToClipboard()">Copier dans le presse-papiers</button>
                """
                components.html(copy_js, height=40)
                
            else:
                st.warning("Aucune ligne non utilisée trouvée.")


        # Télécharger le fichier modifié
        modified_xml, new_filename = save_xml(st.session_state.modified_tree_2025, filename_2025)
        st.download_button(
            label=f"Télécharger {new_filename}",
            data=modified_xml,
            file_name=new_filename,
            mime="application/xml"
        )