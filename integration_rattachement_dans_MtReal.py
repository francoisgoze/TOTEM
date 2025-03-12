import xml.etree.ElementTree as ET
import streamlit as st
import os
import time

def modifier_xml(fichier_entree, fichier_sortie):
    # Charger le fichier XML
    tree = ET.parse(fichier_entree)
    root = tree.getroot()

    # Définir l'espace de noms principal
    namespace = "http://www.minefi.gouv.fr/cp/demat/docbudgetaire"
    
    # Trouver et modifier chaque élément LigneBudget
    for ligne_budget in root.findall(".//{" + namespace + "}LigneBudget"):
        mt_real = ligne_budget.find("{" + namespace + "}MtReal")
        mt_sup = ligne_budget.find("{" + namespace + "}MtSup")
        
        if mt_real is not None and mt_sup is not None:
            # Convertir les valeurs et les additionner
            mt_real_value = float(mt_real.get("V"))
            mt_sup_value = float(mt_sup.get("V"))
            mt_real.set("V", f"{mt_real_value + mt_sup_value:.8f}")

    # Supprimer les préfixes de l'espace de noms
    for elem in root.iter():
        if elem.tag.startswith("{"):
            elem.tag = elem.tag.split("}", 1)[1]  # Enlever le namespace
    
    # Restaurer la déclaration de l'espace de noms sur la racine
    root.set("xmlns", namespace)
    root.set("xmlns:ns2", "http://www.w3.org/2000/09/xmldsig#")
    
    # Sauvegarder le fichier modifié
    tree.write(fichier_sortie, encoding="utf-8", xml_declaration=True)
    return fichier_sortie

# Interface Streamlit
st.title("Modification de Fichier XML TOTEM de CA pour ajouter les rattachements à la balise MtReal")

uploaded_file = st.file_uploader("Choisissez un fichier XML", type=["xml"])

if uploaded_file is not None:
    file_name = uploaded_file.name if uploaded_file.name else f"fichier_{int(time.time())}"  # Générer un nom si inexistant
    file_name = os.path.splitext(file_name)[0]  # Récupérer le nom sans extension
    output_file = f"{file_name}_corrigé.xml"  # Ajouter le suffixe _corrigé
    
    with open("temp.xml", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    modified_file = modifier_xml("temp.xml", output_file)
    
    with open(modified_file, "rb") as f:
        st.download_button("Télécharger le fichier modifié", f, file_name=output_file, mime="application/xml")