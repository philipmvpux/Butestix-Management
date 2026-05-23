
import io
import os
import re
import streamlit as st
from io import BytesIO
from datetime import date, datetime
from math import ceil

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# ── Hilfsfunktion: sicherer String (None/bytes → str) ───────
def _s(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8")
        except Exception:
            return value.decode("latin-1", errors="replace")
    return str(value)


# ── Logo-Hilfsfunktion ───────────────────────────────────────
def _draw_logo_or_name(c, firmenname: str, height: float) -> bool:
    """
    Zeichnet das Firmenlogo oben links.
    Gibt True zurück wenn Logo gezeichnet wurde, sonst False.
    """
    logo_bytes = st.session_state.get("firmenlogo")
    if logo_bytes:
        try:
            from PIL import Image
            logo_img = Image.open(io.BytesIO(logo_bytes))
            max_w, max_h = 120, 60
            w, h = logo_img.size
            scale = min(max_w / w, max_h / h, 1.0)
            w_new, h_new = int(w * scale), int(h * scale)
            logo_img = logo_img.resize((w_new, h_new))
            logo_path = "_temp_logo.png"
            logo_img.save(logo_path)
            c.drawImage(logo_path, 50, height - 50 - h_new,
                        width=w_new, height=h_new, mask="auto")
            os.remove(logo_path)
            return True
        except Exception:
            pass
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, firmenname)
    return False


# ── Fußzeile (Bankdaten, Kontakt, Handelsregister) ──────────
def _draw_footer(c, y: float, firmenname: str,
                 gesellschaftsform: str, adresse: str):
    bankname        = _s(st.session_state.get("bankname"))
    iban            = _s(st.session_state.get("iban"))
    bic             = _s(st.session_state.get("bic"))
    geschaeftsfuehrer = _s(st.session_state.get("geschaeftsfuehrer"))
    telefon         = _s(st.session_state.get("firmentelefon"))
    registergericht = _s(st.session_state.get("registergericht"))
    hrb_nummer      = _s(st.session_state.get("hrb_nummer"))
    ustidnr         = _s(st.session_state.get("ustidnr"))

    c.setFont("Helvetica", 7)
    c.drawString(50, y, "Anschrift:")
    if gesellschaftsform.strip() == "Einzelunternehmen":
        c.drawString(50, y - 15, firmenname)
    else:
        c.drawString(50, y - 15, f"{firmenname} {gesellschaftsform.strip()}")
    c.drawString(50, y - 30, adresse)

    c.drawString(180, y,      bankname)
    c.drawString(180, y - 15, f"IBAN: {iban}")
    c.drawString(180, y - 30, f"BIC: {bic}")

    c.drawString(300, y,      "Geschäftsführer:")
    c.drawString(300, y - 15, geschaeftsfuehrer)
    c.drawString(300, y - 30, f"Tel.: {telefon}")

    c.drawString(400, y,      registergericht)
    c.drawString(400, y - 15, f"HRB: {hrb_nummer}")
    c.drawString(400, y - 30, f"UStIdNr.: {ustidnr}")


# ── Kopfzeile (Adressblock rechts) ──────────────────────────
def _draw_header_right(c, height: float,
                       firmenname: str, gesellschaftsform: str,
                       adresse: str, telefon: str, fax: str):
    right_x = 400
    y = height - 65
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_x + 150, y, "Anschrift")
    y -= 15
    c.setFont("Helvetica", 10)
    if gesellschaftsform.strip() == "Einzelunternehmen":
        c.drawRightString(right_x + 150, y, firmenname)
    else:
        c.drawRightString(right_x + 150, y,
                          f"{firmenname} {gesellschaftsform.strip()}")
    y -= 15
    c.drawRightString(right_x + 150, y, adresse)
    y -= 50
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(right_x + 150, y, "Kontakt")
    y -= 15
    c.setFont("Helvetica", 10)
    if telefon:
        c.drawRightString(right_x + 150, y, f"Tel: {telefon}")
        y -= 15
    if fax:
        c.drawRightString(right_x + 150, y, f"Fax: {fax}")


# ============================================================
#  1. PAUSCHALRECHNUNG
# ============================================================

def generate_pauschal_invoice_pdf(
    projekt_name, empfaenger_name, empfaenger_adresse,
    pauschalbetrag, rechnungsnummer,
    leistungszeitraum_start, leistungszeitraum_ende
) -> BytesIO:
    """Erzeugt eine einfache Pauschalrechnung als PDF."""

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Firmendaten
    firmenname       = _s(st.session_state.get("firmenname"))
    gesellschaftsform = _s(st.session_state.get("gesellschaftsform"))
    adresse          = _s(st.session_state.get("firmenadresse"))
    telefon          = _s(st.session_state.get("firmentelefon"))
    fax              = _s(st.session_state.get("firmenfax"))

    # Übergabewerte sichern
    empfaenger_name    = _s(empfaenger_name)
    empfaenger_adresse = _s(empfaenger_adresse)
    projekt_name       = _s(projekt_name)

    # Logo / Firmenname
    _draw_logo_or_name(c, firmenname, height)

    # Adressblock rechts
    _draw_header_right(c, height, firmenname, gesellschaftsform,
                       adresse, telefon, fax)

    # Empfänger
    c.drawString(50, height - 155, empfaenger_name)
    c.drawString(50, height - 170, empfaenger_adresse)

    # Projektinfos
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 270, "Projekt:")
    c.setFont("Helvetica", 10)
    c.drawString(125, height - 270, projekt_name)

    # Rechnungsinfos
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50,  height - 290, "Rechnungsdatum:")
    c.drawString(185, height - 290, "Rechnungsnummer:")
    c.drawString(350, height - 290, "Leistungszeitraum:")
    c.setFont("Helvetica", 10)
    c.drawString(50,  height - 310, date.today().strftime("%d.%m.%Y"))
    c.drawString(185, height - 310, str(rechnungsnummer))
    c.drawString(350, height - 310,
                 f"{leistungszeitraum_start.strftime('%d.%m.%Y')} bis "
                 f"{leistungszeitraum_ende.strftime('%d.%m.%Y')}")

    # Trennlinie
    c.setLineWidth(1)
    c.line(50, height - 320, width - 50, height - 320)

    # Betrag
    y = height - 370
    c.setFont("Helvetica", 10)
    c.drawString(50,  y, f"Pauschale für die vereinbarten Leistungen zum Projekt {projekt_name}")
    c.drawString(450, y, f"{pauschalbetrag:.2f} €")
    y -= 30

    mwst       = pauschalbetrag * 0.19
    nettobetrag = pauschalbetrag + mwst

    c.setFont("Helvetica", 10)
    c.drawString(330, y, "Bruttobetrag:")
    c.drawString(450, y, f"{pauschalbetrag:.2f} €")
    y -= 20
    c.drawString(330, y, "zzgl. 19% MwSt.")
    c.drawString(450, y, f"{mwst:.2f} €")
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.drawString(330, y, "Gesamtbetrag:")
    c.drawString(450, y, f"{nettobetrag:.2f} €")

    # Zahlungsaufforderung
    y = 150
    c.setFont("Helvetica", 10)
    c.drawString(50, y,
                 "Bitte überweisen Sie den Gesamtbetrag innerhalb von "
                 "14 Tagen auf das unten angegebene Konto.")
    y -= 20
    c.drawString(50, y, "Bei Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung.")
    y -= 20
    c.setLineWidth(1)
    c.line(50, y, width - 50, y)
    y -= 20

    # Fußzeile
    _draw_footer(c, y, firmenname, gesellschaftsform, adresse)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ============================================================
#  2. DETAILRECHNUNG (Material + Lohn + Geräte)
# ============================================================

def generate_invoice_pdf_v2(
    projekt_name, empfaenger_name, empfaenger_adresse,
    positionen, arbeitsleistungen, rechnungsnummer,
    leistungszeitraum_start, leistungszeitraum_ende,
    geraetepositionen=None
) -> BytesIO:
    """Mehrseitige Rechnung mit Material-, Lohn- und Gerätepositionen."""

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    firmenname        = _s(st.session_state.get("firmenname", ""))
    gesellschaftsform = _s(st.session_state.get("gesellschaftsform", ""))
    adresse           = _s(st.session_state.get("firmenadresse", ""))
    telefon           = _s(st.session_state.get("firmentelefon", ""))
    fax               = _s(st.session_state.get("firmenfax", ""))

    # Positionen zusammenstellen
    material_positionen = [(n, m, e, p) for n, m, e, p in positionen if m > 0]
    lohn_positionen     = [
        (l["rolle"], l["stunden"], "Stunden", l["stundensatz"])
        for l in arbeitsleistungen if l["stunden"] > 0
    ]
    geraet_positionen = []
    if geraetepositionen:
        geraet_positionen = [
            (p["geraet"], p["stunden"], "Stunden", p["betriebskosten"])
            for p in geraetepositionen if p["stunden"] > 0
        ]

    # Alle Positionen mit Block-Headern zusammenführen
    alle_positionen = []
    for header, positions, typ in [
        ("Materialaufwand",  material_positionen, "Material"),
        ("Lohnaufwand",      lohn_positionen,     "Lohn"),
        ("Gerätekosten",     geraet_positionen,   "Geraet"),
    ]:
        alle_positionen.append((None, None, None, None, f"{typ}-Header"))
        for p in positions:
            alle_positionen.append((*p, typ))

    # Seitenweise ausgeben
    max_pro_seite = 20
    total         = 0.0
    geraete_total = 0.0
    laufnummer    = 1
    pos_index     = 0
    page_num      = 0

    while pos_index < len(alle_positionen):

        # ── Seitenkopf ──────────────────────────────────────
        _draw_logo_or_name(c, firmenname, height)

        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(width - 50, height - 50,
                          str(page_num + 1).zfill(2))

        _draw_header_right(c, height, firmenname, gesellschaftsform,
                           adresse, telefon, fax)

        c.drawString(50, height - 155, empfaenger_name)
        c.drawString(50, height - 170, empfaenger_adresse)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50,  height - 270, "Projekt:")
        c.setFont("Helvetica", 10)
        c.drawString(125, height - 270, projekt_name)

        c.setFont("Helvetica-Bold", 10)
        c.drawString(50,  height - 290, "Rechnungsdatum:")
        c.drawString(185, height - 290, "Rechnungsnummer:")
        c.drawString(350, height - 290, "Leistungszeitraum:")
        c.setFont("Helvetica", 10)
        c.drawString(50,  height - 310, date.today().strftime("%d.%m.%Y"))
        c.drawString(185, height - 310, str(rechnungsnummer))
        c.drawString(350, height - 310,
                     f"{leistungszeitraum_start.strftime('%d.%m.%Y')} bis "
                     f"{leistungszeitraum_ende.strftime('%d.%m.%Y')}")

        c.setLineWidth(1)
        c.line(50, height - 320, width - 50, height - 320)

        # Tabellenkopf
        y = height - 340
        if page_num > 0:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Fortsetzung der Positionen")
            y -= 25

        c.setFont("Helvetica-Bold", 11)
        c.drawString(50,  y, "Pos.")
        c.drawString(100, y, "Bezeichnung")
        c.drawString(250, y, "Menge")
        c.drawString(300, y, "/Einheit")
        c.drawString(370, y, "E-Preis €")
        c.drawString(450, y, "Gesamt €")
        y -= 30
        c.setLineWidth(1)
        c.line(50, height - 350, width - 50, height - 350)
        c.setFont("Helvetica", 10)

        # ── Positionen dieser Seite ──────────────────────────
        count = 0
        while count < max_pro_seite and pos_index < len(alle_positionen):
            name, menge, einheit, preis, typ = alle_positionen[pos_index]

            if typ.endswith("-Header"):
                # Header nur ausgeben wenn danach noch Platz für eine Position
                nachfolger_ok = (
                    pos_index + 1 < len(alle_positionen)
                    and not alle_positionen[pos_index + 1][4].endswith("-Header")
                    and count < max_pro_seite - 1
                )
                if not nachfolger_ok:
                    break

                label_map = {
                    "Material-Header": "Materialaufwand",
                    "Lohn-Header":     "Lohnaufwand",
                    "Geraet-Header":   "Gerätekosten",
                }
                c.setFont("Helvetica-Bold", 11)
                c.drawString(100, y, label_map.get(typ, ""))
                y -= 20
                c.setFont("Helvetica", 10)
                pos_index += 1
                count += 1
            else:
                gesamt = menge * preis
                if typ == "Material":
                    total += gesamt
                elif typ == "Geraet":
                    geraete_total += gesamt

                c.drawString(50,  y, f"{laufnummer:05d}")
                c.drawString(100, y, str(name))
                c.drawString(250, y, f"{menge:.2f}")
                c.drawString(300, y, str(einheit))
                c.drawString(370, y, f"{preis:.2f}")
                c.drawString(450, y, f"{gesamt:.2f}")
                laufnummer += 1
                y -= 20
                pos_index += 1
                count += 1

        page_num += 1

        # ── Letzte Seite: Summen + Fußzeile ─────────────────
        if pos_index >= len(alle_positionen):
            arbeits_total = sum(
                l["stunden"] * l["stundensatz"]
                for l in arbeitsleistungen if l["stunden"] > 0
            )
            brutto      = total + arbeits_total + geraete_total
            mwst        = brutto * 0.19
            nettobetrag = brutto + mwst

            y -= 25
            c.setFont("Helvetica", 10)
            c.drawString(330, y, "Bruttobetrag:")
            c.drawString(450, y, f"{brutto:.2f} €")
            y -= 10
            c.drawString(330, y, "zzgl. 19% MwSt.")
            c.drawString(450, y, f"{mwst:.2f} €")
            y -= 20
            c.setFont("Helvetica-Bold", 12)
            c.drawString(330, y, "Gesamtbetrag:")
            c.drawString(450, y, f"{nettobetrag:.2f} €")

            # Neue Seite für Fußzeile falls nicht genug Platz
            if y <= 150:
                c.showPage()
                page_num += 1

            y = 150
            c.setFont("Helvetica", 10)
            c.drawString(50, y,
                         "Bitte überweisen Sie den Gesamtbetrag innerhalb von "
                         "14 Tagen auf das unten angegebene Konto.")
            y -= 20
            c.drawString(50, y,
                         "Bei Rückfragen stehen wir Ihnen jederzeit gerne zur Verfügung.")
            y -= 20
            c.setLineWidth(1)
            c.line(50, y, width - 50, y)
            y -= 20

            _draw_footer(c, y, firmenname, gesellschaftsform, adresse)

        c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


# ============================================================
#  3. TAGESBERICHT-PDF (aus Archiv-Daten)
# ============================================================

def generate_report_pdf_from_data(projekt_name, datum, report_data) -> BytesIO:
    """
    Erzeugt einen Tagesbericht als PDF aus gespeicherten Archiv-Daten.

    Args:
        projekt_name: Name des Projekts
        datum:        Datum als str oder date-Objekt
        report_data:  Dict mit Schlüsseln wetter, boden, arbeitsbericht,
                      mitarbeiter, materialeinsatz, geraeteeinsatz,
                      probleme, todo, checklisten_data
    Returns:
        BytesIO mit dem fertigen PDF
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Tagesbericht")

    c.setFont("Helvetica", 10)
    y = height - 80
    c.drawString(50, y, f"Projekt: {projekt_name}")
    y -= 20

    datum_str = datum if isinstance(datum, str) else datum.strftime("%d.%m.%Y")
    c.drawString(50, y, f"Datum: {datum_str}")
    y -= 30

    # Felder
    fields = [
        ("Wetter",         report_data.get("wetter", "")),
        ("Bodenzustand",   report_data.get("boden", "")),
        ("Arbeitsbericht", report_data.get("arbeitsbericht", "")),
        ("Mitarbeiter",    report_data.get("mitarbeiter", "")),
        ("Materialeinsatz",report_data.get("materialeinsatz", "")),
        ("Geräteeinsatz",  report_data.get("geraeteeinsatz", "")),
        ("Probleme",       report_data.get("probleme", "")),
        ("To-Do",          report_data.get("todo", "")),
    ]

    for label, value in fields:
        if not value:
            continue
        c.setFont("Helvetica-Bold", 11)
        c.drawString(50, y, f"{label}:")
        y -= 15
        c.setFont("Helvetica", 9)
        for line in (value or "").split("\n"):
            for i in range(0, max(len(line), 1), 90):
                c.drawString(60, y, line[i:i + 90])
                y -= 12
        y -= 5

        # Neue Seite falls nötig
        if y < 60:
            c.showPage()
            y = height - 50

    # Footer
    c.setFont("Helvetica", 8)
    c.drawString(50, 30,
                 f"Generiert: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    c.drawString(width - 150, 30, "[Regeneriert aus Archiv-Daten]")

    c.save()
    buffer.seek(0)
    return buffer


# ============================================================
#  4. MARKDOWN → PDF
# ============================================================

def markdown_to_pdf(markdown_text: str, pdf_filename: str) -> str:
    """
    Konvertiert einen Markdown-Text in eine PDF-Datei.

    Args:
        markdown_text: Markdown-formatierter Text
        pdf_filename:  Pfad zur Ausgabedatei
    Returns:
        pdf_filename
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=11)

    for line in markdown_text.split("\n"):
        if line.startswith("# "):
            pdf.set_font("Arial", "B", size=16)
            pdf.cell(0, 10, line[2:], ln=True)
            pdf.set_font("Arial", size=11)
        elif line.startswith("## "):
            pdf.set_font("Arial", "B", size=14)
            pdf.cell(0, 10, line[3:], ln=True)
            pdf.set_font("Arial", size=11)
        elif line.startswith("### "):
            pdf.set_font("Arial", "B", size=12)
            pdf.cell(0, 10, line[4:], ln=True)
            pdf.set_font("Arial", size=11)
        elif line.strip().startswith(("- ", "* ")):
            pdf.cell(0, 8, "• " + line.strip()[2:], ln=True)
        elif line.strip() == "---":
            pdf.cell(0, 5, "", ln=True)
        elif line.strip() == "":
            pdf.cell(0, 3, "", ln=True)
        else:
            cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
            cleaned = re.sub(r"\*(.*?)\*",     r"\1", cleaned)
            cleaned = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", cleaned)
            pdf.multi_cell(0, 5, cleaned)

    pdf.output(pdf_filename)
    return pdf_filename
# ============================================================
#  5. FORTSCHRITTSBERICHT-PDF
# ============================================================
 
def generate_fortschritt_pdf(projekt_id: int, projekt_name: str) -> BytesIO | None:
    """
    Erstellt den täglichen Fortschrittsbericht als PDF.
    Wird in pages/fortschritt.py aufgerufen.
 
    Returns:
        BytesIO mit dem fertigen PDF, oder None wenn keine Daten vorhanden.
    """
    import textwrap
    import pandas as pd
    from datetime import date, datetime
    from database import engine
    from ui.archiv import save_bericht_daten_to_archive, save_pdf_to_archive
 
    heute      = date.today().strftime("%Y-%m-%d")
    buffer     = BytesIO()
    c          = canvas.Canvas(buffer, pagesize=A4)
    firmenname = st.session_state.get("firmenname", "")
 
    y = 800
 
    # ── Kopfzeile ────────────────────────────────────────────
    c.setFont("Helvetica", 20)
    c.line(40, y, 550, y)
    c.setDash()
    y -= 20
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Datum: {date.today().strftime('%d.%m.%Y')}")
    y -= 30
 
    # ── Wetterdaten ──────────────────────────────────────────
    wetter_row = pd.read_sql(
        "SELECT * FROM wetterdaten WHERE projekt_id = %s AND datum = %s",
        engine, params=(projekt_id, heute)
    )
    c.setLineWidth(1)
    c.setDash()
    c.line(40, y, 550, y)
    y -= 20
 
    if not wetter_row.empty:
        wetter1    = wetter_row["wetter1"].iloc[0]
        wetter2    = wetter_row["wetter2"].iloc[0]
        boden1     = wetter_row["boden1"].iloc[0]
        boden2     = wetter_row["boden2"].iloc[0]
        temperatur = wetter_row["temperatur"].iloc[0]
        schlecht   = wetter_row["schlecht"].iloc[0]
 
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Wetter:")
        c.setFont("Helvetica", 10)
        c.drawString(170, y, str(wetter1))
        c.drawString(300, y, str(wetter2))
        c.setFont("Helvetica-Bold", 10)
        c.drawString(390, y, "Temperatur:")
        c.setFont("Helvetica", 10)
        c.drawString(490, y, f"{temperatur} °C")
        y -= 20
        c.setLineWidth(1); c.setDash(); c.line(40, y, 550, y); y -= 20
 
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Bodenverhältnisse:")
        c.setFont("Helvetica", 10)
        c.drawString(170, y, str(boden1))
        c.drawString(300, y, str(boden2))
        y -= 20
        c.setLineWidth(1); c.setDash(); c.line(40, y, 550, y); y -= 20
 
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Schlechtes Wetter:")
        c.setFont("Helvetica", 10)
        c.drawString(170, y, "Ja" if schlecht else "Nein")
        y -= 20
 
    c.setLineWidth(1); c.setDash(); c.line(40, y, 550, y); y -= 20
 
    # ── Arbeitskräfte ─────────────────────────────────────────
    ak_df = pd.read_sql(
        "SELECT COUNT(DISTINCT benutzername) AS anzahl FROM arbeitszeiten WHERE projekt_id = %s AND datum = %s",
        engine, params=(projekt_id, heute)
    )
    anzahl_ak = ak_df["anzahl"].iloc[0] if not ak_df.empty else 0
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Anzahl AK:")
    c.setFont("Helvetica", 10)
    c.drawString(170, y, str(anzahl_ak))
    y -= 20
    c.setLineWidth(1); c.setDash(); c.line(40, y, 550, y); y -= 20
 
    # ── Erledigte Checklistenpunkte ───────────────────────────
    df_check = pd.read_sql(
        "SELECT * FROM checklistenpunkte WHERE projekt_id = %s AND erledigt = 1 AND erledigt_am = %s ORDER BY id",
        engine, params=(projekt_id, heute)
    )
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Ausgeführte Arbeiten:")
    c.setFont("Helvetica", 10)
    y -= 20
    for _, row in df_check.iterrows():
        erledigt = "-" if row["erledigt"] else "X"
        c.drawString(60, y, f"{erledigt} {row['text']}")
        y -= 15
        if row.get("kommentar") and row["kommentar"].strip():
            c.drawString(80, y, f"Kommentar Fortschritt: {row['kommentar']}")
            y -= 15
        if y < 100:
            c.showPage(); y = 800
 
    # Mitarbeiter-Kommentar
    fk_row = pd.read_sql(
        "SELECT kommentar FROM checklisten_fortschrittkommentar WHERE projekt_id = %s AND datum = %s",
        engine, params=(projekt_id, heute)
    )
    if not fk_row.empty and fk_row["kommentar"].iloc[0].strip():
        c.drawString(60, y, f"- {fk_row['kommentar'].iloc[0]}")
        y -= 15
    y -= 20
 
    # ── Probleme & Zeitaufwand ────────────────────────────────
    problem_row = pd.read_sql(
        "SELECT kommentar, zeitaufwand FROM checklisten_gesamtkommentar WHERE projekt_id = %s AND datum = %s",
        engine, params=(projekt_id, heute)
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
            c.drawString(60, y, "Benötigte Zeit:")
            tw = c.stringWidth("Benötigte Zeit:", "Helvetica-Bold", 10)
            c.setFont("Helvetica", 10)
            c.drawString(60 + tw + 10, y, f"{row['zeitaufwand']} min.")
            y -= 20
 
    # Kommentare aus erledigten Checklistenpunkten
    kommentare = [r["kommentar"] for _, r in df_check.iterrows() if r.get("kommentar") and r["kommentar"].strip()]
    if kommentare:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(60, y, "Kommentar Fortschritt:")
        y -= 18
        c.setFont("Helvetica", 10)
        for punkt in kommentare:
            for line in textwrap.wrap(punkt, width=50):
                c.drawString(80, y, f"- {line}")
                y -= 15
                if y < 100:
                    c.showPage(); y = 800
        y -= 10
 
    # ── Tabellen: Mitarbeiter | Geräte ───────────────────────
    mitarbeiter_df = pd.read_sql(
        """SELECT m.benutzername, m.vorname, m.nachname, m.rolle,
                  COALESCE(SUM(a.stunden), 0) as stunden
           FROM mitarbeiter m
           INNER JOIN mitarbeiter_projekte mp ON m.benutzername = mp.mitarbeiter_benutzername
           LEFT JOIN arbeitszeiten a
               ON m.benutzername = a.benutzername AND a.projekt_id = mp.projekt_id AND a.datum = %s
           WHERE mp.projekt_id = %s
           GROUP BY m.benutzername, m.vorname, m.nachname, m.rolle""",
        engine, params=(heute, projekt_id)
    )
    geraete_df = pd.read_sql(
        "SELECT geraet, nutzungszeit FROM geraete_nutzung WHERE projekt_id = %s AND datum::date = %s::date",
        engine, params=(projekt_id, heute)
    )
    try:
        material_df = pd.read_sql(
            "SELECT material, menge, einheit FROM materialien WHERE projekt_id = %s AND datum = %s",
            engine, params=(projekt_id, heute)
        )
    except Exception:
        material_df = pd.DataFrame(columns=["material", "menge", "einheit"])
 
    y_tab = y
    x_l   = 40
    x_r   = 320
 
    # Mitarbeitertabelle
    c.setLineWidth(1); c.setDash(); c.line(x_l, y_tab, x_l + 255, y_tab)
    y_m = y_tab - 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_l + 10, y_m, "Mitarbeiter")
    c.drawString(x_l + 205, y_m, "Stunden")
    y_m -= 10
    c.setLineWidth(1); c.setDash(); c.line(x_l, y_m, x_l + 255, y_m)
    y_m -= 20
    c.setFont("Helvetica", 10)
    for _, row in mitarbeiter_df.iterrows():
        voller_name = f"{row['vorname']} {row['nachname']}"
        c.drawString(x_l + 10, y_m, f"{voller_name} ({row['rolle'] or '-'})")
        c.drawString(x_l + 225, y_m, f"{row['stunden']:.2f}")
        y_m -= 15
    y_m -= 5
 
    # Gerätetabelle
    c.setLineWidth(1); c.setDash(); c.line(x_r, y_tab, x_r + 255, y_tab)
    y_g = y_tab - 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_r + 10, y_g, "Geräte")
    c.drawString(x_r + 205, y_g, "Stunden")
    y_g -= 10
    c.setLineWidth(1); c.setDash(); c.line(x_r, y_g, x_r + 255, y_g)
    y_g -= 20
    c.setFont("Helvetica", 10)
    for _, row in geraete_df.iterrows():
        try:
            nutzungszeit = float(row["nutzungszeit"]) if pd.notnull(row["nutzungszeit"]) else 0.0
            c.drawString(x_r + 10, y_g, str(row["geraet"]))
            c.drawString(x_r + 225, y_g, f"{nutzungszeit:.2f}")
            y_g -= 15
        except Exception:
            pass
    y_g -= 5
 
    # ── Materialtabelle ───────────────────────────────────────
    y = min(y_m, y_g)
    c.setLineWidth(1); c.setDash(); c.line(x_l, y, x_l + 255, y)
    y_mat = y - 18
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_l + 10, y_mat, "Material")
    c.drawString(x_l + 210, y_mat, "Menge")
    y_mat -= 10
    c.setLineWidth(1); c.setDash(); c.line(x_l, y_mat, x_l + 255, y_mat)
    y_mat -= 20
    c.setFont("Helvetica", 10)
    for _, row in material_df.iterrows():
        try:
            menge   = float(row["menge"]) if pd.notnull(row["menge"]) else 0.0
            einheit = str(row["einheit"]) if pd.notnull(row.get("einheit")) else ""
            c.drawString(x_l + 10, y_mat, str(row["material"]))
            c.drawString(x_l + 180, y_mat, f"{menge:.2f} {einheit}")
            y_mat -= 15
        except Exception:
            pass
 
    c.save()
    buffer.seek(0)
 
    # ── Archiv speichern ──────────────────────────────────────
    wetter_text = ""
    boden_text  = ""
    if not wetter_row.empty:
        wetter_text = f"{wetter_row['wetter1'].iloc[0]}, {wetter_row['wetter2'].iloc[0]} | Temp: {wetter_row['temperatur'].iloc[0]}°C"
        boden_text  = f"{wetter_row['boden1'].iloc[0]}, {wetter_row['boden2'].iloc[0]}"
 
    mitarbeiter_text = ", ".join(mitarbeiter_df["benutzername"].tolist())
    material_text    = ", ".join([
        f"{r['material']}: {r['menge']} {r['einheit']}"
        for _, r in material_df.iterrows() if r["material"] != "-"
    ])
    geraete_text = ", ".join([
        f"{r['geraet']}: {r['nutzungszeit']}h"
        for _, r in geraete_df.iterrows() if r["geraet"] != "-"
    ])
    probleme_text = problem_row["kommentar"].iloc[0] if not problem_row.empty else ""
 
    save_bericht_daten_to_archive(
        benutzername=st.session_state.user,
        projekt_id=projekt_id,
        wetter=wetter_text, boden=boden_text,
        arbeitsbericht="", mitarbeiter=mitarbeiter_text,
        materialeinsatz=material_text, geraeteeinsatz=geraete_text,
        probleme=probleme_text, todo="", checklisten_data="",
        erstellt_von_admin=0
    )
    save_pdf_to_archive(st.session_state.user, projekt_id, buffer.getvalue())
    buffer.seek(0)
    return buffer