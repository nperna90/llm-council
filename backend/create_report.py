import os
from fpdf import FPDF
from datetime import datetime
from pathlib import Path

# Assicuriamoci che la cartella reports esista
# La cartella reports è nella root del progetto
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


class InvestmentMemoPDF(FPDF):
    def header(self):
        # Intestazione Professionale
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'LLM COUNCIL | INVESTMENT MEMORANDUM', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 5, 'Artificial Intelligence Strategic Advisory', 0, 1, 'C')
        self.ln(5)
        # Linea divisoria
        self.set_draw_color(50, 50, 50)
        self.set_line_width(0.5)
        self.line(10, 30, 200, 30)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} - Strictly Confidential', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(0)
        self.cell(0, 8, f'  {label}', 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, text):
        self.set_font('Times', '', 11)
        self.set_text_color(20)
        # Sostituzioni caratteri Markdown semplici
        clean_text = text.replace('**', '').replace('__', '').replace('`', '').replace('*', '')
        
        # Il testo dovrebbe già essere pulito da clean_text_for_pdf, ma facciamo un controllo finale
        # Rimuovi caratteri di controllo che potrebbero causare problemi
        clean_text = ''.join(c for c in clean_text if c.isprintable() or c in ('\n', '\r', '\t'))
        
        # Verifica finale che sia in latin-1
        try:
            clean_text.encode('latin-1')
        except UnicodeEncodeError:
            # Se ancora ci sono problemi, rimuovi caratteri problematici
            clean_text = ''.join(c if ord(c) < 256 else '?' for c in clean_text)
        
        # Se il testo è vuoto dopo la pulizia, usa un placeholder
        if not clean_text.strip():
            clean_text = "[Contenuto non disponibile - caratteri non supportati]"
        
        try:
            self.multi_cell(0, 6, clean_text)
            self.ln()
        except Exception as e:
            # Se anche questo fallisce, prova con testo minimo
            print(f"   ⚠️ Errore durante scrittura testo: {e}")
            try:
                self.multi_cell(0, 6, "[Errore nella formattazione del contenuto]")
                self.ln()
            except:
                pass  # Se anche questo fallisce, continua


def clean_text_for_pdf(text):
    """
    Pulisce il testo per renderlo compatibile con FPDF (latin-1 encoding).
    Sostituisce caratteri Unicode non supportati con equivalenti ASCII.
    """
    if not text:
        return ""
    
    # Mappa di sostituzione per caratteri comuni italiani/europei
    replacements = {
        'à': 'a', 'è': 'e', 'é': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'À': 'A', 'È': 'E', 'É': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U',
        '€': 'EUR', '£': 'GBP', '¥': 'JPY', '°': 'deg',
        '–': '-', '—': '-', '"': '"', ''': "'", ''': "'", '"': '"',
        '…': '...', '•': '*', '→': '->', '←': '<-', '↑': '^', '↓': 'v',
    }
    
    # Applica sostituzioni
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Rimuovi tutti i caratteri non-ASCII rimanenti
    try:
        # Prova a codificare in latin-1
        text = text.encode('latin-1', 'replace').decode('latin-1')
    except:
        # Fallback: rimuovi caratteri non supportati
        text = ''.join(c if ord(c) < 256 and c.isprintable() else '?' for c in text)
    
    return text


def generate_pdf(conversation_id, title, content):
    """
    Genera un PDF formattato basato sul contenuto della chat.
    Salva il file nella cartella 'reports'.
    """
    # Pulisci il contenuto PRIMA di creare il PDF - CRITICO per FPDF
    print(f"   Pulizia contenuto per compatibilità FPDF (latin-1)...")
    original_length = len(content)
    content = clean_text_for_pdf(content)
    title = clean_text_for_pdf(title)
    print(f"   Contenuto pulito: {len(content)} caratteri (originale: {original_length})")
    
    pdf = InvestmentMemoPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Metadata del documento
    pdf.set_font('Arial', 'B', 12)
    
    # Pulisci il titolo per evitare problemi con caratteri speciali
    safe_title_display = title[:100] if title else "Investment Analysis"
    
    try:
        pdf.cell(0, 6, f"REF ID: {conversation_id[:8]}", 0, 1)
        pdf.cell(0, 6, f"SUBJECT: {safe_title_display}", 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"DATE: {datetime.now().strftime('%d %B %Y, %H:%M')}", 0, 1)
        pdf.ln(10)
    except Exception as e:
        print(f"   ⚠️ Errore durante scrittura metadata: {e}")
        # Continua comunque

    # Parsing del contenuto (simula la lettura dei capitoli Markdown)
    lines = content.split('\n')
    buffer = ""
    
    for line in lines:
        line = line.strip()
        # Se trova un titolo (## o #)
        if line.startswith('##') or (line.startswith('#') and len(line) < 50):
            if buffer:
                pdf.chapter_body(buffer)
                buffer = ""
            clean_title = line.replace('#', '').strip()
            # Pulisci anche il titolo
            clean_title = clean_text_for_pdf(clean_title)
            pdf.chapter_title(clean_title)
        else:
            buffer += line + "\n"
    
    # Scrivi il resto del buffer
    if buffer:
        pdf.chapter_body(buffer)

    # Nome file sicuro
    safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
    safe_title = safe_title.replace(" ", "_")
    
    # Se il titolo è vuoto o troppo corto, usa un default
    if not safe_title or len(safe_title) < 3:
        safe_title = "Investment_Analysis"
    
    # Crea il nome del file
    filename = REPORTS_DIR / f"Report_{safe_title}_{conversation_id[:8]}.pdf"
    
    # Assicurati che la directory esista
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        print(f"   Salvataggio PDF in: {filename}")
        print(f"   Directory reports: {REPORTS_DIR} (esiste: {REPORTS_DIR.exists()})")
        
        # Converti il path in stringa assoluta per evitare problemi
        abs_filename = str(filename.absolute())
        print(f"   Path assoluto: {abs_filename}")
        
        # Salva il PDF
        pdf.output(abs_filename)
        
        # Verifica che il file sia stato creato
        if not Path(abs_filename).exists():
            print(f"   ❌ File non creato dopo output()")
            print(f"   Verifica permessi di scrittura su: {REPORTS_DIR}")
            return None
        
        file_size = Path(abs_filename).stat().st_size
        if file_size == 0:
            print(f"   ❌ File creato ma vuoto (0 bytes)")
            return None
            
        print(f"   ✅ PDF salvato: {file_size} bytes")
        return abs_filename
    except PermissionError as e:
        print(f"   ❌ Errore permessi durante salvataggio PDF: {e}")
        print(f"   Verifica di avere i permessi di scrittura su: {REPORTS_DIR}")
        import traceback
        traceback.print_exc()
        return None
    except Exception as e:
        print(f"   ❌ Errore durante salvataggio PDF: {e}")
        print(f"   Tipo errore: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None


# Test locale
if __name__ == "__main__":
    generate_pdf("TEST_123", "Analisi NVDA", "## Intro\nTesto di prova.\n## Conclusione\nFine.")
    print("Test PDF completato. Controlla la cartella 'reports'.")
