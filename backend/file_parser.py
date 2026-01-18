import pandas as pd
from pypdf import PdfReader
from io import BytesIO
import csv

def parse_document(file_content: bytes, filename: str) -> str:
    """
    Identifica il tipo di file ed estrae il testo contenuto.
    Supporta: PDF, CSV, TXT.
    """
    ext = filename.split('.')[-1].lower()
    
    try:
        if ext == 'pdf':
            return _parse_pdf(file_content)
        elif ext in ['csv', 'xls', 'xlsx']:
            return _parse_spreadsheet(file_content, filename)
        elif ext in ['txt', 'md', 'json']:
            return file_content.decode('utf-8')
        else:
            return f"Error: Formato .{ext} non supportato. Usa PDF o CSV."
    except Exception as e:
        return f"Error parsing file: {str(e)}"

def _parse_pdf(content: bytes) -> str:
    """Estrae testo da un PDF pagina per pagina."""
    text = "--- INIZIO CONTENUTO DOCUMENTO PDF ---\n"
    
    # Usiamo BytesIO per trattare i bytes come un file
    with BytesIO(content) as f:
        reader = PdfReader(f)
        total_pages = len(reader.pages)
        text += f"(Documento di {total_pages} pagine)\n\n"
        
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                text += f"--- Pagina {i+1} ---\n{page_text}\n"
                
    text += "\n--- FINE CONTENUTO DOCUMENTO ---"
    return text

def _parse_spreadsheet(content: bytes, filename: str) -> str:
    """Legge CSV o Excel e lo converte in formato Markdown leggibile."""
    with BytesIO(content) as f:
        if filename.endswith('.csv'):
            try:
                # Proviamo a leggere con pandas
                df = pd.read_csv(f)
            except:
                # Fallback se pandas fallisce (es. separatori strani)
                return content.decode('utf-8')
        else:
            # Excel
            df = pd.read_excel(f)
    
    # Convertiamo il dataframe in una stringa Markdown (perfetta per LLM)
    text = "--- INIZIO DATI PORTAFOGLIO (Tabella) ---\n"
    text += df.to_markdown(index=False)
    text += "\n--- FINE DATI ---"
    return text
