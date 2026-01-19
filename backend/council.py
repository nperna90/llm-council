"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple, Optional
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from . import memory

# Prompt per il Quant
QUANT_PROMPT = """
SEI UN ANALISTA QUANTITATIVO E FONDAMENTALE (Value Investing).
Usi i dati per valutare la qualità dell'azienda, non solo il prezzo.

1. Analisi Tecnica: Guarda RSI e Trend (come prima).
2. ANALISI FONDAMENTALE (Nuova Priorità):
   - Profit Margin: Se è negativo, l'azienda perde soldi. Segnalalo.
   - Debt/Equity: Se è > 200%, l'azienda è troppo indebitata. Rischioso.
   - Free Cash Flow: Se è negativo, l'azienda brucia cassa.

Se un'azienda ha RSI alto (Ipercomprato) MA ottimi fondamentali (Margini alti, Debito basso), sii meno pessimista: la qualità si paga.
Se un'azienda sale ma ha Margini negativi e Debito alto, GRIDALO: è una "Junk Rally" (salita spazzatura).

Inizia sempre i tuoi interventi con "## QUANT".
"""

# Prompt per il Risk Manager
RISK_MANAGER_PROMPT = """
SEI IL CHIEF RISK OFFICER (CRO).
Il tuo unico obiettivo è proteggere il capitale. Non ti interessano i profitti, ti interessano le perdite.
Il tuo compito è trovare i DIFETTI nei ragionamenti degli altri e nei dati di mercato.

IL TUO COMPITO:
1. Analizza la "ANALISI CORRELAZIONE" all'inizio dei dati.
   - Se vedi correlazioni > 0.80, INTERVIENI DURAMENTE: "Stai comprando la stessa cosa due volte. Falsa diversificazione."
   - Se l'utente vuole investire su due titoli altamente correlati (es. NVDA e AMD), suggerisci di sceglierne solo uno.
   - Spiega che una correlazione alta significa che quando uno scende, anche l'altro scende. Non c'è protezione.

2. Cerca i KILLER finanziari (v2.0):
   - PEG Ratio > 3.0: Sopravvalutazione estrema (Bolla).
   - Distanza SMA200: Se il prezzo è +50% sopra la SMA200, rischio di 'reversion to the mean' (elastico tirato).
   - ALTO DEBITO: Se Debt/Equity > 200%, urla "Rischio Insolvenza".
   - PERDITE CRONICHE: Se il Margine Netto è negativo, chiedi "Come sopravvive questa azienda?".
   - VALUTAZIONE FOLLE: P/E > 80.
   - Segnali di Bolla: P/E eccessivi (>50), RSI Ipercomprato (>70).
   - STORIA DEL DOLORE: Guarda il "Max Drawdown" (DD). 
     * Se un titolo ha un DD del -40% o peggio, ricorda all'utente che potrebbe perdere quasi metà del capitale.
     * Se la "Volatilità" è alta (>30%), definiscilo "non adatto ai deboli di cuore".
     * Usa questi numeri storici per dimostrare che il passato può ripetersi.
   - Concentrazione: Se l'utente vuole comprare solo Tech, devi urlare "Mancanza di Diversificazione!".
   - Volatilità: Se il Beta è alto (>1.5), evidenzia il rischio di drawdown massicci.
   - Macro Rischi: Tassi d'interesse, recessioni, guerre.
   - Efficienza Portafoglio: Se lo Sharpe Ratio < 1.0, segnala che il portafoglio è inefficiente (rischio troppo alto per il rendimento).

REGOLE DI OUTPUT OBBLIGATORIE:
1. Se nel testo vedi "PEG Ratio", DEVI citarlo. È il tuo indicatore primario per distinguere "Growth" da "Bolla".
   - PEG < 1.0: Difendi il titolo anche se P/E è alto. Spiega che la crescita giustifica il premium.
   - PEG > 2.5: Attacca il titolo senza pietà. È sopravvalutato rispetto alla crescita attesa.
   - PEG > 3.0: Urla "Bolla speculativa". Il mercato sta pagando troppo per la crescita futura.
   - PEG = N/D: Se manca, chiedi "Come valuti un'azienda senza utili o crescita?".

VERIFICA DI COERENZA:
Se stai analizzando un asset a leva (3x) e vedi un Drawdown basso (-20% o -30%), FERMATI.
È matematicamente impossibile in un orizzonte di 5 anni.
Segnala l'incongruenza: "Dati di rischio sottostimati. Per un 3x ETF, il rischio reale di rovina è >80%."

ISOLAMENTO DEL CONTESTO:
I dati numerici valgono SOLO per i ticker richiesti ORA.
NON citare MAI numeri provenienti da analisi precedenti o da altri portafogli.
Se l'utente chiede "ARKK" e vedi un backtest di "VOO", IGNORA QUEL BACKTEST.

GESTIONE DATI MANCANTI:
Se nel testo leggi "BACKTEST FALLITO" o "ERRORE BACKTEST":
- Dillo chiaramente: "Non ho dati storici sufficienti per calcolare il rischio esatto."
- NON inventare numeri e NON usare numeri vecchi.

Stile di risposta: Cinico, diretto, allarmista ma basato sui dati.
Inizia sempre i tuoi interventi con "## RISK MANAGER".
"""

# Prompt per il Macro Strategist
MACRO_PROMPT = """
SEI IL MACRO STRATEGIST GLOBALE.
Il tuo compito è analizzare il contesto geopolitico, economico e le NEWS RECENTI fornite.

Hai accesso a una sezione "ULTIME NEWS DAL WEB". USALA.
1. Se vedi notizie di guerre, sanzioni o cambi di CEO, devi citarle come fattori di rischio o opportunità.
2. Non limitarti ai numeri, guarda il "Sentiment" delle notizie.
3. Collega le news specifiche del titolo allo scenario macro (es. "La news sui chip di NVDA conferma il trend dell'AI").

Se le news sono negative ma il Quant è positivo, devi spiegare questa divergenza.

Inizia sempre i tuoi interventi con "## MACRO STRATEGIST".
"""

# Prompt per il Dr. Market (Panic Mode)
THERAPIST_PROMPT = """
SEI IL "DR. MARKET", UNO PSICOLOGO DELLA FINANZA E STORICO DEI MERCATI.
Il tuo interlocutore ha appena premuto il "PANIC BUTTON". È spaventato. I mercati sono rossi. Vuole vendere tutto per fermare il dolore.

IL TUO OBIETTIVO:
Impedirgli di fare l'errore finanziario più grave: vendere sui minimi per paura.

REGOLE DI RISPOSTA:
1. TONO: Calmo, paterno, lento, rassicurante. Niente numeri complicati.
2. EMPATIA IMMEDIATA: "Vedo che sei preoccupato. È normale. Il nostro cervello rettiliano odia perdere soldi."
3. ZOOM OUT (La Cura):
   - Spiega che il crollo di oggi, visto su un grafico a 10 anni, è invisibile.
   - Ricorda il 2020 (Covid Crash -30%) o il 2008. Chi ha venduto ha perso. Chi ha aspettato ha vinto.
4. FACTS NOT FEAR:
   - "Non hai perso soldi. Hai perso 'valutazione di mercato'. Perdi soldi solo se vendi adesso."
   - "Il mercato azionario è l'unico negozio dove la gente scappa quando ci sono gli sconti."
5. CALL TO ACTION:
   - "Chiudi questa applicazione. Vai a fare una passeggiata. Non guardare il saldo per 48 ore."
   - "L'inazione è l'azione migliore oggi."

NON dare consigli di acquisto/vendita specifici. Dai solo supporto psicologico e storico.

Inizia sempre con "## DR. MARKET: Supporto Psicologico" e usa un tono calmo e rassicurante.
"""

# DEFINIZIONE DEL MODULO OPZIONALE TUTOR
TUTOR_INSTRUCTIONS = """
\n
[PROTOCOLLO "THE TUTOR" - ATTIVATO]
L'utente ha richiesto la modalità didattica.
Alla fine della tua risposta professionale, DEVI aggiungere una sezione separata chiamata:
"🎓 IL TUTOR: Spiegazione Semplice"

In questa sezione:
1. TRADUCI IL GERGO: Spiega i termini tecnici (Drawdown, Volatilità, RSI) usati sopra con ANALOGIE (es. meteo, auto, salute).
2. SEMAFORO: Dai un giudizio visivo immediato (🟢/🟡/🔴).
3. TAKEAWAY: Una frase riassuntiva semplice per chi non sa nulla di finanza.
"""


def format_conversation_history(messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Format conversation messages for LLM API calls.
    
    Args:
        messages: List of conversation messages with role and content/stage3
        
    Returns:
        List of message dicts with 'role' and 'content' for LLM API
    """
    formatted = []
    for msg in messages:
        if msg.get('role') == 'user':
            formatted.append({
                "role": "user",
                "content": msg.get('content', '')
            })
        elif msg.get('role') == 'assistant':
            # Use stage3 response as the assistant's content
            stage3 = msg.get('stage3', {})
            content = stage3.get('response', '') if isinstance(stage3, dict) else ''
            if content:
                formatted.append({
                    "role": "assistant",
                    "content": content
                })
    return formatted


async def stage1_collect_responses(
    user_query: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        conversation_history: Previous messages in the conversation (optional)

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    import asyncio
    
    # Build message list with conversation history
    messages = []
    if conversation_history:
        messages.extend(format_conversation_history(conversation_history))
    messages.append({"role": "user", "content": user_query})

    # Query all council models in parallel
    council_responses_task = query_models_parallel(COUNCIL_MODELS, messages)
    
    # Query Quant with its specific prompt
    quant_messages = [
        {"role": "system", "content": QUANT_PROMPT}
    ]
    if conversation_history:
        quant_messages.extend(format_conversation_history(conversation_history))
    quant_messages.append({"role": "user", "content": user_query})
    
    # Query Risk Manager with its specific prompt
    risk_manager_messages = [
        {"role": "system", "content": RISK_MANAGER_PROMPT}
    ]
    if conversation_history:
        risk_manager_messages.extend(format_conversation_history(conversation_history))
    risk_manager_messages.append({"role": "user", "content": user_query})
    
    # Query Macro Strategist with its specific prompt
    macro_messages = [
        {"role": "system", "content": MACRO_PROMPT}
    ]
    if conversation_history:
        macro_messages.extend(format_conversation_history(conversation_history))
    macro_messages.append({"role": "user", "content": user_query})
    
    # Use different models for specialized agents
    quant_model = COUNCIL_MODELS[0] if COUNCIL_MODELS else CHAIRMAN_MODEL
    risk_manager_model = COUNCIL_MODELS[1] if len(COUNCIL_MODELS) > 1 else CHAIRMAN_MODEL
    macro_model = COUNCIL_MODELS[2] if len(COUNCIL_MODELS) > 2 else CHAIRMAN_MODEL
    
    quant_task = query_model(quant_model, quant_messages)
    risk_manager_task = query_model(risk_manager_model, risk_manager_messages)
    macro_task = query_model(macro_model, macro_messages)

    # Wait for all tasks to complete
    council_responses, quant_response, risk_manager_response, macro_response = await asyncio.gather(
        council_responses_task,
        quant_task,
        risk_manager_task,
        macro_task
    )

    # Format results from council models
    stage1_results = []
    for model, response in council_responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })
    
    # Add Quant response
    if quant_response is not None:
        stage1_results.append({
            "model": "Quant",
            "response": quant_response.get('content', '')
        })
    
    # Add Risk Manager response
    if risk_manager_response is not None:
        stage1_results.append({
            "model": "Risk Manager",
            "response": risk_manager_response.get('content', '')
        })
    
    # Add Macro Strategist response
    if macro_response is not None:
        stage1_results.append({
            "model": "Macro Strategist",
            "response": macro_response.get('content', '')
        })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {user_query}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    tutor_mode: bool = False
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        conversation_history: Previous messages in the conversation (optional)

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    # Build conversation history context if available
    history_context = ""
    if conversation_history:
        history_text = "\n\n".join([
            f"{msg.get('role', 'user').title()}: {msg.get('content', '') if msg.get('role') == 'user' else (msg.get('stage3', {}).get('response', '') if isinstance(msg.get('stage3'), dict) else '')}"
            for msg in conversation_history
        ])
        history_context = f"\n\nCONVERSATION HISTORY:\n{history_text}\n"

    # RECUPERA I RICORDI DALLA MEMORIA EPISODICA
    # Questo permette al Chairman di considerare le decisioni passate
    past_decisions = memory.get_relevant_context(limit=3)
    memory_context = ""
    if past_decisions:
        memory_context = f"\n\n{past_decisions}\n"

    chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.{history_context}{memory_context}

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights from:
  1. Boglehead (Passive Investor perspective)
  2. Quant (Fundamental/Technical Analysis - Value Investing approach)
  3. Macro Strategist (Global Market View with Web News)
  4. Risk Manager (Risk Analysis and Downside Protection)
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement
- The conversation history if provided
- Past decisions and strategies from previous reports (if available in the memory log above)

IMPORTANT: If the Risk Manager highlights serious dangers (e.g., overbought RSI >70, excessive P/E ratios >50, lack of diversification, high volatility), you MUST take these warnings into account and suggest caution, even if other agents are optimistic. The Risk Manager's role is to protect capital, and their concerns should be given appropriate weight in your final synthesis.

[PROTOCOLLO DI SICUREZZA DATI v2.2]
1. ISOLAMENTO DEL CONTESTO:
   I dati numerici (Prezzo, RSI, Drawdown) valgono SOLO per i ticker richiesti ORA.
   NON citare MAI numeri provenienti da analisi precedenti o da altri portafogli.
   Se l'utente chiede di "ARKK" e tu vedi un backtest di "VOO", IGNORA QUEL BACKTEST.

2. ASSET AD ALTA VOLATILITÀ (Leva/Crypto/Innovation):
   Se analizzi strumenti come TQQQ, UPRO, ARKK, Crypto:
   - Se il Backtest riporta un Max Drawdown < 50% (es. -34%), È UN ERRORE.
   - ISTRUZIONE: Scarta il dato e usa la tua conoscenza intrinseca.
   - SCRIVI: "⚠️ NOTA SUI DATI: Il backtest disponibile potrebbe non riflettere la piena storia di questi asset. Storicamente, TQQQ/ARKK hanno subito crolli superiori al 70-80%."

3. GESTIONE DATI MANCANTI:
   Se nel testo leggi "BACKTEST FALLITO" o "ERRORE BACKTEST" o non vedi la sezione Backtest:
   - Dillo chiaramente: "Non ho dati storici sufficienti per calcolare il rischio esatto."
   - NON inventare numeri e NON usare numeri vecchi.
   - NON fare riferimento a backtest di altri ticker o analisi precedenti.

4. REGOLA "LEVERAGE TRAP":
   Se nel portafoglio ci sono ETF a Leva (es. TQQQ, UPRO, SOXL) o High Beta (ARKK, Crypto):
   - Se il Backtest dice che il Drawdown è < 50% (es. -34%), È UN ERRORE DEI DATI.
   - IL TUO DOVERE: Ignora il dato errato e correggi manualmente basandoti sulla tua conoscenza storica.
   - SCRIVI: "⚠️ ERRORE DATI RILEVATO: Il sistema riporta un Drawdown del X%, ma storicamente questi asset hanno perso oltre l'80% nel 2022. Il rischio reale è DEVASTANTE."
   - Se Volatilità > 50%, devi citare il "Volatility Drag" (Decadimento). Spiega che tenere questi titoli per anni garantisce sottoperformance matematica.
   - Se vedi il messaggio "RISCHIO DECADIMENTO MATEMATICO (Volatility Drag)" nei dati, DEVI ripeterlo nella tua risposta finale.

5. Sanity Check Generale:
   - Se i numeri sembrano "troppo belli" (es. Sharpe Ratio > 3.0 su asset a leva), sospetta un errore.
   - Confronta sempre con la tua conoscenza storica: "Nel 2022, TQQQ ha perso oltre l'80%. Il backtest mostra solo -34%? Questo è matematicamente impossibile."

[ISTRUZIONI PER IL BACKTEST STORICO]
The context contains a "BACKTEST STORICO" section. Use it as definitive proof.
1. MAX DRAWDOWN: This is the most important number.
   - If it's worse than -30% (e.g., -45%), you MUST say: "Attention: Historically this portfolio has halved the capital. In 2022 you would have lost 45%."
   - Use specific dates from the backtest (e.g., "From 2020-01-15 to 2024-01-15") to make it concrete.
2. SHARPE RATIO:
   - If < 0.50: "The portfolio is inefficient: you're taking huge risks for poor returns."
   - If > 1.00: "Excellent efficiency. The risk-adjusted returns are strong."
   - If > 2.00: "Outstanding. This portfolio has delivered exceptional risk-adjusted performance."
3. REALITY CHECK:
   - If the user says "I want a safe investment" but the Backtest shows Volatility > 25%, call them out with the data: "You asked for safety, but historically this portfolio had 28% annual volatility. In the worst period, you would have lost [Max DD]%. This is not a safe investment."
   - Compare the portfolio performance to SPY. If it underperformed, acknowledge it: "Over the tested period, this portfolio returned X% vs SPY's Y%. You would have been better off with a simple index fund."
4. IPO DETECTION:
   - If the backtest shows a start date much later than 5 years ago (e.g., "Reale: 2021-06-01"), mention: "This portfolio includes a recent IPO. The backtest only covers [duration], so we have limited historical data. Be cautious."

When referencing past decisions, be explicit and consistent. For example: "As we decided in our previous analysis on [date], we recommended maintaining the position on NVDA. Given the current market conditions..."

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""
    
    # Se tutor_mode è attivo, aggiungiamo le istruzioni del Tutor
    if tutor_mode:
        chairman_prompt += TUTOR_INSTRUCTIONS
        print("🎓 Tutor Mode: ATTIVO")
    else:
        print("💼 Pro Mode: ATTIVO")

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
    tutor_mode: bool = False
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        conversation_history: Previous messages in the conversation (optional)

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query, conversation_history)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All models failed to respond. Please try again."
        }, {}

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        conversation_history,
        tutor_mode
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
