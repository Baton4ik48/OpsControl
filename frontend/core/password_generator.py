import random
import string


# ЙЦУКЕН → QWERTY транслитерация для мнемоники
_RU_TO_EN = {
    'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y',
    'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
    'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h',
    'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': "'",
    'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n',
    'ь': 'm', 'б': ',', 'ю': '.',
}

_WORDS = [
    "конь", "скачет", "волк", "бежит", "орёл", "летит", "тигр", "прыгает",
    "медведь", "ревёт", "лиса", "крадётся", "змея", "ползёт", "рысь", "мчится",
    "сокол", "парит", "буря", "гремит", "ветер", "воет", "гром", "грохочет",
]


def _transliterate(word: str) -> str:
    return "".join(_RU_TO_EN.get(ch.lower(), ch) for ch in word)


def generate_password(length: int = 16, min_digits: int = 4) -> tuple[str, str]:
    """
    Возвращает (password, mnemonic).
    Пароль: цифры + английские буквы в смешанном регистре.
    Мнемоника: два русских слова + цифровой префикс.
    """
    digits = [random.choice(string.digits) for _ in range(min_digits)]

    letters_count = length - min_digits
    letters = [
        random.choice(string.ascii_uppercase if random.random() > 0.5 else string.ascii_lowercase)
        for _ in range(letters_count)
    ]

    parts = digits + letters
    random.shuffle(parts)
    password = "".join(parts)

    # Мнемоника: число + два слова через дефис
    num = "".join(random.choice(string.digits) for _ in range(4))
    w1 = random.choice(_WORDS).capitalize()
    w2 = random.choice(_WORDS).capitalize()
    mnemonic = f"{num}-{w1}-{w2}"

    return password, mnemonic
