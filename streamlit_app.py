import streamlit as st
from naw_tools import guerre
def RC():
    st.title("Analyse de RC")


    RC = st.text_area("Copiez le RC ici.")

    if not RC:
        st.stop()

    armies_avant, armies_apres, niveaux = guerre.parseRC(rc=RC)

    col1, col2 = st.columns(2)

    with col1:
        st.table(niveaux["Attaquant"])
        st.table(armies_avant["Attaquant"])
        st.table(armies_apres["Attaquant"])

    with col2:
        st.table(niveaux["Defenseur"])
        st.table(armies_avant["Defenseur"])
        st.table(armies_apres["Defenseur"])


with st.sidebar:
    page = st.selectbox("Choix d'outil.", ("Analyse RC", "Simulateur de combat"))

if page == "Analyse RC":
    RC()
elif page == "Simulateur de combat":
    pass

