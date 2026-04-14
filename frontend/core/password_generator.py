import random
import string
import os

# ЙЦУКЕН → QWERTY транслитерация
_RU_TO_EN = {
    'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y',
    'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
    'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h',
    'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': "'",
    'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n',
    'ь': 'm', 'б': ',', 'ю': '.', 'ё': '`',
}

# ─── Словарь по ролям ───
# Только слова, в первых 4 буквах нет: ж, б, ю, э, х, ъ, ё

_SUBJECTS = [
    "пилот", "мастер", "турист", "капитан", "клиент",
    "сигнал", "магнит", "титан", "рыцарь", "кактус",
    "снайпер", "курсант", "маркер", "атлет", "партнер",
    "султан", "генерал", "стрелок", "кассир", "танкист",
]

_VERBS = [
    "красит", "тащит", "катит", "пилит", "лепит", "крутит",
    "кинул", "ставит", "тянет", "искал", "спасал", "строит",
    "кликнул", "таскал", "прятал", "кидает", "ловит", "несёт",
    "рисует", "варит", "ценит", "гасит", "ведёт", "дарит",
]

_OBJECTS = [
    "ракету", "лампу", "гитару", "салат", "парус", "кирпич",
    "канат", "маску", "плитку", "рапиру", "статус", "картину",
    "палатку", "пластик", "кассету", "настил", "пакет", "компас",
    "фигуру", "факел", "кулак", "каравай", "сервер", "кнопку",
]

_PLACES = [
    "в парке", "на крыше", "у канала", "на скале", "в каюте",
    "у стены", "на палубе", "в кратере", "у ракеты", "на мосту",
    "в центре", "на манеже", "в ангаре", "на катке", "у реки",
    "на старте", "в каньоне", "на рынке", "у причала", "на склоне",
]

# Шаблоны: роли → читаемое предложение
_TEMPLATES = {
    2: [("subject", "verb")],
    3: [
        ("subject", "verb", "object"),
        ("subject", "verb", "place"),
    ],
    4: [
        ("subject", "verb", "object", "place"),
    ],
    5: [
        ("subject", "verb", "object", "place", "subject"),
    ],
}

_POOLS = {
    "subject": _SUBJECTS,
    "verb":    _VERBS,
    "object":  _OBJECTS,
    "place":   _PLACES,
}


def _transliterate(word: str) -> str:
    """Переводит русское слово в QWERTY-раскладку с сохранением регистра."""
    result = []
    for ch in word:
        lower = ch.lower()
        mapped = _RU_TO_EN.get(lower, ch)
        if ch.isupper():
            mapped = mapped.upper()
        result.append(mapped)
    return "".join(result)


def _clean_word(word: str) -> str:
    """'в парке' → 'парке'"""
    parts = word.strip().split()
    return parts[-1] if parts else word


def generate_password(
    word_count: int = 4,
    letters_per_word: int = 4,
    digit_count: int = 2,
) -> tuple[str, str]:
    """
    Генерирует пароль и осмысленную мнемоническую фразу.

    Структура фразы:
        2 слова: «Пилот красит»
        3 слова: «Пилот красит ракету»
        4 слова: «Пилот красит ракету на крыше»
        5 слов:  «Пилот красит ракету на крыше мастер»

    Пароль: число + первые N букв каждого слова в QWERTY.
    """
    word_count = max(2, min(5, word_count))
    letters_per_word = max(3, min(4, letters_per_word))
    digit_count = max(0, min(4, digit_count))

    # Число
    number = "".join(random.choice(string.digits) for _ in range(digit_count)) if digit_count else ""

    # Шаблон
    templates = _TEMPLATES[word_count]
    template = random.choice(templates)

    password_parts = [number]
    mnemonic_parts = [f'<span style="color:#FFB800">{number}</span>'] if number else []

    for role in template:
        pool = _POOLS[role]
        raw_word = random.choice(pool)
        word = _clean_word(raw_word)

        prefix = word[:letters_per_word].capitalize()
        transliterated = _transliterate(prefix)
        password_parts.append(transliterated)

        # Мнемоника с предлогом
        if role == "place" and raw_word != word:
            preposition = raw_word[:raw_word.rfind(word)].strip()
            if len(word) > letters_per_word:
                hint = f'<span style="color:#FFB800">{word[:letters_per_word].capitalize()}</span>{word[letters_per_word:]}'
            else:
                hint = f'<span style="color:#FFB800">{word.capitalize()}</span>'
        else:
            if len(word) > letters_per_word:
                hint = f'<span style="color:#FFB800">{word[:letters_per_word].capitalize()}</span>{word[letters_per_word:]}'
            else:
                hint = f'<span style="color:#FFB800">{word.capitalize()}</span>'
        mnemonic_parts.append(hint)

    password = "".join(password_parts)
    mnemonic = " ".join(mnemonic_parts)

    return password, mnemonic


# ─── Демо ───
if __name__ == "__main__":
    print("=== Генератор осмысленных паролей ===\n")

    configs = [
        (2, 3, 2,  "Кто + Делает"),
        (3, 4, 2,  "Кто + Делает + Что"),
        (4, 4, 2,  "Кто + Делает + Что + Где"),
        (5, 3, 4,  "Кто + Делает + Что + Где + Кто"),
    ]

    for words, letters, digits, label in configs:
        print(f"[{label}]")
        for _ in range(3):
            pwd, hint = generate_password(words, letters, digits)
            print(f"  ({len(pwd):2d} зн.)  {pwd}")
            print(f"           {hint}")
        print()