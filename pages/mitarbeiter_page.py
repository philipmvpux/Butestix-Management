# ============================================================
#  pages/mitarbeiter_page.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.mitarbeiter_page import mitarbeiter_page
# ============================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from io import BytesIO
from sqlalchemy import text
from database import engine
from ui.helpers import (
    lade_firmendaten, GESELLSCHAFTSFORMEN, ROLLEN,
    EINHEITEN, GGG, wetter_optionen, boden_optionen,
)

def mitarbeiter_page():
        if "projekt_id" in st.session_state:
            projekt_id = st.session_state["projekt_id"]
            df = pd.read_sql("SELECT name FROM projekte WHERE id = %s", engine, params=(projekt_id,))
            heute = date.today().strftime("%Y-%m-%d")
            # --- Geräteverbrauch-Reset (korrekt, wie bisher) ---
            if st.session_state.get("geraete_eingabe_datum") != heute:
                st.session_state.geraete_expander_unten = False
                st.session_state.geraete_eingabe_gespeichert = []
                st.session_state.geraetezeilen = [{"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0}]
                st.session_state.geraete_eingabe_datum = heute
                st.session_state.geraete_reset_done = False
                st.rerun()
            st.session_state.geraete_reset_done = True
            # --- Materialverbrauch-Reset: Nur Expander um Mitternacht zurücksetzen, keine Daten löschen! ---
            if st.session_state.get("material_eingabe_datum") != heute:
                st.session_state.material_expander_unten = False
                st.session_state.material_eingabe_datum = heute
                st.rerun()
            if not df.empty:
                col_head, col_btn, col_bt = st.columns([6, 2, 2])
                with col_head:
                    st.header(f"Projekt: {df['name'].iloc[0]}")
                with col_btn:
                    if st.button("Vorplanungs-Kalender"):
                        st.session_state.page = "vorplanung"
                        st.rerun()              
                with col_bt:
                    if st.button("Material-Planung"):
                        st.session_state.page = "materialplanung"
                        st.rerun()
                st.subheader("Projekt-Checkliste")
                with st.expander(" Checkliste bearbeiten"):
                    # Checklistenpunkte laden
                    checklist_df = pd.read_sql(
                        "SELECT id, text, kommentar, erledigt FROM checklistenpunkte WHERE projekt_id = %s ORDER BY id",
                        engine, params=(projekt_id,)
                    )

                    if checklist_df.empty:
                        st.info("Für dieses Projekt wurde noch keine Checkliste angelegt.")
                    else:
                        # Fortschrittspunkte: Abhakbar, Kommentarspalte darunter mit Speicher-Button
                        for idx, row in checklist_df.iterrows():
                            if row["text"]:
                                col1, col2, col3 = st.columns([8, 2, 2])
                                col1.write(row["text"])
                                erledigt = bool(row["erledigt"])
                                checked = col2.checkbox("Abgehakt", value=erledigt, key=f"erledigt_{row['id']}")
                                if col3.button("💾", key=f"save_erledigt_{row['id']}"):
                                    erledigt_am = date.today().strftime("%Y-%m-%d") if checked else None
                                    with engine.begin() as conn:
                                        conn.execute(
                                            text("""
                                                UPDATE checklistenpunkte SET erledigt = :erledigt, erledigt_am = :erledigt_am WHERE id = :id
                                            """),
                                            {"erledigt": int(checked), "erledigt_am": erledigt_am, "id": row["id"]}
                                        )
                                    st.success("Fortschritt gespeichert.")
                                    st.rerun()
                        # Zeile hinzufügen-Button wieder am Ende
                        # Separates Textfeld für Checklisten-Kommentar des Mitarbeiters
                        # Tabelle wird in database.py erstellt
                        fortschritt_kommentar_key = f"fortschritt_kommentar_{projekt_id}"
                        fortschritt_kommentar = st.text_area("zusätzlicher Fortschritt", value=st.session_state.get(fortschritt_kommentar_key, ""), key=fortschritt_kommentar_key, height=40)
                        if st.button("Fortschritt speichern", key="save_fortschritt_kommentar"):
                            # benutzername Spalte wird in database.py erstellt
                            # DELETE und dann INSERT statt ON CONFLICT (da Primary Key möglicherweise nicht gültig ist)
                            with engine.begin() as conn:
                                # Zuerst alten Eintrag löschen
                                conn.execute(
                                    text("""
                                        DELETE FROM checklisten_fortschrittkommentar 
                                        WHERE projekt_id = :projekt_id 
                                        AND benutzername = :benutzername 
                                        AND datum = :datum
                                    """),
                                    {
                                        "projekt_id": projekt_id,
                                        "benutzername": st.session_state.user,
                                        "datum": date.today().strftime("%Y-%m-%d")
                                    }
                                )
                                # Dann neuen Eintrag einfügen
                                conn.execute(
                                    text("""
                                        INSERT INTO checklisten_fortschrittkommentar (projekt_id, benutzername, kommentar, datum)
                                        VALUES (:projekt_id, :benutzername, :kommentar, :datum)
                                    """),
                                    {
                                        "projekt_id": projekt_id,
                                        "benutzername": st.session_state.user,
                                        "kommentar": fortschritt_kommentar,
                                        "datum": date.today().strftime("%Y-%m-%d")
                                    }
                                )
                            st.success("Fortschritt-Kommentar gespeichert.")
                            st.rerun()                     
                        # Button entfernt: Kommentare werden nicht als eigene Checklistenpunkte gespeichert
                    # Wetter- und Bodenverhältnisse (je 2 Felder)
                    # Wetter- und Bodenverhältnisse (je 2 Felder nebeneinander, keine Dopplung möglich)
                heute = date.today().strftime("%Y-%m-%d")
                try:
                    wetter_row = pd.read_sql(
                        "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
                        engine, params=(projekt_id, heute)
                    )
                except Exception:
                    # Tabelle wetterdaten wird in database.py erstellt
                    wetter_row = pd.DataFrame()  # Leeres DataFrame
                
                wetter_gespeichert = not wetter_row.empty

                if not wetter_gespeichert:
                    st.subheader(" Wetter- und Bodenverhältnisse")
                    with st.expander(" Wetter- und Bodenverhältnisse eintragen"):
                        col_w1, col_w2 = st.columns(2)
                        with col_w1:
                            wetter1 = st.selectbox("Wetter", wetter_optionen, key="wetter1")
                        with col_w2:
                            wetter2 = st.selectbox(
                                "Wetter",
                                [opt for opt in wetter_optionen if opt != wetter1],
                                key="wetter2"
                            )
                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            boden1 = st.selectbox("Bodenverhältnisse", boden_optionen, key="boden1")
                        with col_b2:
                            boden2 = st.selectbox(
                                "Bodenverhältnisse",
                                [opt for opt in boden_optionen if opt != boden1],
                                key="boden2"
                            )
                        col_temp, col_schlecht = st.columns([2, 1])
                        with col_temp:
                            temperatur = st.number_input("Temperatur (°C)", min_value=-30.0, max_value=50.0, step=1.0, key="temperatur")
                        with col_schlecht:
                            schlechtes_wetter = st.checkbox("Schlechtes Wetter", key="schlechtes_wetter")
                        if st.button("Speichern"):
                            with engine.begin() as conn:
                                conn.execute(
                                    text("""
                                        INSERT INTO wetterdaten (projekt_id, datum, wetter1, wetter2, boden1, boden2, temperatur, schlecht)
                                        VALUES (:projekt_id, :datum, :wetter1, :wetter2, :boden1, :boden2, :temperatur, :schlecht)
                                        ON CONFLICT(projekt_id, datum) DO UPDATE SET
                                            wetter1=excluded.wetter1,
                                            wetter2=excluded.wetter2,
                                            boden1=excluded.boden1,
                                            boden2=excluded.boden2,
                                            temperatur=excluded.temperatur,
                                            schlecht=excluded.schlecht
                                    """),
                                    {
                                        "projekt_id": projekt_id,
                                        "datum": heute,
                                        "wetter1": wetter1,
                                        "wetter2": wetter2,
                                        "boden1": boden1,
                                        "boden2": boden2,
                                        "temperatur": temperatur,
                                        "schlecht": int(schlechtes_wetter)
                                    }
                                )
                            st.success("Wetterdaten gespeichert.")
                            st.rerun()
                   # Geräte-Liste aus dem Lager des Chefs laden
                chef_row = pd.read_sql(
                    "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                )
                chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                df_geraete = pd.read_sql(
                    "SELECT geraet, anzahl FROM geraete_lager WHERE benutzername = %s", engine, params=(chefname,)
                )
                geraete_liste = df_geraete["geraet"].tolist()
                geraete_anzahl_dict = dict(zip(df_geraete["geraet"], df_geraete["anzahl"]))

                # Session-State initialisieren
                if "geraete_expander_unten" not in st.session_state:
                    st.session_state.geraete_expander_unten = False
                # Expander oben (Eingabe)
                if not st.session_state.geraete_expander_unten:
                    st.subheader(" Geräteverwaltung")
                    if "geraetezeilen" not in st.session_state or not st.session_state.geraetezeilen:
                        st.session_state.geraetezeilen = [{"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0}]
                    with st.expander(" Geräte-Verwaltung"):
                        if st.button("Neue Gerätezeile hinzufügen", key="add_geraetezeile"):
                            st.session_state.geraetezeilen.append({"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0})
                        to_delete = []
                        for idx, zeile in enumerate(st.session_state.geraetezeilen):
                            cols = st.columns([4, 2, 2, 1])
                            # Gerät auswählen
                            geraet = cols[0].selectbox(
                                "Gerät",
                                ["-"] + geraete_liste,
                                index=(["-"] + geraete_liste).index(zeile["geraet"]) if zeile["geraet"] in geraete_liste else 0,
                                key=f"geraet_select_{idx}"
                            )
                            st.session_state.geraetezeilen[idx]["geraet"] = geraet
                            # Anzahl
                            max_anzahl = int(geraete_anzahl_dict.get(geraet, 1))
                            anzahl = cols[1].number_input(
                                "Anzahl",
                                min_value=1,
                                max_value=max_anzahl,
                                step=1,
                                value=zeile["anzahl"],
                                key=f"anzahl_input_{idx}"
                            )
                            st.session_state.geraetezeilen[idx]["anzahl"] = anzahl
                            # Nutzungszeit
                            nutzungszeit = cols[2].text_input(
                           "Nutzungszeit in h",
                            value=float(zeile["nutzungszeit"]),
                            key=f"nutzungszeit_input_{idx}"
                            )
                            st.session_state.geraetezeilen[idx]["nutzungszeit"] = nutzungszeit
                            # Löschen-Button
                            if cols[3].button("❌", key=f"delete_geraete_{idx}"):
                                to_delete.append(idx)
                        for idx in sorted(to_delete, reverse=True):
                            del st.session_state.geraetezeilen[idx]
                            st.rerun()
                        # Speichern
                        if st.button("Geräte speichern", key="save_geraete"):
                            projekt_id = st.session_state.get("projekt_id")
                            heute = date.today().strftime("%Y-%m-%d")
                            with engine.begin() as conn:
                                for zeile in st.session_state.geraetezeilen:
                                    geraet = zeile["geraet"]
                                    anzahl = zeile["anzahl"]
                                    nutzungszeit = zeile["nutzungszeit"]
                                    try:
                                        nutzungszeit_float = float(nutzungszeit)
                                    except (ValueError, TypeError):
                                        nutzungszeit_float = 0.0

                                    if geraet != "-" and anzahl > 0 and nutzungszeit_float > 0:
                                        try:
                                            conn.exec_driver_sql("""
                                                DELETE FROM geraete_nutzung
                                                WHERE benutzername = %s AND projekt_id = %s AND geraet = %s AND datum::date = %s::date
                                            """, (st.session_state.user, projekt_id, geraet, heute))
                                            conn.exec_driver_sql("""
                                                INSERT INTO geraete_nutzung (benutzername, projekt_id, geraet, datum, nutzungszeit)
                                                VALUES (%s, %s, %s, %s::date, %s)
                                            """, (st.session_state.user, projekt_id, geraet, heute, nutzungszeit_float))
                                        except Exception as e:
                                            # Transaktion ist fehlgeschlagen, muss neue Transaktion starten
                                            # benutzername Spalte wird in database.py erstellt
                                            # Versuche erneut zu inserieren in neuer Transaktion
                                            try:
                                                with engine.begin() as new_conn:
                                                    new_conn.exec_driver_sql("""
                                                        DELETE FROM geraete_nutzung
                                                        WHERE benutzername = %s AND projekt_id = %s AND geraet = %s AND datum::date = %s::date
                                                    """, (st.session_state.user, projekt_id, geraet, heute))
                                                    new_conn.exec_driver_sql("""
                                                        INSERT INTO geraete_nutzung (benutzername, projekt_id, geraet, datum, nutzungszeit)
                                                        VALUES (%s, %s, %s, %s::date, %s)
                                                    """, (st.session_state.user, projekt_id, geraet, heute, nutzungszeit_float))
                                            except Exception:
                                                st.error(f"Fehler beim Speichern von {geraet}: {str(e)[:100]}")
                            
                            # Eingabe merken und Expander nach unten verschieben
                            st.session_state.geraete_eingabe_gespeichert = [z.copy() for z in st.session_state.geraetezeilen]
                            st.session_state.geraete_eingabe_datum = heute
                            st.session_state.geraete_expander_unten = True
                            st.session_state.geraetezeilen = [{"geraet": "-", "anzahl": 1, "nutzungszeit": 0.0}]
                            st.success(f"Geräte gespeichert: {len(st.session_state.geraete_eingabe_gespeichert)} Einträge")
                            st.rerun()

                if not st.session_state.get("material_expander_unten", False):    
                    st.subheader(" Materialverwaltung")
                    with st.expander("Materialverwaltung für das Projekt"):
                        if "materialzeilen" not in st.session_state or not st.session_state.materialzeilen:
                            st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                        # Lagerdaten laden
                        chef_row = pd.read_sql(
                            "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                        )
                        chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                        df_lager = pd.read_sql(
                            "SELECT material, einheit FROM lagerbestand WHERE benutzername = %s",
                            engine, params=(chefname,)
                        )
                        lager_materialien = df_lager["material"].tolist()
                        einheiten_dict = df_lager.set_index("material")["einheit"].to_dict()
                        # --- Buttons oben: Zeile entfernen links, hinzufügen rechts ---
                        col_add, col_spacer, col_remove= st.columns([2, 6, 2])
                        with col_remove:
                            if st.button("Zeile entfernen", key="remove_material_row") and len(st.session_state.materialzeilen) > 1:
                                st.session_state.materialzeilen.pop()
                                st.rerun()
                        with col_add:
                            if st.button("Zeile hinzufügen", key="add_material_row"):
                                st.session_state.materialzeilen.append({"material": "-", "menge": 0.0, "einheit": ""})
                                st.rerun()
                        # --- Materialauswahl und Eingabe ---
                        to_delete = []
                        for idx, zeile in enumerate(st.session_state.materialzeilen):
                            cols = st.columns([4, 2, 2, 1])
                            mat = cols[0].selectbox(
                                "Material",
                                ["-"] + lager_materialien,
                                index=(["-"] + lager_materialien).index(zeile["material"]) if zeile["material"] in lager_materialien else 0,
                                key=f"material_select_{idx}"
                            )
                            st.session_state.materialzeilen[idx]["material"] = mat
                            einheit = einheiten_dict.get(mat, "")
                            cols[1].write(f"Einheit: {einheit}")
                            menge = cols[2].number_input(
                                "Menge",
                                min_value=0.0,
                                step=1.0,
                                value=zeile["menge"],
                                key=f"menge_input_{idx}"
                            )
                            st.session_state.materialzeilen[idx]["menge"] = menge
                            st.session_state.materialzeilen[idx]["einheit"] = einheit
                        # Speichern-Button
                        if st.button("Materialien speichern", key="save_materialien"):
                            projekt_id = st.session_state.get("projekt_id")
                            heute = date.today().strftime("%Y-%m-%d")
                            chef_row = pd.read_sql(
                                "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                            )
                            chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                            for zeile in st.session_state.materialzeilen:
                                mat = zeile["material"]
                                menge = zeile["menge"]
                                einheit = einheiten_dict.get(mat, "")
                                with engine.begin() as conn:
                                    # datum Spalte wird in database.py erstellt
                                    result = conn.exec_driver_sql("""
                                        SELECT menge, bearbeitet_von_bauunternehmer FROM materialien
                                        WHERE projekt_id = %s AND material = %s AND benutzername = %s AND datum = %s
                                    """, (projekt_id, mat, chefname, heute)).fetchone()
                                    if result:
                                        alte_menge, bearbeitet = result
                                        if bearbeitet == 1:
                                            pass
                                        else:
                                            neue_menge = float(alte_menge) + menge
                                            conn.exec_driver_sql("""
                                                UPDATE materialien SET menge = %s, einheit = %s, bearbeitet_von_bauunternehmer = 0, datum = %s
                                                WHERE projekt_id = %s AND material = %s AND benutzername = %s AND datum = %s
                                            """, (neue_menge, einheit, heute, projekt_id, mat, chefname, heute))
                                    else:
                                        conn.exec_driver_sql("""
                                            INSERT INTO materialien (projekt_id, material, menge, benutzername, einheit, bearbeitet_von_bauunternehmer, datum)
                                            VALUES (%s, %s, %s, %s, %s, 0, %s)
                                        """, (projekt_id, mat, menge, chefname, einheit, heute))
                            st.success("Materialien für das Projekt wurden gespeichert.")
                            st.session_state.material_eingabe_gespeichert = [z.copy() for z in st.session_state.materialzeilen]
                            st.session_state.material_eingabe_datum = heute
                            st.session_state.material_expander_unten = True
                            st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                            st.success(f"Materialien gespeichert: {len(st.session_state.material_eingabe_gespeichert)} Einträge")
                            st.rerun()               
                # Kommentar-Block ersetzen durch eigenen Expander für "Problem"
                st.subheader(" Probleme & zusätzlicher Zeitaufwand")
                with st.expander(" Problem melden / dokumentieren"):
                    # Robust: projekt_id IMMER als Integer setzen
                    projekt_id_int = int(st.session_state.get("projekt_id", projekt_id))
                    benutzername = str(st.session_state.user)
                    heute = date.today().strftime("%Y-%m-%d")
                    with engine.begin() as conn:
                        try:
                            conn.exec_driver_sql("ALTER TABLE checklisten_gesamtkommentar ADD COLUMN zeitaufwand TEXT")
                        except:
                            pass
                    # Problemtext laden (nur für heute!)
                    problem_row = pd.read_sql(
                        "SELECT kommentar, zeitaufwand FROM checklisten_gesamtkommentar WHERE projekt_id = %s AND benutzername = %s AND datum = %s",
                        engine, params=(projekt_id_int, benutzername, heute)
                    )
                    problem_text = problem_row["kommentar"].iloc[0] if not problem_row.empty else ""
                    zeitaufwand = problem_row["zeitaufwand"].iloc[0] if ("zeitaufwand" in problem_row.columns and not problem_row.empty) else ""

                    neuer_problemtext = st.text_area("Problembeschreibung", value=problem_text, height=150, key="problem_text")
                    neue_zeit = st.text_input("Benötigte Zeit (in min.)", value=zeitaufwand, key="problem_zeit")

                    if st.button("Problem speichern"):
                        # Spalte hinzufügen in separater Transaktion
                        try:
                            with engine.begin() as conn:
                                conn.exec_driver_sql("ALTER TABLE checklisten_gesamtkommentar ADD COLUMN zeitaufwand TEXT")
                        except:
                            pass
                        # DELETE und dann INSERT statt ON CONFLICT (da kein UNIQUE Constraint)
                        with engine.begin() as conn:
                            # Zuerst alten Eintrag löschen
                            conn.execute(
                                text("""
                                    DELETE FROM checklisten_gesamtkommentar 
                                    WHERE projekt_id = :projekt_id 
                                    AND benutzername = :benutzername 
                                    AND datum = :datum
                                """),
                                {
                                    "projekt_id": projekt_id_int,
                                    "benutzername": benutzername,
                                    "datum": heute
                                }
                            )
                            # Dann neuen Eintrag einfügen
                            conn.execute(
                                text("""
                                    INSERT INTO checklisten_gesamtkommentar (projekt_id, benutzername, kommentar, zeitaufwand, datum)
                                    VALUES (:projekt_id, :benutzername, :kommentar, :zeitaufwand, :datum)
                                """),
                                {
                                    "projekt_id": projekt_id_int,
                                    "benutzername": benutzername,
                                    "kommentar": neuer_problemtext,
                                    "zeitaufwand": neue_zeit,
                                    "datum": heute
                                }
                            )
                        st.success("Problem und Zeitaufwand gespeichert.")
                        st.rerun()
                # --- Arbeitszeit erfassen ---
                heute = date.today().strftime("%Y-%m-%d")
                arbeitszeit_row = pd.read_sql(
                    "SELECT * FROM arbeitszeiten WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
                    engine, params=(st.session_state.user, projekt_id, heute)
                )
                arbeitszeit_gespeichert = not arbeitszeit_row.empty

                # Expander oben NUR anzeigen, wenn noch NICHT gespeichert!
                if not arbeitszeit_gespeichert:
                    st.subheader(" Arbeitszeit erfassen")
                    with st.expander("+ Neue Zeiterfassung eintragen"):
                        with st.form(f"zeiterfassung_formular_{projekt_id}_{st.session_state.user}"):
                            datum = st.date_input(" Datum", value=date.today())
                            col1, col2, col3 = st.columns([2,2,2])
                            with col1:
                                von = st.time_input(" Von", value=datetime.strptime("08:00", "%H:%M").time())
                            with col2:
                                bis = st.time_input(" Bis", value=datetime.strptime("16:00", "%H:%M").time())
                            with col3:
                                krank = st.toggle("Krankmeldung", value=False, key="krankmeldung")
                            speichern = st.form_submit_button("Eintrag speichern")
                        if speichern:
                            if krank:
                                # Durchschnitt der letzten 91 Tage (nur Werte > 0)
                                df_91d = pd.read_sql(
                                    "SELECT stunden FROM arbeitszeiten WHERE benutzername = %s AND projekt_id = %s AND datum >= %s ORDER BY datum DESC",
                                    engine,
                                    params=(st.session_state.user, projekt_id, (date.today() - timedelta(days=91)).strftime('%Y-%m-%d'))
                                )
                                debug_stunden_liste_pos = [v for v in df_91d["stunden"].tolist() if v > 0]
                                if debug_stunden_liste_pos:
                                    stunden = sum(debug_stunden_liste_pos) / len(debug_stunden_liste_pos)
                                else:
                                    stunden = 0.0
                            else:
                                stunden = (datetime.combine(date.today(), bis) - datetime.combine(date.today(), von)).seconds / 3600
                                if stunden > 6: 
                                    stunden -= 0.5
                                if stunden > 8:
                                    stunden -= 0.25
                                if stunden > 10:
                                    st.warning("Arbeitszeit über 10 Stunden. Maximale Tagesarbeitszeit überschritten.")
                            with engine.begin() as conn:
                                try:
                                    conn.exec_driver_sql("""
                                        INSERT INTO arbeitszeiten (benutzername, projekt_id, datum, startzeit, endzeit, stunden)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (
                                        st.session_state.user,
                                        projekt_id,
                                        datum.strftime("%Y-%m-%d"),
                                        von.strftime("%H:%M"),
                                        bis.strftime("%H:%M"),
                                        stunden
                                    ))
                                except Exception as e:
                                    if "startzeit" in str(e).lower() or "endzeit" in str(e).lower() or "undefinedcolumn" in str(e).lower():
                                        # Spalten hinzufügen
                                        try:
                                            with engine.begin() as new_conn:
                                                new_conn.exec_driver_sql("ALTER TABLE arbeitszeiten ADD COLUMN startzeit TEXT")
                                        except:
                                            pass
                                        try:
                                            with engine.begin() as new_conn:
                                                new_conn.exec_driver_sql("ALTER TABLE arbeitszeiten ADD COLUMN endzeit TEXT")
                                        except:
                                            pass
                       
                                        # Versuche erneut
                                        with engine.begin() as new_conn:
                                            new_conn.exec_driver_sql("""
                                                INSERT INTO arbeitszeiten (benutzername, projekt_id, datum, startzeit, endzeit, stunden)
                                                VALUES (%s, %s, %s, %s, %s, %s)
                                            """, (
                                                st.session_state.user,
                                                projekt_id,
                                                datum.strftime("%Y-%m-%d"),
                                                von.strftime("%H:%M"),
                                                bis.strftime("%H:%M"),
                                                stunden
                                            ))
                                    else:
                                        raise
                            st.success("Arbeitszeit erfolgreich gespeichert.")
                            st.rerun()
                # --- Abgeschlossene Aufgaben ---
                st.markdown("### Abgeschlossene Aufgaben")
                with st.expander("Abgeschlossene Aufgaben anzeigen"):    
                    abgeschlossen_df = checklist_df[checklist_df["erledigt"] == 1]
                    if abgeschlossen_df.empty:
                        st.info("Noch keine Aufgaben abgeschlossen.")
                    else:
                        for _, row in abgeschlossen_df.iterrows():
                            st.markdown(f"- {row['text']}")
                st.markdown ("### Eingetragene Daten")
                if not wetter_gespeichert and not arbeitszeit_gespeichert and not st.session_state.get("geraete_eingabe_gespeichert") and not st.session_state.get("material_eingabe_gespeichert"):
                    st.info("Noch keine Daten für heute eingetragen.")
                # Nach abgeschlossenen Aufgaben, ganz unten im Layout:
                heute = date.today().strftime("%Y-%m-%d")
                wetter_row = pd.read_sql(
                    "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
                    engine, params=(projekt_id, heute)
                )
                wetter_gespeichert = not wetter_row.empty

                    # Wetter-Expander unten NUR anzeigen, wenn Wetterdaten für heute existieren
                if wetter_gespeichert:
                        wetter_title = "Wetter- und Bodenverhältnisse eintragen"
                        with st.expander(wetter_title):
                            st.info("Wetterdaten für heute wurden bereits gespeichert.")
                            st.markdown(
                                "<style>.streamlit-expanderHeader {color: var(--text-color) !important;}</style>",
                                unsafe_allow_html=True
                            )
                            # Werte anzeigen
                            st.write(f"Wetter 1: {wetter_row['wetter1'].iloc[0]}")
                            st.write(f"Wetter 2: {wetter_row['wetter2'].iloc[0]}")
                            st.write(f"Boden 1: {wetter_row['boden1'].iloc[0]}")
                            st.write(f"Boden 2: {wetter_row['boden2'].iloc[0]}")
                            st.write(f"Temperatur: {wetter_row['temperatur'].iloc[0]} °C")
                            st.write(f"Schlechtes Wetter: {'Ja' if wetter_row['schlecht'].iloc[0] else 'Nein'}")
                            col1, col2 = st.columns([8, 2])
                            with col2:
                                if st.button("Bearbeiten", key="wetter_edit"):
                                    with engine.begin() as conn:
                                        conn.execute(
                                            text("DELETE FROM wetterdaten WHERE projekt_id = :projekt_id AND datum = :datum"),
                                            {"projekt_id": projekt_id, "datum": heute}
                                        )
                                    st.rerun()
                heute = date.today().strftime("%Y-%m-%d")
                arbeitszeit_row = pd.read_sql(
                    "SELECT * FROM arbeitszeiten WHERE benutzername = %s AND projekt_id = %s AND datum = %s",
                    engine, params=(st.session_state.user, projekt_id, heute)
                )
                arbeitszeit_gespeichert = not arbeitszeit_row.empty

                arbeitszeit_title = "+ Neue Zeiterfassung eintragen"
                if arbeitszeit_gespeichert:
                    arbeitszeit_title += ""
                    with st.expander(arbeitszeit_title):
                        st.info("Arbeitszeit für heute wurde bereits gespeichert.")
                        st.markdown(
                            "<style>.streamlit-expanderHeader {color: var(--text-color) !important;}</style>",
                            unsafe_allow_html=True
                        )
                        # Werte anzeigen
                        row = arbeitszeit_row.iloc[0]
                        st.write(f"Von: {row['startzeit']} Uhr")
                        st.write(f"Bis: {row['endzeit']} Uhr")
                        st.write(f"Stunden: {row['stunden']:.2f}")
                        col1, col2 = st.columns([8, 2])
                        with col2:
                            if st.button("Bearbeiten", key="arbeitszeit_edit"):
                                with engine.begin() as conn:
                                    conn.execute(
                                        text("DELETE FROM arbeitszeiten WHERE benutzername = :benutzername AND projekt_id = :projekt_id AND datum = :datum"),
                                        {"benutzername": st.session_state.user, "projekt_id": projekt_id, "datum": heute}
                                    )
                                st.rerun()
                if st.session_state.geraete_expander_unten:
                    with st.expander("Geräteverwaltung für das Projekt", expanded=True):
                        eingabe = st.session_state.get("geraete_eingabe_gespeichert", [])
                        if not eingabe:
                            st.info("Keine Geräte-Eingabe für heute vorhanden.")
                        else:
                            st.info("Geräte wurden heute bereits eingegeben.")
                            for z in eingabe:
                                geraet = z.get("geraet", "-")
                                anzahl = z.get("anzahl", 0)
                                nutzungszeit = z.get("nutzungszeit", "")
                                # Versuche die Nutzungszeit als Zahl zu interpretieren, sonst als Text anzeigen
                                try:
                                    nutzungszeit_float = float(nutzungszeit)
                                except (ValueError, TypeError):
                                    nutzungszeit_float = None
                                # Zeige nur sinnvolle Einträge
                                if geraet != "-" and int(anzahl) > 0 and nutzungszeit:
                                    st.write(f"{geraet}: {anzahl} Stück, Nutzungszeit: {nutzungszeit} Std.")
                        if st.button("Bearbeiten", key="edit_geraete"):
                            # Geräte-Nutzungen für heute löschen
                            projekt_id = st.session_state.get("projekt_id")
                            heute = st.session_state.get("geraete_eingabe_datum", date.today().strftime("%Y-%m-%d"))
                            with engine.begin() as conn:
                                for zeile in eingabe:
                                    geraet = zeile.get("geraet", "-")
                                    if geraet != "-":
                                        conn.exec_driver_sql("""
                                            DELETE FROM geraete_nutzung WHERE benutzername = %s AND projekt_id = %s AND geraet = %s AND datum::date = %s::date
                                        """, (st.session_state.user, projekt_id, geraet, heute))
                            st.session_state.geraete_expander_unten = False
                            st.session_state.geraetezeilen = eingabe.copy()
                            st.session_state.geraete_eingabe_gespeichert = []
                            st.rerun()
                if st.session_state.get("material_expander_unten", False):
                    # Prüfe, ob die gespeicherten Werte nur '-' und 0.0 sind (Mitternachts-Reset)
                    eingabe = st.session_state.get("material_eingabe_gespeichert", [])
                    mitternacht_reset = (
                        eingabe and all(z.get("material") == "-" and z.get("menge") == 0.0 for z in eingabe)
                    )
                    # Nur zurücksetzen, wenn Expander noch unten ist und Mitternachtsreset erkannt wird
                    if mitternacht_reset and st.session_state.material_expander_unten:
                        st.session_state.material_expander_unten = False
                        st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                        st.session_state.material_eingabe_gespeichert = []
                        st.rerun()
                    else:
                        with st.expander("Materialverwaltung für das Projekt", expanded=True):
                            if not eingabe:
                                st.info("Keine Eingabe für heute vorhanden.")
                            else:
                                st.info("Material wurde heute bereits eingegeben.")
                                for zeile in eingabe:
                                    mat = zeile["material"]
                                    menge = zeile["menge"]
                                    einheit = ""
                                    if "einheiten_dict" in locals():
                                        einheit = einheiten_dict.get(mat, "")
                                    else:
                                        # Fallback: Einheit aus DB holen
                                        df_lager = pd.read_sql(
                                            "SELECT einheit FROM lagerbestand WHERE material = %s",
                                            engine, params=(mat,)
                                        )
                                        einheit = df_lager["einheit"].iloc[0] if not df_lager.empty else ""
                                    st.write(f"{mat}: {menge} {einheit}")
                            if st.button("Bearbeiten", key="edit_materialien"):
                                # Manuelles Zurücksetzen: Einträge von HEUTE aus materialien löschen
                                projekt_id = st.session_state.get("projekt_id")
                                heute = st.session_state.get("material_eingabe_datum", date.today().strftime("%Y-%m-%d"))
                                chef_row = pd.read_sql(
                                    "SELECT chefname FROM mitarbeiter WHERE benutzername = %s", engine, params=(st.session_state.user,)
                                )
                                chefname = chef_row["chefname"].iloc[0] if not chef_row.empty else ""
                                try:
                                    with engine.begin() as conn:
                                        # DELETE heutige Einträge aus materialien (wo datum = heute)
                                        conn.exec_driver_sql(
                                            "DELETE FROM materialien WHERE projekt_id = %s AND benutzername = %s AND datum = %s",
                                            (projekt_id, chefname, heute)
                                        )
                                    st.session_state.material_expander_unten = False
                                    st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                                    st.session_state.material_eingabe_gespeichert = []
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Fehler beim Löschen: {str(e)[:100]}")
                
                if st.session_state.get("material_expander_unten", False):
                    # Prüfe, ob die gespeicherten Werte nur '-' und 0.0 sind (Mitternachts-Reset)
                    eingabe = st.session_state.get("material_eingabe_gespeichert", [])
                    mitternacht_reset = (
                        eingabe and all(z.get("material") == "-" and z.get("menge") == 0.0 for z in eingabe)
                    )
                    # Nur zurücksetzen, wenn Expander noch unten ist und Mitternachtsreset erkannt wird
                    if mitternacht_reset and st.session_state.material_expander_unten:
                        st.session_state.material_expander_unten = False
                        st.session_state.materialzeilen = [{"material": "-", "menge": 0.0, "einheit": ""}]
                        st.session_state.material_eingabe_gespeichert = []
                        st.rerun()
            
            else:
                st.warning("Projekt nicht gefunden.")
        else:
            st.warning("Kein Projekt zugewiesen.")  

# === Developer Auth Page ===
