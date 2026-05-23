# ============================================================
#  pages/rechnungen.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.rechnungen import rechnungs_page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO

from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
)

from ui.pdf_generator import (
    generate_invoice_pdf_v2, 
    generate_pauschal_invoice_pdf
)

def rechnungs_page():
            # ✅ Prüfe ob Bank- und Registerdaten vorhanden sind
        required_bank_fields = {
            "iban": "IBAN",
            "bic": "BIC",
            "bankname": "Bankname"
        }
        missing_bank_fields = [field for field in required_bank_fields.keys() if not st.session_state.get(field)]
        
        if missing_bank_fields:
            # Leite zur Setup-Seite für Bank-Daten um
            st.session_state.page = "setup_bank_register_data"
            st.session_state.return_page = "app"  # Merke dass wir vom Invoice zurückkommen
            st.rerun()
        
        st.header(" Rechnung manuell erstellen")

        st.markdown("Hier kannst du eine individuelle Rechnung für ein Projekt erstellen.")
        # 1. Projekt manuell eingeben oder aus Liste auswählen
        # Hole alle Projekte des Benutzers
        df_projekte = pd.read_sql("SELECT name FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        projekt_liste = df_projekte["name"].tolist()
        if not projekt_liste:
            st.warning("Keine aktiven Projekte vorhanden. Bitte zuerst ein Projekt anlegen.")
            projekt_name = ""
        else:
            # Callback: wenn ein Projekt ausgewählt wird, autofülle die zugehörige Rechnungsnummer
            def _update_rechnungsnummer():
                pn = st.session_state.get("projekt_select")
                if not pn:
                    return
                df_p = pd.read_sql("SELECT rechnungsnummer FROM projekte WHERE name = %s AND benutzername = %s", engine, params=(pn, st.session_state.user))
                if not df_p.empty and pd.notnull(df_p["rechnungsnummer"].iloc[0]):
                    st.session_state["rechnungsnummer_input"] = int(df_p["rechnungsnummer"].iloc[0])
                else:
                    st.session_state["rechnungsnummer_input"] = st.session_state.get("standard_rechnungsnummer", 1)

            projekt_name = st.selectbox("Projektname", projekt_liste, index=0, key="projekt_select", on_change=_update_rechnungsnummer)
        empfaenger_name = st.text_input("Empfängername")
        empfaenger_adresse = st.text_area("Empfängeradresse")
        
        leistungszeitraum_start = st.date_input(
            "Leistungszeitraum Beginn",
            value=st.session_state.get("leistungszeitraum_start", date.today()),
            key="leistungszeitraum_start"
        )
        leistungszeitraum_ende = st.date_input("Leistungszeitraum Ende", value=date.today(), key="leistungszeitraum_ende")
    
        
                # Rechnungsnummer bestimmen (nicht im Session-State speichern!)
        df_projekt = pd.read_sql("SELECT id, rechnungsnummer FROM projekte WHERE name = %s AND benutzername = %s", engine, params=(projekt_name, st.session_state.user))
        if not df_projekt.empty and pd.notnull(df_projekt["rechnungsnummer"].iloc[0]):
            autofill_rechnungsnummer = int(df_projekt["rechnungsnummer"].iloc[0])
        else:
            autofill_rechnungsnummer = st.session_state.get("standard_rechnungsnummer", 1)

        # If the input widget has not been set in session state yet, initialize it so the widget shows the project's number
        if "rechnungsnummer_input" not in st.session_state:
            st.session_state["rechnungsnummer_input"] = autofill_rechnungsnummer

        rechnungsnummer = st.number_input(
            "Rechnungsnummer",
            min_value=1,
            step=1,
            key="rechnungsnummer_input"
        )
        # 3. Rechnungsnummer-Widget anzeigen
        # --- Rechnungsmodus auswählen ---
        rechnungsmodus = st.radio(
            "Rechnungsmodus wählen",
            ["Berechnet (automatisch)", "Pauschale (Festpreis)"],
            key="rechnungsmodus"  # Use consistent key for state management
        )
       
       
        # Button zum automatischen Ausfüllen der Positionen
        if rechnungsmodus == "Berechnet (automatisch)":
            if st.button("Auto-Fill: Projekt-Daten"):
                # ...existing code for automatische Berechnung...
                df_projekt = pd.read_sql("SELECT id, rechnungsnummer FROM projekte WHERE name = %s AND benutzername = %s", engine, params=(projekt_name, st.session_state.user))
                if not df_projekt.empty:             
                    projekt_id = int(df_projekt["id"].iloc[0])
                    # Die Rechnungsnummer wurde bereits durch _update_rechnungsnummer() gesetzt
                    if "datum" in df_projekt.columns and pd.notnull(df_projekt["datum"].iloc[0]):
                        st.session_state.leistungszeitraum_start = datetime.strptime(df_projekt["datum"].iloc[0], "%Y-%m-%d").date()
                    df_material = pd.read_sql("SELECT material, menge, einheit FROM materialien WHERE projekt_id = %s AND benutzername = %s", engine, params=(projekt_id, st.session_state.user))
                    df_lager = pd.read_sql("SELECT material, preis_ankauf, preis_verkauf FROM lagerbestand WHERE benutzername = %s", engine, params=(st.session_state.user,))
                    i = 0
                    for row in df_material.itertuples():
                        menge = float(row.menge) if row.menge is not None else 0.0
                        if menge > 0:
                            st.session_state[f"name_{i}"] = row.material
                            st.session_state[f"menge_{i}"] = menge
                            st.session_state[f"einheit_{i}"] = row.einheit if row.einheit is not None else ""
                            preis_row = df_lager[df_lager["material"] == row.material]
                            preis = preis_row["preis_verkauf"].iloc[0] if not preis_row.empty and preis_row["preis_verkauf"].iloc[0] is not None else 0.0
                            st.session_state[f"preis_{i}"] = preis
                            i += 1
                    st.session_state.rechnungs_positionen = max(i, 1)

                    df_mitarbeiter = pd.read_sql("""
                        SELECT m.benutzername, m.rolle 
                        FROM mitarbeiter m
                        JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
                        WHERE mp.projekt_id = %s AND m.chefname = %s
                    """, engine, params=(projekt_id, st.session_state.user))
                    df_gehalt = pd.read_sql("SELECT rolle, gehalt FROM standardgehaelter", engine)
                    j = 0
                    for row in df_mitarbeiter.itertuples():
                        df_stunden = pd.read_sql(
                            "SELECT SUM(stunden) as gesamtstunden FROM arbeitszeiten WHERE projekt_id = %s AND benutzername = %s",
                            engine, params=(projekt_id, row.benutzername)
                        )
                        gesamtstunden = df_stunden["gesamtstunden"].iloc[0] if not df_stunden.empty and df_stunden["gesamtstunden"].iloc[0] is not None else 0.0
                        if gesamtstunden > 0:
                            st.session_state[f"rolle_{j}"] = row.rolle
                            gehalt_row = df_gehalt[df_gehalt["rolle"] == row.rolle]
                            stundensatz = gehalt_row["gehalt"].iloc[0] if not gehalt_row.empty else 0.0
                            st.session_state[f"lohn_{j}"] = stundensatz
                            st.session_state[f"stunden_{j}"] = gesamtstunden
                            j += 1
                    st.session_state.anzahl_mitarbeiter = max(j, 1)
                    df_geraete_nutzung = pd.read_sql("""
                        SELECT n.geraet, SUM(n.nutzungszeit) as stunden
                        FROM geraete_nutzung n
                        WHERE n.projekt_id = %s
                        GROUP BY n.geraet
                    """, engine, params=(projekt_id,))
                    df_geraete_lager = pd.read_sql(
                        "SELECT geraet, betriebskosten FROM geraete_lager WHERE benutzername = %s",
                        engine, params=(st.session_state.user,)
                    )
                    k = 0
                    for row in df_geraete_nutzung.itertuples():
                        stunden = float(row.stunden) if row.stunden is not None else 0.0
                        if stunden > 0:
                            st.session_state[f"geraet_{k}"] = row.geraet
                            st.session_state[f"geraet_stunden_{k}"] = stunden
                            kosten_row = df_geraete_lager[df_geraete_lager["geraet"] == row.geraet]
                            default_kosten = float(kosten_row["betriebskosten"].iloc[0]) if not kosten_row.empty else 0.0
                            st.session_state[f"geraet_kosten_{k}"] = default_kosten
                            k += 1
                    st.session_state.geraete_positionen = max(k, 1)
                    st.success("Formular wurde automatisch mit Projekt-Daten ausgefüllt.")
                else:
                    st.warning("Projekt nicht gefunden. Bitte korrekten Projektnamen eingeben.")
        # 2. Manuell Positionen hinzufügen (Materialien/Leistungen)
        if rechnungsmodus == "Berechnet (automatisch)":
            st.subheader("Rechnungspositionen hinzufügen")
            positionen = []
            if "rechnungs_positionen" not in st.session_state:
                st.session_state.rechnungs_positionen = 1
            col_add, col_remove = st.columns([1, 1])
            with col_add:
                if st.button("Position hinzufügen"):
                    st.session_state.rechnungs_positionen += 1
            with col_remove:
                if st.button("Position entfernen"):
                    if st.session_state.rechnungs_positionen > 1:
                        st.session_state.rechnungs_positionen -= 1       
            if "anzahl_mitarbeiter" not in st.session_state:
                st.session_state.anzahl_mitarbeiter = 1
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Mitarbeiterposition hinzufügen"):
                    st.session_state.anzahl_mitarbeiter += 1
            with col2:
                if st.button("Mitarbeiterposition entfernen") and st.session_state.anzahl_mitarbeiter > 1:
                    st.session_state.anzahl_mitarbeiter -= 1
            if "geraete_positionen" not in st.session_state:
                st.session_state.geraete_positionen = 1
            col_add_g, col_remove_g = st.columns([1, 1])
            with col_remove_g:
                if st.button("Geräteposition entfernen") and st.session_state.geraete_positionen > 1:
                    if st.session_state.geraete_positionen > 1:
                        st.session_state.geraete_positionen -= 1

            with col_add_g:
                if st.button("Geräteposition hinzufügen"):
                    st.session_state.geraete_positionen += 1
            # ...existing code für berechnete Positionen...
        else:
            st.subheader("Pauschalbetrag eingeben")
            pauschale = st.number_input("Pauschalbetrag (Brutto, EUR)", min_value=0.0, step=0.01, key="pauschalbetrag")
            st.info("Die Rechnung wird als Pauschale erstellt. Der Betrag wird als Bruttowert übernommen.")
        df_geraete_lager = pd.read_sql(
            "SELECT geraet, betriebskosten FROM geraete_lager WHERE benutzername = %s",
            engine, params=(st.session_state.user,)
        )
        geraete_liste = df_geraete_lager["geraet"].tolist()
        if rechnungsmodus == "Berechnet (automatisch)":
            # Hole alle Materialien aus dem Lagerbestand
            df_materialien = pd.read_sql(
                "SELECT material, einheit, preis_verkauf FROM lagerbestand WHERE benutzername = %s",
                engine,
                params=(st.session_state.user,)
            )
            materialien_liste = [""] + sorted(df_materialien["material"].tolist())
            
            with st.form("rechnungsformular"):
                st.subheader("Matreialkosten")
                positionen = []
                for i in range(st.session_state.rechnungs_positionen):
                    cols = st.columns([4, 2, 2, 2])
                    name = cols[0].selectbox("Bezeichnung", materialien_liste, key=f"name_{i}")
                    menge = cols[1].number_input("Menge", min_value=0.0, step=1.0, key=f"menge_{i}")
                    
                    # Hole Einheit und Verkaufspreis wenn Material ausgewählt
                    if name and name in df_materialien["material"].values:
                        material_row = df_materialien[df_materialien["material"] == name].iloc[0]
                        einheit = material_row["einheit"]
                        default_preis = float(material_row["preis_verkauf"]) if pd.notnull(material_row["preis_verkauf"]) else 0.0
                    else:
                        einheit = EINHEITEN[0]
                        default_preis = 0.0
                    
                    einheit = cols[2].selectbox("Einheit", EINHEITEN, key=f"einheit_{i}", index=EINHEITEN.index(einheit) if einheit in EINHEITEN else 0)
                    preis = cols[3].number_input("Einzelpreis (€)", min_value=0.0, step=0.1, value=default_preis, key=f"preis_{i}")
                    
                    if name and menge > 0:
                        positionen.append({"name": name, "menge": menge, "einheit": einheit, "preis": preis})
                st.subheader("Mitarbeiterleistungen")
                arbeitsleistungen = []
                for j in range(st.session_state.anzahl_mitarbeiter): 
                    cols = st.columns([4, 0.5, 2, 0.5, 2,])
                    rolle = cols[0].selectbox("Rolle", [""] + ROLLEN, key=f"rolle_{j}")
                    stundensatz = cols[2].number_input("Stundenlohn (€)", min_value=0.0, key=f"lohn_{j}")
                    stunden = cols[4].number_input("Geleistete Stunden", min_value=0.0, key=f"stunden_{j}")
                    if rolle and stunden > 0:
                        arbeitsleistungen.append({
                            "rolle": rolle,
                            "stundensatz": stundensatz,
                            "stunden": stunden
                        })
                st.subheader("Gerätekosten")
                geraetepositionen = []
                for k in range(st.session_state.geraete_positionen):
                    cols = st.columns([4, 2, 2])
                    geraet = cols[0].selectbox("Gerät", [""] + geraete_liste, key=f"geraet_{k}")
                    stunden = cols[1].number_input("Nutzungsstunden", min_value=0.0, step=0.1, key=f"geraet_stunden_{k}")
                    default_kosten = float(df_geraete_lager[df_geraete_lager["geraet"] == geraet]["betriebskosten"].iloc[0]) if geraet in geraete_liste else 0.0
                    kosten = cols[2].number_input("Betriebskosten (€ pro Std)", min_value=0.0, step=0.1, value=default_kosten, key=f"geraet_kosten_{k}")
                    if geraet and stunden > 0:
                        geraetepositionen.append({
                            "geraet": geraet,
                            "stunden": stunden,
                            "betriebskosten": kosten
                        })
                erstellen = st.form_submit_button("Rechnung erstellen")
        elif rechnungsmodus == "Pauschale (Festpreis)":
            positionen = [
                {
                    "name": f"{projekt_name} ",
                    "menge": 1,
                    "einheit": "Pauschale",
                    "preis": pauschale,
                    "gesamtpreis": pauschale
                }
            ]
            with st.form("rechnungsformular"):
                erstellen = st.form_submit_button("Rechnung erstellen")
        if erstellen and projekt_name and empfaenger_name:
            num_check = pd.read_sql("SELECT name FROM projekte WHERE rechnungsnummer = %s AND benutzername = %s", engine, params=(rechnungsnummer, st.session_state.user))
            if not num_check.empty and num_check["name"].iloc[0] != projekt_name:
                st.error(f"Rechnungsnummer {rechnungsnummer} ist bereits für Projekt '{num_check['name'].iloc[0]}' vergeben!")
            else:
                rechnungsmodus = st.session_state.rechnungsmodus  # Use the radio button's state directly
                
                # Unterschiedliche PDF-Generierung je nach Modus
                if rechnungsmodus == "Pauschale (Festpreis)":
                    # Im Pauschalmodus keine Positionen, nur den Pauschalbetrag übergeben
                    # Im Pauschalmodus keine Positionen, nur den Pauschalbetrag übergeben
                    pdf_buffer = generate_pauschal_invoice_pdf(
                        projekt_name,
                        empfaenger_name,
                        empfaenger_adresse,
                        pauschale,  # Bruttobetrag für Pauschale
                        rechnungsnummer,
                        leistungszeitraum_start,
                        leistungszeitraum_ende
                    )
                    # ✅ RICHTIG: pauschale ist BRUTTO, nettobetrag = brutto / 1.19
                    nettobetrag = pauschale / 1.19
                else:
                    # Berechnet (automatisch) Modus
                    if 'arbeitsleistungen' not in locals():
                        arbeitsleistungen = []
                    if 'geraetepositionen' not in locals():
                        geraetepositionen = []
                    
                    pdf_buffer = generate_invoice_pdf_v2(
                        projekt_name,
                        empfaenger_name,
                        empfaenger_adresse,
                        [(p["name"], p["menge"],p["einheit"], p["preis"]) for p in positionen],
                        arbeitsleistungen,
                        rechnungsnummer,
                        leistungszeitraum_start,
                        leistungszeitraum_ende,
                        geraetepositionen
                    )
                    # ✅ Berechne Netto aus allen Positionen
                    nettobetrag = 0.0
                    # Material
                    if 'positionen' in locals():
                        for p in positionen:
                            nettobetrag += p.get("preis", 0.0) * p.get("menge", 0.0)
                    # Arbeitsleistungen
                    if arbeitsleistungen:
                        for leistung in arbeitsleistungen:
                            nettobetrag += leistung.get("stundensatz", 0.0) * leistung.get("stunden", 0.0)
                    # Gerätekosten
                    if geraetepositionen:
                        for pos in geraetepositionen:
                            nettobetrag += pos.get("betriebskosten", 0.0) * pos.get("stunden", 0.0)
                
                pdf_buffer.seek(0)
                pdf_bytes = pdf_buffer.getvalue()
                st.markdown(f"**PDF-Größe beim Speichern:** {len(pdf_bytes)} Bytes")
                st.markdown(f"**PDF-Bytes (Hex, erste 100):** {pdf_bytes[:100].hex()}")
                # PDF auch in die Tabelle 'rechnungen' speichern
                benutzername = st.session_state.get("user")
                if not benutzername or benutzername is None:
                    st.error("Kein Benutzername gesetzt! Bitte zuerst einloggen.")
                    return
                
                # Stelle sicher, dass die Spalte benutzername existiert (separate connection)
                try:
                    with engine.begin() as temp_conn:
                        temp_conn.exec_driver_sql("ALTER TABLE rechnungen ADD COLUMN benutzername TEXT")
                except Exception:
                    pass  # Column already exists
                
                # Now use a fresh connection for the INSERT
                with engine.begin() as conn:
                    # Stelle sicher, dass ein Benutzer angemeldet ist und übergebe den Benutzernamen beim Speichern
                    benutzername = st.session_state.get("user")
                    if not benutzername:
                        st.error("Bitte melden Sie sich zuerst an, bevor Sie eine Rechnung speichern.")
                    else:
                        try:
                            # Delete old invoice if exists and insert new one
                            conn.exec_driver_sql(
                                "DELETE FROM rechnungen WHERE projekt_name = %s AND rechnungsnummer = %s",
                                (projekt_name, rechnungsnummer)
                            )
                            conn.exec_driver_sql(
                                "INSERT INTO rechnungen (projekt_name, rechnungsnummer, pdf_data, erstellt_am, nettobetrag, benutzername) VALUES (%s, %s, %s, %s, %s, %s)",
                                (projekt_name, rechnungsnummer, pdf_bytes, date.today().strftime("%Y-%m-%d"), nettobetrag, benutzername)
                            )
                            conn.commit()
                            st.success("Rechnung gespeichert.")
                            try:
                                # Ensure the project row stores this invoice number so it can be autofilled next time
                                conn.exec_driver_sql(
                                    "UPDATE projekte SET rechnungsnummer = %s WHERE name = %s AND benutzername = %s",
                                    (rechnungsnummer, projekt_name, benutzername)
                                )
                                conn.commit()
                            except Exception:
                                conn.rollback()
                                pass
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Fehler beim Speichern der Rechnung: {str(e)}")
                        st.download_button("Rechnung als PDF herunterladen", data=pdf_bytes, file_name=f"Rechnung_{projekt_name}_{rechnungsnummer}.pdf", mime="application/pdf")
        elif erstellen:
            st.warning("Bitte Projektname und Empfängerdaten eingeben.")

