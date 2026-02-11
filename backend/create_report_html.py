"""
Genera PDF con formattazione HTML/CSS per mantenere lo stile visivo dell'interfaccia.
Usa xhtml2pdf per convertire HTML in PDF.
"""

import os
from datetime import datetime
from pathlib import Path
from xhtml2pdf import pisa
from markdown import markdown

# Assicuriamoci che la cartella reports esista
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def clean_text_for_pdf(text):
    """
    Pulisce il testo per renderlo compatibile con HTML/PDF.
    Mantiene i caratteri Unicode ma li gestisce correttamente.
    """
    if not text:
        return ""
    
    # Rimuovi solo caratteri di controllo problematici
    text = ''.join(c for c in text if c.isprintable() or c in ('\n', '\r', '\t'))
    
    return text


def identify_agent_type(text):
    """Identifica il tipo di agente dal testo."""
    upper_text = text.upper()
    
    if 'BOGLEHEAD' in upper_text or 'BOGLE' in upper_text:
        return 'BOGLEHEAD'
    elif 'QUANT' in upper_text or 'QUANTITATIVE' in upper_text:
        return 'QUANT'
    elif 'MACRO' in upper_text or 'STRATEGIST' in upper_text or 'GLOBAL' in upper_text:
        return 'MACRO'
    elif 'CHAIRMAN' in upper_text or 'DELIBERA' in upper_text or 'SINTESI FINALE' in upper_text or 'FINAL SYNTHESIS' in upper_text:
        return 'CHAIRMAN'
    else:
        return 'DEFAULT'


def generate_html_content(conversation_id, title, content):
    """Genera HTML formattato con stili CSS per gli agenti."""
    
    # Colori agenti (stessi dell'interfaccia)
    agent_styles = {
        'BOGLEHEAD': {
            'color': '#10b981',
            'border_color': '#10b981',
            'bg_color': '#f0fdf4',
            'icon': '🛡️',
            'name': 'Boglehead'
        },
        'QUANT': {
            'color': '#3b82f6',
            'border_color': '#3b82f6',
            'bg_color': '#eff6ff',
            'icon': '📊',
            'name': 'Quant'
        },
        'MACRO': {
            'color': '#8b5cf6',
            'border_color': '#8b5cf6',
            'bg_color': '#faf5ff',
            'icon': '🌍',
            'name': 'Macro Strategist'
        },
        'CHAIRMAN': {
            'color': '#d4af37',
            'border_color': '#d4af37',
            'bg_color': '#fffbeb',
            'icon': '⚖️',
            'name': 'Chairman'
        }
    }
    
    # Pulisci il contenuto
    content = clean_text_for_pdf(content)
    title = clean_text_for_pdf(title)
    
    # Dividi in sezioni (usa regex per split)
    import re
    sections = re.split(r'(?=## )', content)
    
    # Genera HTML
    html_parts = []
    
    # Header
    html_parts.append(f"""
    <div style="text-align: center; margin-bottom: 30px; border-bottom: 2px solid #e5e7eb; padding-bottom: 20px;">
        <h1 style="color: #111827; font-size: 24px; margin: 0 0 10px 0;">LLM COUNCIL</h1>
        <p style="color: #6b7280; font-size: 14px; margin: 0;">Investment Memorandum</p>
    </div>
    """)
    
    # Metadata
    html_parts.append(f"""
    <div style="margin-bottom: 30px; padding: 15px; background: #f9fafb; border-radius: 8px;">
        <p style="margin: 5px 0; color: #374151;"><strong>REF ID:</strong> {conversation_id[:8]}</p>
        <p style="margin: 5px 0; color: #374151;"><strong>SUBJECT:</strong> {title}</p>
        <p style="margin: 5px 0; color: #374151;"><strong>DATE:</strong> {datetime.now().strftime('%d %B %Y, %H:%M')}</p>
    </div>
    """)
    
    # Contenuto
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        agent_type = identify_agent_type(section)
        
        if agent_type != 'DEFAULT' and agent_type in agent_styles:
            style = agent_styles[agent_type]
            
            # Estrai titolo e corpo
            lines = section.split('\n')
            title_line = lines[0].replace('#', '').strip() if lines else ''
            body_text = '\n'.join(lines[1:]).strip()
            
            # Converti Markdown in HTML
            body_html = markdown(body_text, extensions=['fenced_code', 'tables'])
            
            # Card agente
            html_parts.append(f"""
            <div style="
                margin-bottom: 20px;
                border-left: 4px solid {style['border_color']};
                background: {style['bg_color']};
                padding: 20px;
                border-radius: 0 8px 8px 0;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    margin-bottom: 15px;
                    color: {style['color']};
                    font-weight: 600;
                    font-size: 16px;
                ">
                    <span style="font-size: 20px; margin-right: 8px;">{style['icon']}</span>
                    <span>{title_line or style['name']}</span>
                </div>
                <div style="
                    padding-left: 28px;
                    color: {'#000000' if agent_type == 'CHAIRMAN' else '#111827'};
                    font-size: 14px;
                    line-height: 1.75;
                ">
                    {body_html}
                </div>
            </div>
            """)
        else:
            # Testo normale
            html_text = markdown(section, extensions=['fenced_code', 'tables'])
            html_parts.append(f"""
            <div style="
                margin-bottom: 20px;
                color: #374151;
                line-height: 1.75;
                font-size: 14px;
            ">
                {html_text}
            </div>
            """)
    
    # HTML completo
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #111827;
                line-height: 1.6;
            }}
            h1, h2, h3, h4, h5, h6 {{
                color: #111827;
                margin-top: 20px;
                margin-bottom: 10px;
            }}
            h1 {{ font-size: 24px; }}
            h2 {{ font-size: 20px; }}
            h3 {{ font-size: 18px; }}
            p {{
                margin: 10px 0;
            }}
            ul, ol {{
                margin: 10px 0;
                padding-left: 30px;
            }}
            li {{
                margin: 5px 0;
            }}
            code {{
                background: #f3f4f6;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }}
            pre {{
                background: #f3f4f6;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                margin: 15px 0;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 15px 0;
            }}
            th, td {{
                border: 1px solid #e5e7eb;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background: #f9fafb;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        {''.join(html_parts)}
    </body>
    </html>
    """
    
    return html_content


def generate_pdf(conversation_id, title, content):
    """
    Genera un PDF formattato con HTML/CSS per mantenere lo stile visivo.
    """
    print(f"   Generazione PDF HTML per conversazione {conversation_id[:8]}...")
    print(f"   Titolo: {title}")
    print(f"   Lunghezza contenuto: {len(content)} caratteri")
    
    try:
        # Genera HTML
        html_content = generate_html_content(conversation_id, title, content)
        
        # Nome file sicuro
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '-', '_')]).strip()
        safe_title = safe_title.replace(" ", "_")
        
        if not safe_title or len(safe_title) < 3:
            safe_title = "Investment_Analysis"
        
        filename = REPORTS_DIR / f"Report_{safe_title}_{conversation_id[:8]}.pdf"
        abs_filename = str(filename.absolute())
        
        print(f"   Salvataggio PDF in: {abs_filename}")
        
        # Converti HTML in PDF
        with open(abs_filename, 'wb') as result_file:
            pisa_status = pisa.CreatePDF(
                html_content,
                dest=result_file,
                encoding='UTF-8'
            )
        
        if pisa_status.err:
            print(f"   ❌ Errore durante conversione HTML->PDF: {pisa_status.err}")
            return None
        
        # Verifica che il file sia stato creato
        if not Path(abs_filename).exists():
            print(f"   ❌ File non creato")
            return None
        
        file_size = Path(abs_filename).stat().st_size
        if file_size == 0:
            print(f"   ❌ File creato ma vuoto (0 bytes)")
            return None
        
        print(f"   ✅ PDF salvato: {file_size} bytes")
        return abs_filename
        
    except Exception as e:
        print(f"   ❌ Errore durante generazione PDF: {e}")
        import traceback
        traceback.print_exc()
        return None
