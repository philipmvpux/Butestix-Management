

import textwrap
import traceback
from datetime import date
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database import engine


# ============================================================
#  DATEN SPEICHERN / LADEN
# ============================================================

def save_bericht_daten_to_archive(
    benutzername, projekt_id,
    wetter="", boden="", arbeitsbericht="", mitarbeiter="",
    materialeinsatz="", geraeteeinsatz="", probleme="", todo="",
    checklisten_data="", erstellt_von_admin=0
) -> bool:
    """Bericht-Daten (kein PDF) in der Datenbank speichern."""
    today = date.today().strftime("%Y-%m-%d")
    logs  = []

    def _log(msg):
        logs.append(msg)
        print(msg)

    _log(f"{'='*60}")
    _log(f"save_bericht_daten_to_archive() — Benutzer={benutzername} Projekt={projekt_id} Datum={today}")

    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO bericht_daten_archive (
                    benutzername, projekt_id, datum,
                    wetter, boden, arbeitsbericht, mitarbeiter,
                    materialeinsatz, geraeteeinsatz, probleme, todo,
                    checklisten_data, erstellt_von_admin, aktualisiert_am
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_TIMESTAMP)
                ON CONFLICT(benutzername, projekt_id, datum)
                DO UPDATE SET
                    wetter            = excluded.wetter,
                    boden             = excluded.boden,
                    arbeitsbericht    = excluded.arbeitsbericht,
                    mitarbeiter       = excluded.mitarbeiter,
                    materialeinsatz   = excluded.materialeinsatz,
                    geraeteeinsatz    = excluded.geraeteeinsatz,
                    probleme          = excluded.probleme,
                    todo              = excluded.todo,
                    checklisten_data  = excluded.checklisten_data,
                    erstellt_von_admin= excluded.erstellt_von_admin,
                    aktualisiert_am   = CURRENT_TIMESTAMP
                """,
                (benutzername, projekt_id, today,
                 wetter, boden, arbeitsbericht, mitarbeiter,
                 materialeinsatz, geraeteeinsatz, probleme, todo,
                 checklisten_data, erstellt_von_admin)
            )
        _log("✅ INSERT/UPDATE erfolgreich")

        if "archive_debug_logs" not in st.session_state:
            st.session_state.archive_debug_logs = []
        st.session_state.archive_debug_logs.append("\n".join(logs))
        return True

    except Exception as e:
        _log(f"❌ FEHLER: {type(e).__name__}: {e}")
        _log(traceback.format_exc())
        if "archive_debug_logs" not in st.session_state:
            st.session_state.archive_debug_logs = []
        st.session_state.archive_debug_logs.append("\n".join(logs))
        return False


def load_bericht_daten_from_archive(benutzername, projekt_id, datum) -> dict | None:
    """Bericht-Daten für einen bestimmten Tag laden."""
    try:
        result = pd.read_sql(
            """SELECT wetter, boden, arbeitsbericht, mitarbeiter,
                      materialeinsatz, geraeteeinsatz, probleme, todo, checklisten_data
               FROM bericht_daten_archive
               WHERE benutzername = %s AND projekt_id = %s AND datum = %s""",
            engine, params=(benutzername, projekt_id, datum)
        )
        return result.iloc[0].to_dict() if not result.empty else None
    except Exception:
        return None


def save_pdf_to_archive(benutzername, projekt_id, pdf_bytes) -> bool:
    """PDF-BLOB in der Datenbank speichern (für Rechnungen)."""
    today = date.today().strftime("%Y-%m-%d")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                INSERT INTO pdf_archive (benutzername, projekt_id, datum, pdf_blob, aktualisiert_am)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT(benutzername, projekt_id, datum)
                DO UPDATE SET pdf_blob = excluded.pdf_blob, aktualisiert_am = CURRENT_TIMESTAMP
                """,
                (benutzername, projekt_id, today, pdf_bytes)
            )
        return True
    except Exception:
        return False


def load_pdf_from_archive(benutzername, projekt_id, datum) -> bytes | None:
    """PDF-BLOB aus der Datenbank laden."""
    try:
        result = pd.read_sql(
            "SELECT pdf_blob FROM pdf_archive WHERE benutzername=%s AND projekt_id=%s AND datum=%s",
            engine, params=(benutzername, projekt_id, datum)
        )
        if result.empty:
            return None
        pdf_data = result.iloc[0]["pdf_blob"]
        return bytes(pdf_data) if isinstance(pdf_data, memoryview) else pdf_data
    except Exception:
        return None


# ============================================================
#  AUTOMATISCHE PDF-GENERIERUNG (Scheduler)
# ============================================================

def auto_generate_pdfs_at_2355():
    """Um 23:55 Uhr: Platzhalter-Einträge für alle aktiven Projekte speichern."""
    try:
        active = pd.read_sql(
            "SELECT DISTINCT bauunternehmer, id FROM projekte WHERE status = 'aktiv'", engine
        )
        for _, project in active.iterrows():
            try:
                save_bericht_daten_to_archive(
                    benutzername=project["bauunternehmer"],
                    projekt_id=project["id"],
                    arbeitsbericht="[Automatisch um 23:55 Uhr erstellt]",
                    erstellt_von_admin=1,
                )
            except Exception:
                pass
    except Exception:
        pass


def init_pdf_scheduler() -> bool:
    """APScheduler starten: automatische Einträge um 23:55 Uhr."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        if not scheduler.running:
            scheduler.add_job(
                auto_generate_pdfs_at_2355,
                "cron", hour=23, minute=55,
                id="auto_pdf_generation", replace_existing=True,
            )
            scheduler.start()
            return True
    except Exception:
        pass
    return False


# ============================================================
#  UI – BERICHT-ARCHIV
# ============================================================

def berichtarchiv_page():
    st.set_page_config(page_title="Bericht-Archiv", layout="centered")

    col_head, col_btn = st.columns([8, 2])
    with col_head:
        st.title("Tagesbericht-Archiv")
    with col_btn:
        st.button("Zurück", on_click=lambda: st.session_state.update(page="profil"))

    st.info("Für jedes Projekt und beliebiges Datum einen Tagesbericht als PDF erstellen.")

    projekte = pd.read_sql(
        "SELECT id, name FROM projekte WHERE benutzername = %s",
        engine, params=(st.session_state.user,)
    )
    if projekte.empty:
        st.info("Noch keine Projekte vorhanden.")
        return

    for _, projekt in projekte.iterrows():
        with st.expander(f"Projekt: {projekt['name']}"):
            datum = st.date_input(
                f"Berichtsdatum für {projekt['name']}",
                value=date.today(),
                key=f"archiv_datum_{projekt['id']}"
            )

            if st.button(
                f"Bericht für {datum.strftime('%d.%m.%Y')} erstellen",
                key=f"archiv_pdf_{projekt['id']}"
            ):
                pdf_buffer = _erstelle_tagesbericht_pdf(projekt, datum)
                st.success(f"PDF für {datum.strftime('%d.%m.%Y')} erstellt!")
                st.download_button(
                    "📥 PDF herunterladen",
                    pdf_buffer,
                    file_name=f"Bericht_{projekt['name']}_{datum.strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                )


def _erstelle_tagesbericht_pdf(projekt, datum) -> BytesIO:
    """Tagesbericht-PDF für ein Projekt und Datum erzeugen."""
    heute_str  = datum.strftime("%Y-%m-%d")
    buffer     = BytesIO()
    c          = canvas.Canvas(buffer, pagesize=A4)
    firmenname = st.session_state.get("firmenname", "")
    y          = 800

    # ── Kopfzeile ────────────────────────────────────────────
    c.setFont("Helvetica", 20)
    c.drawString(50, y, firmenname)
    y -= 25
    c.setLineWidth(2)
    c.setDash(6, 6)
    c.line(40, y, 550, y)
    c.setDash()
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Datum: {heute_str}")
    y -= 30

    # ── Wetterdaten ──────────────────────────────────────────
    wetter_row = pd.read_sql(
        "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
        engine, params=(projekt["id"], heute_str)
    )
    c.setLineWidth(1)
    c.setDash()
    c.line(40, y, 550, y)
    y -= 20

    if not wetter_row.empty:
        w = wetter_row.iloc[0]
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Wetter:")
        c.setFont("Helvetica", 10)
        c.drawString(170, y, str(w["wetter1"]))
        c.drawString(300, y, str(w["wetter2"]))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(390, y, "Temperatur:")
        c.setFont("Helvetica", 10)
        c.drawString(490, y, f"{w['temperatur']} °C")
        y -= 20
        c.line(40, y, 550, y)
        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Bodenverhältnisse:")
        c.setFont("Helvetica", 10)
        c.drawString(170, y, str(w["boden1"]))
        c.drawString(300, y, str(w["boden2"]))
        y -= 20
        c.line(40, y, 550, y)
        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Schlechtes Wetter:")
        c.setFont("Helvetica", 10)
        c.drawString(170, y, "Ja" if w["schlecht"] else "Nein")
        y -= 20

    c.line(40, y, 550, y)
    y -= 20

    # ── Anzahl Arbeitskräfte ──────────────────────────────────
    ak_df = pd.read_sql(
        "SELECT COUNT(DISTINCT benutzername) AS anzahl FROM arbeitszeiten WHERE projekt_id=%s AND datum=%s",
        engine, params=(projekt["id"], heute_str)
    )
    anzahl_ak = ak_df["anzahl"].iloc[0] if not ak_df.empty else 0
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Anzahl AK:")
    c.setFont("Helvetica", 10)
    c.drawString(170, y, str(anzahl_ak))
    y -= 20
    c.line(40, y, 550, y)
    y -= 20

    # ── Ausgeführte Arbeiten (Checkliste) ─────────────────────
    df_check = pd.read_sql(
        "SELECT * FROM checklistenpunkte WHERE projekt_id=%s AND erledigt=1 AND erledigt_am=%s ORDER BY id",
        engine, params=(projekt["id"], heute_str)
    )
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Ausgeführte Arbeiten:")
    y -= 20
    c.setFont("Helvetica", 10)
    for _, row in df_check.iterrows():
        c.drawString(60, y, f"- {row['text']}")
        y -= 15
        if y < 100:
            c.showPage()
            y = 800

    # Fortschritt-Kommentar
    fk = pd.read_sql(
        "SELECT kommentar FROM checklisten_fortschrittkommentar WHERE projekt_id=%s AND datum=%s",
        engine, params=(projekt["id"], heute_str)
    )
    if not fk.empty and fk["kommentar"].iloc[0] and str(fk["kommentar"].iloc[0]).strip():
        c.drawString(60, y, f"- {fk['kommentar'].iloc[0]}")
        y -= 15
    y -= 20

    # ── Probleme & Zeitaufwand ────────────────────────────────
    problem_row = pd.read_sql(
        "SELECT kommentar, zeitaufwand FROM checklisten_gesamtkommentar WHERE projekt_id=%s AND kommentar!='' AND datum=%s",
        engine, params=(projekt["id"], heute_str)
    )
    if not problem_row.empty:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, "Problem & Zeitaufwand:")
        y -= 18
        for _, row in problem_row.iterrows():
            for line in textwrap.wrap(row["kommentar"] or "", width=50):
                c.setFont("Helvetica", 10)
                c.drawString(60, y, line)
                y -= 20
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"Benötigte Zeit: {row['zeitaufwand']} min.")
            y -= 20

    # ── Mitarbeiter + Geräte nebeneinander ───────────────────
    mitarbeiter_df = pd.read_sql(
        """SELECT m.benutzername, m.vorname, m.nachname, m.rolle,
                  COALESCE(SUM(a.stunden), 0) as stunden
           FROM mitarbeiter m
           INNER JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
           LEFT JOIN arbeitszeiten a
               ON m.benutzername = a.benutzername AND a.projekt_id = mp.projekt_id AND a.datum = %s
           WHERE mp.projekt_id = %s
           GROUP BY m.benutzername, m.vorname, m.nachname, m.rolle""",
        engine, params=(heute_str, projekt["id"])
    )
    geraete_df = pd.read_sql(
        "SELECT geraet, nutzungszeit FROM geraete_nutzung WHERE projekt_id=%s AND datum::date=%s::date",
        engine, params=(projekt["id"], heute_str)
    )

    y_tab   = y
    x_links = 40
    x_rechts = 320

    # Mitarbeitertabelle
    c.setLineWidth(1)
    c.line(x_links, y_tab, x_links + 255, y_tab)
    y_m = y_tab - 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_links + 10, y_m, "Mitarbeiter")
    c.drawString(x_links + 205, y_m, "Stunden")
    y_m -= 10
    c.line(x_links, y_m, x_links + 255, y_m)
    y_m -= 20
    c.setFont("Helvetica", 10)
    for _, row in mitarbeiter_df.iterrows():
        name = f"{row['vorname']} {row['nachname']} ({row['rolle'] or '-'})"
        c.drawString(x_links + 10, y_m, name)
        c.drawString(x_links + 225, y_m, f"{row['stunden']:.2f}")
        y_m -= 15

    # Gerätetabelle
    c.line(x_rechts, y_tab, x_rechts + 255, y_tab)
    y_g = y_tab - 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_rechts + 10, y_g, "Geräte")
    c.drawString(x_rechts + 205, y_g, "Stunden")
    y_g -= 10
    c.line(x_rechts, y_g, x_rechts + 255, y_g)
    y_g -= 20
    c.setFont("Helvetica", 10)
    for _, row in geraete_df.iterrows():
        try:
            nutzung = float(row["nutzungszeit"]) if pd.notnull(row["nutzungszeit"]) else 0.0
            c.drawString(x_rechts + 10, y_g, str(row["geraet"]))
            c.drawString(x_rechts + 225, y_g, f"{nutzung:.2f}")
            y_g -= 15
        except Exception:
            pass

    # ── Materialtabelle ───────────────────────────────────────
    y_mat = min(y_m, y_g) - 18
    c.line(x_links, y_mat + 18, x_links + 255, y_mat + 18)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_links + 10, y_mat, "Material")
    c.drawString(x_links + 210, y_mat, "Menge")
    y_mat -= 10
    c.line(x_links, y_mat, x_links + 255, y_mat)
    y_mat -= 20
    material_df = pd.read_sql(
        "SELECT material, menge, einheit FROM materialien WHERE projekt_id=%s AND datum=%s",
        engine, params=(projekt["id"], heute_str)
    )
    c.setFont("Helvetica", 10)
    for _, row in material_df.iterrows():
        try:
            menge = float(row["menge"]) if pd.notnull(row["menge"]) else 0.0
            einheit = str(row["einheit"]) if pd.notnull(row["einheit"]) else ""
            c.drawString(x_links + 10, y_mat, str(row["material"]))
            c.drawString(x_links + 180, y_mat, f"{menge:.2f} {einheit}")
            y_mat -= 15
        except Exception:
            pass

    c.save()
    buffer.seek(0)
    return buffer


# ============================================================
#  UI – RECHNUNGS-ARCHIV
# ============================================================

def rechnungarchiv_page():
    st.set_page_config(page_title="Rechnungs-Archiv", layout="centered")

    col_head, col_btn = st.columns([8, 2])
    with col_head:
        st.title("Rechnungs-Archiv")
    with col_btn:
        if st.button("← Zurück zum Profil"):
            st.session_state.page = "profil"
            st.rerun()

    current_user = st.session_state.get("user")
    if not current_user:
        st.info("Bitte melde dich an, um dein Rechnungs-Archiv zu sehen.")
        return

    df_all = pd.read_sql(
        """
        SELECT r.id, r.projekt_name, r.rechnungsnummer, r.erstellt_am
        FROM rechnungen r
        WHERE (
            r.benutzername = %s
            OR (
                (r.benutzername IS NULL OR r.benutzername = '')
                AND EXISTS (
                    SELECT 1 FROM projekte p
                    WHERE (p.projekt_name = r.projekt_name OR p.name = r.projekt_name)
                      AND p.benutzername = %s
                )
            )
        )
        ORDER BY r.erstellt_am DESC
        """,
        engine, params=(current_user, current_user)
    )

    df_latest = (
        df_all
        .sort_values("erstellt_am", ascending=False)
        .drop_duplicates(subset=["projekt_name"], keep="first")
    )

    if df_latest.empty:
        st.info("Noch keine Rechnungen vorhanden.")
        return

    auswahl_liste = [f"{row['erstellt_am']} – {row['projekt_name']}" for _, row in df_latest.iterrows()]
    projekt_map   = {f"{row['erstellt_am']} – {row['projekt_name']}": row["projekt_name"] for _, row in df_latest.iterrows()}

    label          = st.selectbox("Projekt auswählen", auswahl_liste)
    projekt_name   = projekt_map.get(label)

    if not projekt_name:
        return

    row = pd.read_sql(
        """
        SELECT rechnungsnummer, erstellt_am, pdf_data FROM rechnungen r
        WHERE r.projekt_name = %s
          AND (
              r.benutzername = %s
              OR (
                  (r.benutzername IS NULL OR r.benutzername = '')
                  AND EXISTS (
                      SELECT 1 FROM projekte p
                      WHERE (p.projekt_name = r.projekt_name OR p.name = r.projekt_name)
                        AND p.benutzername = %s
                  )
              )
          )
        ORDER BY r.erstellt_am DESC LIMIT 1
        """,
        engine, params=(projekt_name, current_user, current_user)
    )

    if row.empty:
        st.warning("Keine Rechnungen für dieses Projekt gefunden.")
        return

    erstellt  = row["erstellt_am"].iloc[0]
    pdf_bytes = row["pdf_data"].iloc[0]
    if isinstance(pdf_bytes, memoryview):
        pdf_bytes = bytes(pdf_bytes)
    nummer    = row["rechnungsnummer"].iloc[0]
    pdf_size  = len(pdf_bytes) if pdf_bytes else 0

    st.markdown(f"---\n**Rechnungsnummer:** {nummer} | **Erstellt am:** {erstellt}")
    st.markdown(f"PDF-Größe: **{pdf_size} Bytes**")

    if pdf_size > 100:
        st.download_button(
            f"📥 Rechnung {nummer} herunterladen",
            data=pdf_bytes,
            file_name=f"Rechnung_{projekt_name}_{nummer}.pdf",
            mime="application/pdf",
            key=f"download_{projekt_name}_{nummer}",
        )
    else:
        st.warning("Die PDF ist leer oder beschädigt. Bitte Rechnung neu erstellen.")
