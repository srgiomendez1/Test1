"""Spanish (Excel) -> openfootball English team-name aliases for World Cup 2026.

Used by convert_bets.py (Excel side) and shared so the match keys line up with
the openfootball results feed. Keys are normalized (stripped) Spanish names.
"""

ES_TO_EN = {
    "Alemania": "Germany",
    "Arabia Saudita": "Saudi Arabia",
    "Argelia": "Algeria",
    "Argentina": "Argentina",
    "Australia": "Australia",
    "Austria": "Austria",
    "Bosnia y Herzegovina": "Bosnia & Herzegovina",
    "Brasil": "Brazil",
    "Bélgica": "Belgium",
    "Cabo Verde": "Cape Verde",
    "Canadá": "Canada",
    "Colombia": "Colombia",
    "Corea del Sur": "South Korea",
    "Costa de Marfil": "Ivory Coast",
    "Croacia": "Croatia",
    "Curazao": "Curaçao",
    "Ecuador": "Ecuador",
    "Egipto": "Egypt",
    "Escocia": "Scotland",
    "España": "Spain",
    "Estados Unidos": "USA",
    "Francia": "France",
    "Ghana": "Ghana",
    "Haití": "Haiti",
    "Inglaterra": "England",
    "Irak": "Iraq",
    "Irán": "Iran",
    "Japón": "Japan",
    "Jordania": "Jordan",
    "Marruecos": "Morocco",
    "México": "Mexico",
    "Noruega": "Norway",
    "Nueva Zelanda": "New Zealand",
    "Panamá": "Panama",
    "Paraguay": "Paraguay",
    "Países Bajos": "Netherlands",
    "Portugal": "Portugal",
    "Qatar": "Qatar",
    "RD Congo": "DR Congo",
    "República Checa": "Czech Republic",
    "Senegal": "Senegal",
    "Sudáfrica": "South Africa",
    "Suecia": "Sweden",
    "Suiza": "Switzerland",
    "Turquía": "Turkey",
    "Túnez": "Tunisia",
    "Uruguay": "Uruguay",
    "Uzbekistán": "Uzbekistan",
}

# English (openfootball) -> Spanish, for the UI.
EN_TO_ES = {en: es for es, en in ES_TO_EN.items()}


def to_en(es_name):
    """Map a Spanish team name to the openfootball English name (raises if unknown)."""
    key = (es_name or "").strip()
    if key not in ES_TO_EN:
        raise KeyError(f"Unmapped Spanish team name: {es_name!r}")
    return ES_TO_EN[key]
