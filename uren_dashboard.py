# 📊 Urenanalyse Dashboard met filters, tijdaggregatie en AI-chatbox

import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI 
import os
from pandasai import SmartDataframe

# --- Configuratie ---
st.set_page_config(page_title="Urenanalyse Dashboard", layout="wide")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Raleway&display=swap');
        html, body, [class*="css"]  {
            background-color: #FFFFF4;
            color: #20423C;
            font-family: 'Raleway', sans-serif;
        }
        .stButton>button {
            background-color: #83AF9A;
            color: #20423C;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
            color: #20423C;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Urenanalyse Dashboard")

# --- Upload ---
uploaded_file = st.file_uploader("📂 Upload een Excel-bestand", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine="openpyxl")

    # --- Datumbewerking ---
    if "Begindatum" in df.columns:
        df["Begindatum"] = pd.to_datetime(df["Begindatum"], errors="coerce")
        df = df.dropna(subset=["Begindatum"])
        df["Jaar"] = df["Begindatum"].dt.year
        df["Maand"] = df["Begindatum"].dt.to_period("M").astype(str)
        df["Week"] = df["Begindatum"].dt.to_period("W").astype(str)
        df["Kwartaal"] = df["Begindatum"].dt.to_period("Q").astype(str)
    else:
        st.error("Kolom 'Begindatum' ontbreekt.")

    # --- Sidebar filters ---
    st.sidebar.header("🔎 Filters")
    omzetgroepen = df["Omzetgroep"].dropna().unique()
    selected_omzetgroep = st.sidebar.multiselect("Selecteer omzetgroep", omzetgroepen, default=list(omzetgroepen))

    datum_opties = ["Dit jaar", "Vorig jaar", "Dit kwartaal", "Deze maand", "Vorige maand"]
    periode_optie = st.sidebar.selectbox("Snelfilter periode", datum_opties)

    tijd_aggregatie = st.sidebar.radio("Weergave per", ["Week", "Maand", "Kwartaal", "Jaar"], horizontal=True)

    df = df[df["Omzetgroep"].isin(selected_omzetgroep)]

    vandaag = pd.Timestamp.today()
    if periode_optie == "Dit jaar":
        df = df[df["Begindatum"].dt.year == vandaag.year]
    elif periode_optie == "Vorig jaar":
        df = df[df["Begindatum"].dt.year == vandaag.year - 1]
    elif periode_optie == "Deze maand":
        df = df[df["Begindatum"].dt.month == vandaag.month]
    elif periode_optie == "Vorige maand":
        df = df[df["Begindatum"].dt.month == vandaag.month - 1]
    elif periode_optie == "Dit kwartaal":
        kwartaal = (vandaag.month - 1) // 3 + 1
        df = df[df["Begindatum"].dt.quarter == kwartaal]

    # --- Tijdsaggregatie selectie ---
    periode_kolom = tijd_aggregatie
    if tijd_aggregatie == "Maand":
        df["Periode"] = df["Maand"]
    elif tijd_aggregatie == "Week":
        df["Periode"] = df["Week"]
    elif tijd_aggregatie == "Kwartaal":
        df["Periode"] = df["Kwartaal"]
    elif tijd_aggregatie == "Jaar":
        df["Periode"] = df["Jaar"].astype(str)

    # --- Layout: 2 kolommen ---
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("📈 Kies een grafiek")
        chart_option = st.radio("", [
            "Omzet per periode",
            "Uren per urensoort",
            "Gefactureerd per klant",
            "Resultaat per project",
            "Declarabiliteit per medewerker",
            "Productiviteit per team",
            "Gemiddeld uurtarief per medewerker",
            "Brutomarge per project"
        ])

    with col2:
        st.subheader(f"📊 {chart_option}")

        fig = None
        if chart_option == "Omzet per periode":
            data = df.groupby("Periode")["Totaal na correctie"].sum().reset_index()
            fig = px.line(data, x="Periode", y="Totaal na correctie", title="Omzet per periode")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Uren per urensoort":
            data = df.groupby(["Periode", "Urensoort"])["Aantal"].sum().reset_index()
            fig = px.bar(data, x="Periode", y="Aantal", color="Urensoort", title="Uren per urensoort")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Gefactureerd per klant":
            data = df.groupby("Bedrijf/Contactpersoon")["Gefactureerd"].sum().reset_index().sort_values(by="Gefactureerd", ascending=False)
            fig = px.bar(data, x="Bedrijf/Contactpersoon", y="Gefactureerd", title="Gefactureerd per klant")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Resultaat per project":
            df["Resultaat"] = df["Totaal na correctie"] - df["Kostprijs"]
            data = df.groupby("Project")["Resultaat"].sum().reset_index()
            fig = px.bar(data, x="Project", y="Resultaat", title="Resultaat per project")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Declarabiliteit per medewerker":
            declarabel = df[df["Factureerbaar"] == True]
            data = declarabel.groupby("Medewerker")["Aantal"].sum() / df.groupby("Medewerker")["Aantal"].sum()
            data = data.reset_index(name="Declarabiliteit")
            fig = px.bar(data, x="Medewerker", y="Declarabiliteit", title="Declarabiliteit (%)")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Productiviteit per team":
            if "Dienst" in df.columns:
                data = df.groupby("Dienst")["Aantal"].sum().reset_index()
                fig = px.pie(data, names="Dienst", values="Aantal", title="Uren per dienst")
                st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Gemiddeld uurtarief per medewerker":
            df["Gerealiseerd tarief"] = df["Totaal na correctie"] / df["Aantal"]
            data = df.groupby("Medewerker")["Gerealiseerd tarief"].mean().reset_index()
            fig = px.bar(data, x="Medewerker", y="Gerealiseerd tarief", title="Gemiddeld uurtarief")
            st.plotly_chart(fig, use_container_width=True)

        elif chart_option == "Brutomarge per project":
            df["Marge"] = (df["Totaal na correctie"] - df["Kostprijs"]) / df["Totaal na correctie"]
            data = df.groupby("Project")["Marge"].mean().reset_index()
            fig = px.bar(data, x="Project", y="Marge", title="Brutomarge per project")
            st.plotly_chart(fig, use_container_width=True)

else:
    st.info("📂 Upload een Excel-bestand om te beginnen.")
    
    # --- AI Chatbox met PandasAI ---
st.subheader("🤖 AI-vraag over je data")
vraag = st.text_input("Stel hier je vraag over de dataset (bijv. 'Welke maand had de meeste omzet?')")

if vraag:
    import openai
    
    openai.api_key = os.getenv("OPENAI_API_KEY")


    if not openai_api_key:
        st.warning("API-sleutel niet gevonden. Zet OPENAI_API_KEY als omgevingsvariabele.")
    else:
        client = OpenAI(api_key=openai_api_key)

        with st.spinner("AI is je vraag aan het analyseren..."):
            try:
                kolommen = [
                    "Begindatum", "Jaar", "Maand", "Week", "Kwartaal",
                    "Omzetgroep", "Totaal na correctie", "Aantal", "Project",
                    "Medewerker", "Urensoort", "Gefactureerd", "Kostprijs", "Factureerbaar"
                ]
                df_klein = df[kolommen].dropna().sample(min(50, len(df))).copy()
                tabel_str = df_klein.to_csv(index=False)

                prompt = f"""
Je bent een data-analist. Beantwoord de volgende vraag over de dataset die ik je geef. Geef je antwoord in duidelijke, simpele taal voor een niet-technisch publiek. 

Vraag: {vraag}

Dataset (CSV):
{tabel_str}
"""

                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )

                antwoord = response.choices[0].message.content
                st.success("AI Antwoord:")
                st.markdown(antwoord)

            except Exception as e:
                st.error(f"Er ging iets mis bij het uitvoeren van de AI-analyse:\n\n{str(e)}")



