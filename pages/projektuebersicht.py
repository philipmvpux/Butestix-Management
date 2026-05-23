# ============================================================
#  pages/projektuebersicht.py  –  ETA Baumanagement
#  Import in BETA_0_9.py:
#      from pages.projektuebersicht import projektuebersicht_page
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

def projektuebersicht_page():
        st.header("Projektübersicht")       
        # OPTIMIERT: Eine einzige Query statt 3+ pro Projekt
        @st.cache_data(ttl=300)
        def load_projects_with_costs(user):
            query = """
            SELECT 
                p.id, p.name, p.budget, p.datum,
                COALESCE((
                    SELECT COUNT(*) FROM mitarbeiter_projekte mp 
                    WHERE mp.projekt_id = p.id
                ), 0) as worker_count,
                COALESCE((
                    SELECT SUM(COALESCE(nettobetrag, 0)) FROM rechnungen r 
                    WHERE r.projekt_name = p.name AND r.benutzername = %s
                ), 0) as rechnung_total,
                COALESCE((
                    SELECT SUM(COALESCE(m.menge, 0) * COALESCE(l.preis_ankauf, 0))
                    FROM materialien m 
                    LEFT JOIN lagerbestand l ON m.material = l.material
                    WHERE m.projekt_id = p.id AND m.benutzername = %s
                ), 0) as material_kosten
            FROM projekte p
            WHERE p.benutzername = %s AND p.archiviert_am IS NULL
            ORDER BY p.datum DESC
            """
            return pd.read_sql(query, engine, params=(user, user, user))
        
        df = load_projects_with_costs(st.session_state.user)
        if not df.empty:
            for index, row in df.iterrows():
                project_date = pd.to_datetime(row['datum'])
                days_since = (pd.Timestamp.today() - project_date).days
                if days_since == 0:
                    time_str = "Heute erstellt"
                elif days_since == 1:
                    time_str = "Vor 1 Tag"
                elif days_since < 7:
                    time_str = f"Vor {days_since} Tagen"
                elif days_since < 30:
                    weeks = days_since // 7
                    time_str = f"Vor {weeks} Woche(n)"
                else:
                    months = days_since // 30
                    time_str = f"Vor {months} Monat(en)"
                
                worker_count = int(row['worker_count'])
                rechnung_total = float(row['rechnung_total'])
                material_kosten = float(row['material_kosten'])
                gesamt_kosten = rechnung_total + material_kosten
                budget_diff = float(row['budget']) - gesamt_kosten
                
                with st.expander(f"{row['name']} – {int(row['budget'])} €"):
                    st.markdown(f"**Zeit seit Erstellung:** {time_str}")
                    st.markdown(f"**Mitarbeiter zugewiesen:** {worker_count}")
                    
                    if budget_diff > 0:
                        st.markdown(f"**Budget noch verfügbar:** <span style='color: #4CAF50;'>{budget_diff:.2f} € </span>", unsafe_allow_html=True)
                    elif budget_diff < 0:
                        st.markdown(f"**Budget überschritten um:** <span style='color: #ff9800;'>{abs(budget_diff):.2f} €</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Budget:** <span style='color: #2196F3;'>Exakt ausgegeben</span>", unsafe_allow_html=True)

                    col1, col2, col3 = st.columns([2, 6, 2])
                    with col1:
                        if st.button("Archivieren", key=f"archive_{row['id']}", help="Projekt archivieren"):
                            st.session_state[f"confirm_archive_{row['id']}"] = True
                    with col3:
                        if st.button("Löschen", key=f"delete_{row['id']}", help="Projekt löschen"):
                            st.session_state[f"confirm_delete_{row['id']}"] = True
                
                # Archivierungs-Bestätigung (1. Abfrage)
                if st.session_state.get(f"confirm_archive_{row['id']}", False):
                    st.warning(f"Möchtest du das Projekt **{row['name']}** wirklich abschließen und archivieren?")
                    st.markdown("**Diese Aktion:**")
                    st.markdown("- ✓ Archiviert das Projekt und alle Daten")
                    st.markdown("- ✓ Entfernt Mitarbeiter aus dem Projekt")
                    st.markdown("- ✓ Zieht verbrauchte Materialien vom Lagerbestand ab")
                    st.markdown("- ✓ Aktualisiert die Geräte-Nutzung")
                    st.markdown("- ✗ Das Projekt kann nach der Archivierung nicht mehr bearbeitet werden")
                    
                    archive_col1, archive_col2, archive_col3 = st.columns(3)
                    with archive_col1:
                        if st.button("Ja, archivieren", key=f"confirm_archive_yes_{row['id']}"):
                            st.session_state[f"confirm_archive_double_{row['id']}"] = True
                    with archive_col2:
                        if st.button("Abbrechen", key=f"confirm_archive_no_{row['id']}"):
                            del st.session_state[f"confirm_archive_{row['id']}"]
                            st.rerun()
                
                # DOPPELTE BESTÄTIGUNG für Archivierung
                if st.session_state.get(f"confirm_archive_double_{row['id']}", False):
                    st.error(f" LETZTE BESTÄTIGUNG: Das Projekt **{row['name']}** wird archiviert. Diese Aktion kann nicht rückgängig gemacht werden!")
                    final_col1, final_col2 = st.columns(2)
                    with final_col1:
                        if st.button("JA, ENDGÜLTIG ARCHIVIEREN", key=f"final_archive_{row['id']}"):
                            # === ARCHIVIERUNGS-LOGIK ===
                            try:
                                with engine.begin() as conn:
                                    # 1. Materialien vom Lagerbestand abziehen
                                    materialien_project = pd.read_sql(
                                        "SELECT material, menge FROM materialien WHERE projekt_id = %s AND benutzername = %s",
                                        engine, params=(row['id'], st.session_state.user)
                                    )
                                    for _, mat in materialien_project.iterrows():
                                        menge = float(mat['menge']) if pd.notnull(mat['menge']) else 0.0
                                        if menge > 0:
                                            conn.exec_driver_sql(
                                                "UPDATE lagerbestand SET menge = menge - %s WHERE material = %s AND benutzername = %s",
                                                (menge, mat['material'], st.session_state.user)
                                            )
                                    
                                    # 2. Mitarbeiter aus Projekt entfernen
                                    conn.exec_driver_sql(
                                        "DELETE FROM mitarbeiter_projekte WHERE projekt_id = %s",
                                        (row['id'],)
                                    )
                                    
                                    # 3. Projekt archivierungsdatum setzen (wird in den 3 archiven gespeichert)
                                    conn.exec_driver_sql(
                                        "UPDATE projekte SET archiviert_am = %s WHERE id = %s",
                                        (date.today().strftime("%Y-%m-%d"), row['id'])
                                    )
                                
                                st.success(f"Projekt **{row['name']}** wurde erfolgreich archiviert!")
                                del st.session_state[f"confirm_archive_{row['id']}"]
                                del st.session_state[f"confirm_archive_double_{row['id']}"]
                                st.rerun()
                            except Exception as e:
                                st.error(f"Fehler beim Archivieren: {str(e)}")
                    with final_col2:
                        if st.button("ABBRECHEN", key=f"final_archive_no_{row['id']}"):
                            del st.session_state[f"confirm_archive_{row['id']}"]
                            del st.session_state[f"confirm_archive_double_{row['id']}"]
                            st.rerun()
                
                # Lösch-Bestätigung (alte Logik)
                if st.session_state.get(f"confirm_delete_{row['id']}", False):
                    st.warning(f"Möchtest du das Projekt **{row['name']}** wirklich löschen?")
                    confirm_col1, confirm_col2 = st.columns(2)
                    with confirm_col1:
                        if st.button("Ja, löschen", key=f"confirm_yes_{row['id']}"):
                            with engine.begin() as conn:
                                conn.exec_driver_sql("DELETE FROM projekte WHERE id = %s", (row['id'],))
                            st.success(f"Projekt **{row['name']}** wurde gelöscht.")
                            del st.session_state[f"confirm_delete_{row['id']}"]
                            st.rerun()
                            sync_materialien()
                    with confirm_col2:
                        if st.button("Abbrechen", key=f"confirm_no_{row['id']}"):
                            del st.session_state[f"confirm_delete_{row['id']}"]
        
        # Neu abrufen für die HTML-Tabelle
        df = pd.read_sql("SELECT id, name, budget, datum FROM projekte WHERE benutzername = %s AND archiviert_am IS NULL", engine, params=(st.session_state.user,))
        if not df.empty:
            st.subheader("Projektübersicht - Tabelle")
            # HTML-Tabelle für Projektübersicht
            table_html = "<style>.scroll-table-wrapper{overflow-x:auto;border:1px solid var(--box-border);background:var(--box-bg);padding:1rem;border-radius:8px;}.scroll-table{border-collapse:collapse;width:100%;}.scroll-table th,.scroll-table td{border:1px solid var(--box-border);padding:0.75rem 1rem;text-align:left;color:var(--text-color);}.scroll-table th{background:var(--table-header-bg);font-weight:600;}.scroll-table tbody tr:hover{background:rgba(255,255,255,0.05);}</style>"
            table_html += "<div class='scroll-table-wrapper'><table class='scroll-table'><thead><tr><th>Projektname</th><th>Budget (€)</th><th>Kosten (€)</th><th>Dauer seit Erstellung</th><th>Mitarbeiter</th></tr></thead><tbody>"
            
            for _, row in df.iterrows():
                budget_formatted = f"{float(row['budget']):.2f}" if pd.notnull(row['budget']) else "0.00"
                
                # Berechne Zeit seit Erstellung
                project_date = pd.to_datetime(row['datum'])
                days_since = (pd.Timestamp.today() - project_date).days
                if days_since == 0:
                    time_str = "Heute"
                elif days_since == 1:
                    time_str = "1 Tag"
                elif days_since < 7:
                    time_str = f"{days_since} Tage"
                elif days_since < 30:
                    weeks = days_since // 7
                    time_str = f"{weeks} Wo."
                else:
                    months = days_since // 30
                    time_str = f"{months} Mo."
                
                # Zähle Mitarbeiter
                mitarbeiter_count = pd.read_sql("SELECT COUNT(*) as count FROM mitarbeiter_projekte WHERE projekt_id = %s", engine, params=(row['id'],))
                worker_count = int(mitarbeiter_count['count'].iloc[0]) if not mitarbeiter_count.empty else 0
                
                # Berechne Kosten aus bereits erstellten Rechnungen + ungefähre Schätzung aus Materialien + Geräte-Nutzung
                # 1. Summe der Netto-Beträge aus abgerechneten Rechnungen
                rechnungen_kosten = pd.read_sql("SELECT COALESCE(SUM(nettobetrag), 0) as gesamt FROM rechnungen WHERE projekt_name = %s AND benutzername = %s", engine, params=(row['name'], st.session_state.user))
                rechnung_total = float(rechnungen_kosten['gesamt'].iloc[0]) if not rechnungen_kosten.empty else 0.0
                
                # 2. Ungefähre Materialkosten aus dem Lagerbestand
                materialien_data = pd.read_sql("SELECT m.menge, m.einheit, l.preis_ankauf FROM materialien m LEFT JOIN lagerbestand l ON m.material = l.material WHERE m.projekt_id = %s", engine, params=(row['id'],))
                material_kosten = 0.0
                if not materialien_data.empty:
                    for _, mat_row in materialien_data.iterrows():
                        menge = float(mat_row['menge']) if pd.notnull(mat_row['menge']) else 0.0
                        preis = float(mat_row['preis_ankauf']) if pd.notnull(mat_row['preis_ankauf']) else 0.0
                        material_kosten += menge * preis
                
                # 3. Geräte-Nutzungskosten
                geraete_nutzung_data = pd.read_sql(
                    """SELECT gn.geraet, gn.nutzungszeit, gl.betriebskosten 
                       FROM geraete_nutzung gn 
                       LEFT JOIN geraete_lager gl ON gn.geraet = gl.geraet 
                       WHERE gn.projekt_id = %s""", 
                    engine, params=(row['id'],))
                geraete_kosten = 0.0
                if not geraete_nutzung_data.empty:
                    for _, geraete_row in geraete_nutzung_data.iterrows():
                        nutzungszeit = float(geraete_row['nutzungszeit']) if pd.notnull(geraete_row['nutzungszeit']) else 0.0
                        betriebskosten = float(geraete_row['betriebskosten']) if pd.notnull(geraete_row['betriebskosten']) else 0.0
                        # Berechne Kosten: nutzungszeit (Stunden) * betriebskosten (€/Stunde)
                        geraete_kosten += nutzungszeit * betriebskosten
                
                # Gesamtkosten (bereits abgerechnet + geschätzte Materialien + Geräte-Nutzung)
                gesamt_kosten = rechnung_total + material_kosten + geraete_kosten
                kosten_formatted = f"≈ {gesamt_kosten:.2f}"  # ≈ zeigt an, dass es ungefähre Werte sind
                
                table_html += f"<tr><td><strong>{row['name']}</strong></td><td>{budget_formatted}</td><td>{kosten_formatted}</td><td>{time_str}</td><td>{worker_count}</td></tr>"
            
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("Noch keine Projekte eingetragen.")
