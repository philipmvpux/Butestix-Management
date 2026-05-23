
import sys
import subprocess
import pandas as pd
import streamlit as st

from database import engine

# ── Konstanten ───────────────────────────────────────────────

GESELLSCHAFTSFORMEN = ["Einzelunternehmen","e.K.","GbR","OHG","KG","GmbH","UG","AG"]
EINHEITEN = ["stk","m","m²","m³","kg","t","l"]
GGG = ["Gemietet","Gekauft","Geliehen"]

ROLLEN = [
    "-","Abbrucharbeiter","Abrechner (Bau)","Abteilungsleiter","Anlagenmechaniker SHK",
    "Architekt","Arbeitsvorbereiter","Ausbilder (Handwerk)","Auszubildender",
    "Bauaufseher (Bauüberwacher)","Baucontroller","Baugeräteführer","Bauhelfer",
    "Bauhofleiter","Bauingenieur","Baukalkulator","Baukaufmann/-frau","Bauleiter",
    "Bauleitungsassistent","Baulogistiker","Baumaschinenführer","Baustellenkoordinator",
    "Baustellenleiter","Baustellenlogistiker","Bauüberwacher","Bauzeichner","Betonbauer",
    "Betriebsleiter","Betriebswirt (Bau)","BIM-Koordinator","BIM-Manager","Bodenleger",
    "Buchhalter","CAD-Zeichner","Controller","Dachdecker","Disponent","Einkäufer",
    "Elektriker","Elektroniker für Energie- und Gebäudetechnik","Elektrohelfer",
    "Elektromeister","Energieberater","Energieeffizienz-Experte","Estrichleger",
    "Facility-Manager (Bau)","Fliesenleger","Fuhrparkleiter","Gerüstbauer","Geschäftsführer",
    "Geselle","HR/Personalreferent","IT-Administrator","Kalkulator","Kaufmännischer Leiter",
    "Klimatechniker","Kranführer","Kundendienstleiter","Kundendienstmonteur","Lagerist",
    "Leiter Einkauf","Leiter Kalkulation","LKW-Fahrer","Maler und Lackierer","Maschinist",
    "Maurer","Meister","Metallbauer","Monteur","Oberbauleiter","Obermonteur","Oberpolier",
    "Parkettleger","Polier","Praktikant","Projektassistenz","Projektcontroller",
    "Projektkaufmann/-frau","Projektleiter","Projektsteuerer (Bau)","Prokurist",
    "Qualitätsbeauftragter","Qualitätsmanager","Rohrleitungsbauer","Sanierungsfacharbeiter",
    "Sanitärmonteur","Schlosser","Schreiner/Tischler","Servicetechniker","SHK-Meister",
    "SiGeKo (Sicherheits- und Gesundheitsschutzkoordinator)","Sicherheitsbeauftragter",
    "Statiker","Straßenbauer","Stuckateur","Teamleiter","Techniker","TGA-Planer",
    "Tiefbaufacharbeiter","Trockenbauer","Umweltbeauftragter","Vermessungstechniker",
    "Vorarbeiter","Werkstudent","Zimmerer",
]

wetter_optionen = [
    "bedeckt","bewölkt","dunstig","diesig","eisig","feucht","frostig","gewittrig","grau",
    "hagelnd","heiß","klar","kühl","mild","neblig","nieselig","nasskalt","regnerisch",
    "schauerartig","schneebedeckt","schneefall","schwül","sonnig","stark bewölkt",
    "stark windig","starkregen","stürmisch","südwind","tauend","tiefdruck","trüb",
    "trockenkalt","tropisch","unauffällig","unbeständig","unstet","warm","wechselhaft",
    "wehend","windig","wolkenlos","wolkig","zugig","-",
]

boden_optionen = [
    "ausgetrocknet","bewachsen","bewachsen mit Stoppeln","blättrig",
    "bodenbedeckt (z.B. Mulch)","bröckelig","durchnässt","eisig","fest","feucht",
    "frisch bearbeitet","gefrozen","grasbewachsen","hart","hartgefroren","humos",
    "instabil","klebrig","kompakt","krustig","leicht feucht","lehmig","locker",
    "locker-krümelig","mehlige","mineralisch","moosig","matschig","mit Reif bedeckt",
    "mit Unkraut bedeckt","mit Wurzeln durchzogen","nadlebedeckt","nass","organisch",
    "plastisch","plastisch-klebrig","pulvrig","rissig","rutschig","sandig","schmierig",
    "schneebedeckt","sumpfig","staubig","steinig","tonig","torfig","triefend","trocken",
    "überschwemmt","uneben","vereist","verdichtet","weich","wurzeldurchzogen","-",
]

# ── Paketinstallation ────────────────────────────────────────

def install(package: str):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# ── Gecachte DB-Lookups ──────────────────────────────────────

@st.cache_data(ttl=600)
def get_projekt_name(projekt_id) -> str:
    df = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(projekt_id,))
    return df["name"].iloc[0] if not df.empty else "Unbekannt"

@st.cache_data(ttl=600)
def get_all_mitarbeiter() -> pd.DataFrame:
    return pd.read_sql("SELECT benutzername, vorname, nachname, rolle FROM mitarbeiter", engine)

@st.cache_data(ttl=300)
def get_mitarbeiter_by_project(projekt_id, user) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT benutzername FROM mitarbeiter_projekte WHERE projekt_id = %s",
        engine, params=(projekt_id,)
    )

@st.cache_data(ttl=600)
def get_materialien_for_project(projekt_id, user) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT material, menge, einheit FROM materialien WHERE projekt_id = %s AND benutzername = %s",
        engine, params=(projekt_id, user)
    )

# ── Firmendaten ──────────────────────────────────────────────

def lade_firmendaten():
    user   = st.session_state.get("user")
    result = pd.read_sql("SELECT * FROM firmenprofil WHERE benutzername = %s", engine, params=(user,))

    def _get(col, fallback=""):
        if col in result.columns and not result.empty:
            val = result[col].iloc[0]
            return val if pd.notnull(val) else fallback
        return fallback

    if not result.empty:
        st.session_state.firmenname              = _get("firmenname")
        st.session_state.firmenadresse           = _get("adresse")
        st.session_state.firmentelefon           = _get("telefon")
        st.session_state.firmenfax               = _get("fax")
        st.session_state.gesellschaftsform       = _get("gesellschaftsform", GESELLSCHAFTSFORMEN[0])
        st.session_state.iban                    = _get("iban")
        st.session_state.bic                     = _get("bic")
        st.session_state.bankname                = _get("bankname")
        st.session_state.registergericht         = _get("registergericht")
        st.session_state.hrb_nummer              = _get("hrb_nummer")
        st.session_state.geschaeftsfuehrer       = _get("geschaeftsfuehrer")
        st.session_state.ustidnr                 = _get("ustidnr")
        rn = _get("rechnungsnummer", None)
        st.session_state.standard_rechnungsnummer = int(rn) if rn is not None else 100
    else:
        st.session_state.firmenname              = ""
        st.session_state.firmenadresse           = ""
        st.session_state.firmentelefon           = ""
        st.session_state.firmenfax               = ""
        st.session_state.gesellschaftsform       = GESELLSCHAFTSFORMEN[0]
        st.session_state.iban                    = ""
        st.session_state.bic                     = ""
        st.session_state.bankname                = ""
        st.session_state.registergericht         = ""
        st.session_state.hrb_nummer              = ""
        st.session_state.geschaeftsfuehrer       = ""
        st.session_state.ustidnr                 = ""
        st.session_state.standard_rechnungsnummer = 100

def sync_materialien():
    user        = st.session_state.get("user")
    projekte    = pd.read_sql("SELECT id FROM projekte", engine)
    materialien = pd.read_sql("SELECT material, einheit FROM lagerbestand", engine)
    for _, projekt in projekte.iterrows():
        for _, mat in materialien.iterrows():
            try:
                with engine.begin() as conn:
                    conn.exec_driver_sql(
                        "INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit) VALUES (%s,%s,0,%s,%s)",
                        (int(projekt["id"]), mat["material"], user, mat["einheit"])
                    )
            except Exception:
                pass

# ── AGB & Datenschutz ────────────────────────────────────────

def load_agb() -> str:
    try:
        with open("AGB.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "AGB konnten nicht geladen werden. Bitte kontaktieren Sie den Support."

def load_datenschutz() -> str:
    try:
        with open("DATENSCHUTZ.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Datenschutzerklärung konnte nicht geladen werden. Bitte kontaktieren Sie den Support."

def _scrollbox(content: str):
    st.markdown(
        f"""<div style="height:400px;overflow-y:scroll;border:1px solid #ddd;
        padding:15px;border-radius:5px;background-color:#f9f9f9;">
        {content.replace(chr(10),"<br>")}
        </div>""",
        unsafe_allow_html=True,
    )

def show_agb_with_scrollbar():
    _scrollbox(load_agb())

def show_datenschutz_with_scrollbar():
    _scrollbox(load_datenschutz())
