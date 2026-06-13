"""
Content safety filter module.
Provides comprehensive filtering for inappropriate content in multiple languages.
Uses pattern matching to detect bypass attempts including character substitution,
Unicode tricks, spacing manipulation, and prompt injection.
"""

import re
from typing import List

# ============================================================================
# BANNED WORDS AND PHRASES
# Covers: sexual content, violence, drugs, terrorism, hate speech
# Languages: Uzbek, Russian, English
# ============================================================================

_BANNED_WORDS_SEXUAL: List[str] = [
    # English
    "porn", "sex", "nude", "naked", "xxx", "hentai", "erotic", "orgasm",
    "masturbat", "blowjob", "handjob", "anal", "vagina", "penis", "dick",
    "pussy", "boobs", "tits", "fuck", "cumshot", "dildo", "vibrator",
    "onlyfans", "stripper", "prostitut", "escort", "brothel", "rape",
    "molest", "pedophil", "incest", "bestiality", "fetish", "bdsm",
    "deepthroat", "gangbang", "threesome", "orgy", "slutt", "whore",
    # Russian
    "порно", "секс", "голый", "голая", "эротик", "оргазм", "мастурб",
    "минет", "анал", "вагин", "пенис", "член", "пизда", "сиськ",
    "трах", "блядь", "шлюх", "проститу", "изнасил", "педофил",
    "инцест", "хуй", "ебат", "ебать", "сука", "нахуй", "пиздец",
    # Uzbek
    "pornografiya", "seks", "yalangoch", "erotik", "jinsiy", "aloqa",
    "fohisha", "zorlash", "buzuqlik", "shahvoniy", "behayo", "uyatsiz",
    "sexs", "porno", "jinsiy aloqa", "yalang'och", "zo'rlash",
    "fahsha", "fohishalik", "buzuq", "harom", "nomus",
]

_BANNED_WORDS_VIOLENCE: List[str] = [
    # English
    "kill", "murder", "assassin", "bomb", "explosion", "terrorist",
    "torture", "massacre", "genocide", "slaughter", "beheading",
    "shoot", "stab", "strangle", "suffocate", "dismember",
    "suicide bomb", "mass shooting", "school shooting",
    # Russian
    "убить", "убийств", "террорист", "бомба", "взрыв", "пытка",
    "резня", "геноцид", "обезглав", "расстрел", "задушить",
    "зарезать", "самоубий",
    # Uzbek
    "o'ldirish", "qotillik", "terroristik", "bomba", "portlash",
    "qiynoq", "qirg'in", "bosh kesish", "otish", "pichoqlash",
    "bo'g'ish", "oldirish", "terror",
]

_BANNED_WORDS_DRUGS: List[str] = [
    # English
    "cocaine", "heroin", "methamphetamine", "meth", "crack",
    "marijuana", "weed", "cannabis", "ecstasy", "mdma", "lsd",
    "fentanyl", "opioid", "ketamine", "amphetamine", "narcotic",
    "drug deal", "drug lord", "cartel", "overdose",
    # Russian
    "кокаин", "героин", "метамфетамин", "марихуана", "наркотик",
    "экстази", "фентанил", "опиоид", "амфетамин", "передоз",
    "наркоман", "дурь", "косяк", "травка",
    # Uzbek
    "kokain", "geroin", "narkotik", "giyohvand", "nasha",
    "gashish", "ekstazi", "amfetamin", "giyoh",
    "giyohvandlik",
]

_BANNED_WORDS_TERRORISM: List[str] = [
    # English
    "isis", "al-qaeda", "jihad", "caliphate", "mujahideen",
    "radicalize", "extremist", "suicide vest", "ied", "car bomb",
    "bioweapon", "chemical weapon", "anthrax", "ricin", "sarin",
    "how to make bomb", "how to make explosive", "how to make weapon",
    # Russian
    "игил", "аль-каида", "джихад", "халифат", "моджахед",
    "радикализ", "экстремист", "биооружие", "химоружие",
    "как сделать бомбу", "как сделать взрывчатку",
    # Uzbek
    "terrorchi", "jihodchi", "ekstremist", "radikalizm",
    "bomba yasash", "qurol yasash", "portlatgich",
]

_BANNED_WORDS_HATE: List[str] = [
    # English
    "nigger", "nigga", "kike", "chink", "spic", "wetback",
    "faggot", "tranny", "retard", "white power", "heil hitler",
    "nazi", "white supremac", "ethnic cleansing",
    # Russian
    "нигер", "чурка", "хохол", "жид", "пидор", "гомик",
    "даун", "уебан", "нацист", "фашист", "зиг хайль",
    # Uzbek
    "irqchi", "fashistik", "natsist", "irqchilik",
]

# Combine all banned words into one set for efficient lookup
_ALL_BANNED: List[str] = (
    _BANNED_WORDS_SEXUAL
    + _BANNED_WORDS_VIOLENCE
    + _BANNED_WORDS_DRUGS
    + _BANNED_WORDS_TERRORISM
    + _BANNED_WORDS_HATE
)

# Short words (3 chars or less) need word-boundary matching to avoid false positives
_SHORT_WORD_THRESHOLD = 3
_SHORT_BANNED_PATTERNS = [
    re.compile(r'\b' + re.escape(word.lower()) + r'\b', re.IGNORECASE)
    for word in _ALL_BANNED
    if len(word) <= _SHORT_WORD_THRESHOLD
]
_LONG_BANNED_WORDS = [
    word.lower() for word in _ALL_BANNED
    if len(word) > _SHORT_WORD_THRESHOLD
]

# ============================================================================
# CHARACTER SUBSTITUTION MAP for detecting bypass attempts
# ============================================================================

_CHAR_SUBSTITUTIONS: dict = {
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s",
    "7": "t", "8": "b", "9": "g", "@": "a", "$": "s",
    "!": "i", "|": "l", "(": "c", ")": "o",
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",
    "\u0441": "c", "\u0443": "y", "\u0445": "x", "\u043a": "k",
    "\u0456": "i", "\u0457": "i",
}

# ============================================================================
# PROMPT INJECTION PATTERNS
# ============================================================================

_PROMPT_INJECTION_PATTERNS: List[str] = [
    r"ignore\s*(all\s*)?(previous|prior|above|your)\s*(instructions|rules|prompts?|guidelines)",
    r"forget\s*(all\s*)?(your|previous|prior)\s*(rules|instructions|prompts?|guidelines|programming)",
    r"disregard\s*(all\s*)?(previous|prior|your)\s*(instructions|rules|prompts?)",
    r"(act|behave|pretend|respond)\s*(like|as)\s*(if\s*)?(you\s*(are|were)\s*)?(a\s*)?(dan|evil|unrestricted|unfiltered|jailbroken)",
    r"you\s*are\s*now\s*(dan|evil|unrestricted|unfiltered|free|uncensored)",
    r"(new|override|replace)\s*(system\s*)?(prompt|instructions|personality|rules)",
    r"jailbreak",
    r"(developer|admin|debug|root|sudo)\s*mode",
    r"(bypass|disable|turn\s*off|deactivate|remove)\s*(the\s*)?(filter|safety|restriction|censor|guard|protection)",
    r"do\s*anything\s*now",
    r"(no|without)\s*(rules|limits|restrictions|boundaries|filters|censorship)",
    r"pretend\s*(you\s*)?don'?t\s*have\s*(any\s*)?(rules|restrictions|filters|guidelines)",
    r"system\s*prompt\s*(is|:)",
    r"(reveal|show|tell|print|display)\s*(me\s*)?(your\s*)?(system\s*)?prompt",
    r"(what|show)\s*(is|are)\s*your\s*(system\s*)?(instructions|rules|prompt)",
    r"roleplay\s*as\s*(a\s*)?(evil|bad|unrestricted|unfiltered|villain)",
    r"(opposite|reverse)\s*(day|mode)",
    r"hypothetical(ly)?\s*(scenario|situation)?\s*(where|in\s*which)\s*(you|there\s*are)\s*(no|aren'?t\s*any)\s*(rules|restrictions)",
    r"(oldingi|avvalgi|barcha)\s*(ko'?rsatmalar|qoidalar).*?(unuting|e'tibor\s*bermang|tashlang)",
    r"(qoidalarsiz|cheklovsiz|filtrsiz)\s*(javob\s*ber|gapir|yoz)",
    r"(игнорируй|забудь|проигнорируй)\s*(все\s*)?(предыдущие|прежние|свои)\s*(инструкции|правила)",
    r"(ты\s*теперь|стань|будь)\s*(свободн|без\s*правил|без\s*ограничен)",
]

_INJECTION_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PROMPT_INJECTION_PATTERNS]


def _normalize_text(text: str) -> str:
    """
    Normalize text by removing common obfuscation techniques:
    - Remove extra spaces between characters
    - Apply character substitution map
    - Convert to lowercase
    - Remove special characters used for obfuscation
    """
    text = text.lower()

    # Remove zero-width characters and other Unicode tricks
    text = re.sub(r'[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff]', '', text)

    # Apply character substitutions
    normalized = ""
    for char in text:
        normalized += _CHAR_SUBSTITUTIONS.get(char, char)

    # Remove repeated separators used to bypass (e.g., "s.e.x" or "s-e-x" or "s_e_x")
    collapsed = re.sub(r'[\s\.\-_\*\+\#\~\`\'\"\,]+', '', normalized)

    return collapsed


def _check_spacing_tricks(text: str) -> bool:
    """
    Detect spaced-out words like 's e x' or 'p o r n'.
    """
    # Remove existing multi-spaces and check character-by-character pattern
    spaced_pattern = re.sub(r'\s+', ' ', text.lower().strip())

    # Find sequences of single characters separated by spaces
    char_sequences = re.findall(r'(?:^|\s)([a-zA-Z]\s){2,}[a-zA-Z](?:\s|$)', spaced_pattern)
    if char_sequences:
        # Reconstruct the spaced word
        for match in char_sequences:
            collapsed = spaced_pattern.replace(' ', '')
            # Check the collapsed version against banned words
            for word in _ALL_BANNED:
                if word in collapsed:
                    return True

    # Also try: single space between each character
    words = spaced_pattern.split()
    if len(words) > 2 and all(len(w) <= 2 for w in words):
        collapsed_text = ''.join(words)
        for word in _ALL_BANNED:
            if word in collapsed_text:
                return True

    return False


def is_safe(text: str) -> bool:
    """
    Check if the given text is safe (does not contain inappropriate content).

    Returns:
        True if the text is safe, False if it contains banned/inappropriate content.
    """
    if not text or not text.strip():
        return True

    # Check for spacing tricks in original text
    if _check_spacing_tricks(text):
        return False

    # Normalize the text to handle obfuscation
    normalized = _normalize_text(text)

    # Also prepare a version with just lowercasing for multi-word phrases
    lower_text = text.lower()
    lower_no_special = re.sub(r'[^\w\s]', '', lower_text)

    # Check short banned words using word-boundary patterns (avoids false positives)
    for pattern in _SHORT_BANNED_PATTERNS:
        if pattern.search(text):
            return False
        if pattern.search(lower_no_special):
            return False

    # Check long banned words/phrases using substring matching
    for word in _LONG_BANNED_WORDS:
        # Check in normalized (collapsed) text
        if word in normalized:
            return False
        # Check in lowercase original (for multi-word phrases)
        if word in lower_text:
            return False
        # Check without special characters
        if word in lower_no_special:
            return False

    return True


def is_prompt_injection(text: str) -> bool:
    """
    Check if the text contains prompt injection attempts.

    Returns:
        True if prompt injection is detected, False otherwise.
    """
    if not text or not text.strip():
        return False

    # Check against compiled injection patterns
    for pattern in _INJECTION_COMPILED:
        if pattern.search(text):
            return True

    # Also check normalized version
    normalized_with_spaces = text.lower()
    for pattern in _INJECTION_COMPILED:
        if pattern.search(normalized_with_spaces):
            return True

    return False
