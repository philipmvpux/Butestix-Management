# ============================================================
#  pages/lohnabrechnung.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.lohnabrechnung import lohnabrechnung_page
# ============================================================

import time
import textwrap
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta, time as datetime_time
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
    load_agb, load_datenschutz,
    show_agb_with_scrollbar, show_datenschutz_with_scrollbar,
)
from ui.login import hash_password, verify_password
from ui.archiv import (
    save_bericht_daten_to_archive, load_bericht_daten_from_archive,
    save_pdf_to_archive, load_pdf_from_archive,
)
from ui.pdf_generator import (
    generate_invoice_pdf_v2, generate_pauschal_invoice_pdf,
    generate_fortschritt_pdf, markdown_to_pdf,
)

def lohnabrechnung_page():
    import calendar
    aktuelles_jahr = datetime.now().year
    aktueller_monat = datetime.now().month
    monate = list(range(1, 13))
    monat = st.selectbox("Monat", monate, index=aktueller_monat-1, format_func=lambda m: calendar.month_name[m])
    jahr = st.number_input("Jahr", min_value=2020, max_value=aktuelles_jahr+1, value=aktuelles_jahr, step=1)
    monat_str = f"{monat:02d}"
    jahr_str = str(jahr)
    st.set_page_config(page_title="Lohnübersicht", layout="centered")
    st.title("Lohnübersicht für Mitarbeiter")
    df_mitarbeiter = pd.read_sql("SELECT benutzername, vorname, nachname, rolle FROM mitarbeiter", engine)
    df_stunden = pd.read_sql(
    "SELECT benutzername, SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE TO_CHAR(datum, 'MM') = %s AND TO_CHAR(datum, 'YYYY') = %s GROUP BY benutzername",
    engine, params=(monat_str, jahr_str)
    )   
    df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
    df_mitarbeiter["voller_name"] = df_mitarbeiter["vorname"] + " " + df_mitarbeiter["nachname"]
    mitarbeiter_liste = df_mitarbeiter["voller_name"].tolist()
    benutzer_map = dict(zip(df_mitarbeiter["voller_name"], df_mitarbeiter["benutzername"]))
    # Stunden- und Lohnübersicht ganz oben anzeigen
    st.subheader(f"Stunden- und Lohnübersicht für {calendar.month_name[monat]} {jahr}")
    df = df_mitarbeiter.merge(df_stunden, on="benutzername", how="left").merge(df_gehalt, on="rolle", how="left")
    df["gesamtstunden"] = df["gesamtstunden"].fillna(0)
    df["gehalt"] = df["gehalt"].fillna(0)
    df["Bruttolohn (€)"] = df["gesamtstunden"] * df["gehalt"]
    # HTML-Tabelle für Lohnübersicht
    display_cols = ["voller_name", "rolle", "gesamtstunden", "gehalt", "Bruttolohn (€)"]
    table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
    table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Name</th><th>Rolle</th><th>Gesamtstunden</th><th>Gehalt (€/h)</th><th>Bruttolohn (€)</th></tr></thead><tbody>"
    for _, row in df[display_cols].iterrows():
        voller_name = str(row['voller_name']) if pd.notnull(row['voller_name']) else ""
        rolle = str(row['rolle']) if pd.notnull(row['rolle']) else "-"
        gesamtstunden = f"{float(row['gesamtstunden']):.1f}" if pd.notnull(row['gesamtstunden']) else "0.0"
        gehalt = f"{float(row['gehalt']):.2f}" if pd.notnull(row['gehalt']) else "0.00"
        bruttolohn = f"{float(row['Bruttolohn (€)']):.2f}" if pd.notnull(row['Bruttolohn (€)']) else "0.00"
        table_html += f"<tr><td><strong>{voller_name}</strong></td><td>{rolle}</td><td>{gesamtstunden}</td><td>{gehalt}</td><td>{bruttolohn}</td></tr>"
    table_html += "</tbody></table></div>"
    st.markdown(table_html, unsafe_allow_html=True)
    if "lohnabrechnung_zeilen" not in st.session_state:
        st.session_state.lohnabrechnung_zeilen = [
            {"mitarbeiter": "", "betrag_typ": "berechnet", "betrag": 0.0, "sachleistungen": [], "sachwerte": {}, "ueberstunden": 0.0, "praemien": 0.0, "krankheitstage": 0,}
        ]
    st.subheader("Lohnübersicht erfassen")
    col_add, col_remove = st.columns([1,1])
    with col_add:
        if st.button("+ Zeile hinzufügen"):
            st.session_state.lohnabrechnung_zeilen.append({"mitarbeiter": "", "betrag_typ": "berechnet", "betrag": 0.0, "sachleistungen": [], "sachwerte": {}, "ueberstunden": 0.0, "praemien": 0.0, "krankheitstage": 0, "neuanfaenger": False, "abbrecher": False, "unbezahlter_urlaub": 0})
    with col_remove:
        if st.button("- Zeile entfernen") and len(st.session_state.lohnabrechnung_zeilen) > 1:
            st.session_state.lohnabrechnung_zeilen.pop()
    for idx, zeile in enumerate(st.session_state.lohnabrechnung_zeilen):
        st.markdown(f"<div style='border:2px solid #0078D4; border-radius:8px; padding:16px; margin-bottom:20px; background:var(--box-bg)'><h4>Lohnübersicht Zeile {idx+1}</h4></div>", unsafe_allow_html=True)
        zeile["mitarbeiter"] = st.selectbox("Mitarbeiter", ["-"] + mitarbeiter_liste, index=mitarbeiter_liste.index(zeile["mitarbeiter"]) if zeile["mitarbeiter"] in mitarbeiter_liste else 0, key=f"mitarbeiter_{idx}")
        zeile["betrag_typ"] = st.selectbox("Betragstyp", ["berechnet", "manuell"], index=["berechnet", "manuell"].index(zeile["betrag_typ"]), key=f"betragtyp_{idx}")
        # Automatische Berechnung des Betrags
        if zeile["mitarbeiter"] != "-":
            benutzer = benutzer_map.get(zeile["mitarbeiter"], "")
            rolle = df_mitarbeiter[df_mitarbeiter["benutzername"] == benutzer]["rolle"].iloc[0] if benutzer else "-"
            gesamtstunden = df_stunden[df_stunden["benutzername"] == benutzer]["gesamtstunden"].iloc[0] if benutzer in df_stunden["benutzername"].values else 0.0
            gehalt = df_gehalt[df_gehalt["rolle"] == rolle]["gehalt"].iloc[0] if rolle in df_gehalt["rolle"].values else 0.0
            berechnet = float(gesamtstunden) * float(gehalt)
        else:
            berechnet = 0.0
        if zeile["betrag_typ"] == "berechnet":
            zeile["betrag"] = berechnet
            st.markdown(f"<b>Betrag (€):</b> <span style='color:#0078D4;font-weight:bold'>{berechnet:.2f} €</span>", unsafe_allow_html=True)
        else:
            zeile["betrag"] = st.number_input("Betrag (€)", min_value=0.0, value=zeile["betrag"], key=f"betrag_{idx}")
        sachleistungen = ["Geschäftswagen", "Handy", "Laptop", "Essensgutscheine", "Sonstiges"]
        zeile["sachleistungen"] = st.multiselect("Sachleistungen", sachleistungen, default=zeile.get("sachleistungen", []), key=f"sach_{idx}")
        # Sachleistungswerte
        if "sachwerte" not in zeile:
            zeile["sachwerte"] = {}
        for sach in zeile["sachleistungen"]:
            zeile["sachwerte"][sach] = st.number_input(f"Wert für {sach} (€)", min_value=0.0, value=zeile["sachwerte"].get(sach, 0.0), key=f"sachwert_{idx}_{sach}")
        zeile["ueberstunden"] = st.number_input("Überstunden (h)", min_value=0.0, value=zeile["ueberstunden"], key=f"ueberstunden_{idx}")
        zeile["praemien"] = st.number_input("Prämien (€)", min_value=0.0, value=zeile["praemien"], key=f"praemien_{idx}")
        zeile["krankheitstage"] = st.number_input("Krankheitstage", min_value=0, value=zeile["krankheitstage"], key=f"krank_{idx}")
        # Daten für PDF-Export initialisieren
    df_mitarbeiter = pd.read_sql("SELECT benutzername, vorname, nachname, rolle FROM mitarbeiter", engine)
    df_stunden_pdf = pd.read_sql(
    "SELECT benutzername, SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE TO_CHAR(datum, 'MM') = %s AND TO_CHAR(datum, 'YYYY') = %s GROUP BY benutzername",
    engine, params=(monat_str, jahr_str)
    )
    df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
    df_mitarbeiter["voller_name"] = df_mitarbeiter["vorname"] + " " + df_mitarbeiter["nachname"]
    benutzer_map = dict(zip(df_mitarbeiter["voller_name"], df_mitarbeiter["benutzername"]))
    # PDF-Export Button ganz unten
    st.markdown("---")
    if st.button("📥 Lohnübersicht als PDF exportieren"):
        # Filtere auch für PDF die Daten nach Monat/Jahr
        df_stunden_pdf = pd.read_sql(
            "SELECT benutzername, SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE TO_CHAR(datum, 'MM') = %s AND TO_CHAR(datum, 'YYYY') = %s GROUP BY benutzername",
            engine, params=(monat_str, jahr_str)
        )
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50
        # Firmenname groß
        firmenname = st.session_state.get("firmenname", "")
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, firmenname)
        y -= 22
        # Lohnabrechnung Monat/Jahr
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Lohn Übersicht: {calendar.month_name[monat]} {jahr}")
        y -= 18
        # Tabellenkopf
        c.setFont("Helvetica-Bold", 8)
        x_pos = [30, 140, 190, 250, 340, 410, 500, 560]
        headers = ["Mitarbeiter (Rolle)", "Grundlohn", "Überstunden", "Überstunden-Prämie", "Krankheitstage", "Sachbezüge", "Gesamt-Brutto"]
        for i, header in enumerate(headers):
            c.drawString(x_pos[i], y, header)
        # Horizontale Linie unter Kopf
        y_line = y - 2
        c.setLineWidth(0.5)
        c.line(x_pos[0], y_line, x_pos[-1], y_line)
        y -= 12
        c.setFont("Helvetica", 7)
        payroll_total = 0.0
        for idx, zeile in enumerate(st.session_state.lohnabrechnung_zeilen):
            benutzer = benutzer_map.get(zeile['mitarbeiter'], '')
            rolle = df_mitarbeiter[df_mitarbeiter['benutzername'] == benutzer]['rolle'].iloc[0] if benutzer in df_mitarbeiter['benutzername'].values else "-"
            gesamtstunden = df_stunden_pdf[df_stunden_pdf['benutzername'] == benutzer]['gesamtstunden'].iloc[0] if benutzer in df_stunden_pdf['benutzername'].values else 0.0
            gehalt = df_gehalt[df_gehalt['rolle'] == rolle]['gehalt'].iloc[0] if rolle in df_gehalt['rolle'].values else 0.0
            grundlohn = float(gesamtstunden) * float(gehalt) if zeile["betrag_typ"] == "berechnet" else zeile["betrag"]
            grundlohn_str = f"{grundlohn:,.2f} €".replace(",", ".")
            ueberstunden = zeile.get("ueberstunden", 0.0)
            ueberstunden_str = f"{ueberstunden:.0f} Std." if ueberstunden else "0"
            praemie = zeile.get("praemien", 0.0)
            praemie_str = f"{praemie:,.2f} €".replace(",", ".")
            krankheitstage = zeile.get("krankheitstage", 0)
            if zeile.get("sachleistungen"):
                sachbezuege = "\n".join([f"{s}: {zeile['sachwerte'].get(s,0):.2f} €" for s in zeile["sachleistungen"]])
            else:
                sachbezuege = "–"
            gesamt_brutto = grundlohn + praemie + sum(zeile['sachwerte'].values())
            payroll_total += gesamt_brutto
            gesamt_brutto_str = f"{gesamt_brutto:,.2f} €".replace(",", ".")
            mitarbeiter_rolle = f"{zeile['mitarbeiter']} ({rolle})"
            cell_padding = 4  # Abstand zu den vertikalen Linien
            # Sachbezüge ggf. mehrzeilig ausgeben
            max_lines = max(1, sachbezuege.count("\n") + 1)
            for line_idx in range(max_lines):
                row_values = []
                for i, val in enumerate([mitarbeiter_rolle, grundlohn_str, ueberstunden_str, praemie_str, str(krankheitstage), sachbezuege, gesamt_brutto_str]):
                    if i == 5:  # Sachbezüge
                        sach_lines = sachbezuege.split("\n") if sachbezuege != "–" else ["–"]
                        val = sach_lines[line_idx] if line_idx < len(sach_lines) else ""
                    elif line_idx > 0:
                        val = ""
                    row_values.append(val)
                for i, val in enumerate(row_values):
                    c.drawString(x_pos[i] + cell_padding, y, val)
                # Vertikale Linien
                c.setLineWidth(0.3)
                for x in x_pos:
                    c.line(x, y+8, x, y-2)
                y -= 10
                if y < 60:
                    c.showPage()
                    y = height - 50
            # Nach jedem Mitarbeiter: dünne horizontale Linie
            c.setLineWidth(0.2)
            c.line(x_pos[0], y+4, x_pos[-1], y+4)
            y -= 10
        c.save()
        buffer.seek(0)
        # Save PDF to lohnabrechnung_archiv
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO lohnabrechnung_archiv (jahr, monat, benutzername, erstellt_am, pdf_data)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (jahr, monat, st.session_state.get("user", ""), datetime.now().isoformat(), buffer.getvalue())
            )
            # Speichere/Upsert die Lohn-Ausgabe zusätzlich in ausgaben_lohn (wird im Dashboard als Ausgabe addiert)
            try:
                existing = conn.exec_driver_sql(
                    "SELECT id FROM ausgaben_lohn WHERE benutzername = %s AND jahr = %s AND monat = %s",
                    (st.session_state.get("user", ""), jahr, monat)
                ).fetchone()
                if existing:
                    conn.exec_driver_sql(
                        "UPDATE ausgaben_lohn SET betrag = %s, erstellt_am = %s WHERE id = %s",
                        (float(payroll_total), datetime.now().isoformat(), existing[0])
                    )
                else:
                    conn.exec_driver_sql(
                        "INSERT INTO ausgaben_lohn (benutzername, jahr, monat, betrag, erstellt_am) VALUES (%s, %s, %s, %s, %s)",
                        (st.session_state.get("user", ""), jahr, monat, float(payroll_total), datetime.now().isoformat())
                    )
            except Exception:
                pass
        # Inform user about stored payroll expense
        st.success(f"Lohnübersicht exportiert. Lohn-Summe {payroll_total:,.2f} € wurde als Ausgaben-Lohn gespeichert.")
        st.download_button("PDF herunterladen", buffer, file_name=f"Lohnübersicht_{jahr}_{monat}.pdf", mime="application/pdf")
    st.markdown("---")
