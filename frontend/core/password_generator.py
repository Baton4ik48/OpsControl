import random
import string

# Транслитерация ЙЦУКЕН → QWERTY
_RU_TO_EN = {
    "й": "q", "ц": "w", "у": "e", "к": "r", "е": "t",
    "н": "y", "г": "u", "ш": "i", "щ": "o", "з": "p",
    "х": "[", "ъ": "]", "ф": "a", "ы": "s", "в": "d",
    "а": "f", "п": "g", "р": "h", "о": "j", "л": "k",
    "д": "l", "ж": ";", "э": "'", "я": "z", "ч": "x",
    "с": "c", "м": "v", "и": "b", "т": "n", "ь": "m",
    "б": ",", "ю": ".", "ё": "`",
}

# Буквы, которые дают спецсимволы при трансляции:
#   ж→;  э→'  б→,  ю→.  х→[  ъ→]
#
# Все слова подобраны так, чтобы в ПЕРВЫХ 4 буквах было 2-3 из этих букв.
# Это значит каждый 4-символьный блок пароля уже содержит 2-3 спецсимвола —
# отдельно добавлять ;!@# не нужно.

_WORDS = [
    # б + ж  →  , + ;
    "бежать",       # б,е,ж,а → ,t;f
    "биржа",        # б,и,р,ж → ,bh;
    "абажур",       # а,б,а,ж → f,f;
    "убежал",       # у,б,е,ж → e,t;
    # х + ж  →  [ + ;
    "хижина",       # х,и,ж,и → [b;b
    "хиджаб",       # х,и,д,ж → [bl;
    "хаджи",        # х,а,д,ж → [fl;
    # ю + ж  →  . + ;
    "южный",        # ю,ж,н,ы → .;ys
    "южанин",       # ю,ж,а,н → .;fy
    # ж + ю  →  ; + .
    "жюри",         # ж,ю,р,и → ;.hb
    # э + ж  →  ' + ;
    "этаж",         # э,т,а,ж → 'nf;
    "эжектор",      # э,ж,е,к → ';tr
    # э + х  →  ' + [
    "эхолот",       # э,х,о,л → '[jk
    # б + ю + ж  →  , + . + ;  (три спецсимвола!)
    "бюджет",       # б,ю,д,ж → ,.l;
    # б + ю  →  , + .
    "бюст",         # б,ю,с,т → ,.cn
    "бюро",         # б,ю,р,о → ,.hj
    "бюллетень",    # б,ю,л,л → ,.kk
    # ю + б  →  . + ,
    "юбка",         # ю,б,к,а → .,rf
    "юбилей",       # ю,б,и,л → .,bk
    # б + ъ  →  , + ]
    "объект",       # о,б,ъ,е → j,]t
    "субъект",      # с,у,б,ъ → ce,]
    # б + х  →  , + [
    "бухта",        # б,у,х,т → ,e[n
]

_LETTERS_PER_WORD = 4   # фиксировано: слова подобраны под 4 буквы

def _transliterate(word: str) -> str:
    result = []
    for ch in word:
        lower = ch.lower()
        mapped = _RU_TO_EN.get(lower, ch)
        if ch.isupper():
            mapped = mapped.upper()
        result.append(mapped)
    return "".join(result)

def generate_password(word_count: int = 3, digit_count: int = 2) -> tuple[str, str]:
    """
    Генерирует пароль и мнемоническую подсказку.

    Структура: [digit_count цифр] + [4 QWERTY-символа × word_count слов].
    Каждое слово подобрано так, что в первых 4 буквах содержит 2-3 из
    букв {ж,э,б,ю,х,ъ}, которые при трансляции дают спецсимволы ; ' , . [ ].

    Возвращает: (пароль, мнемоника_html)
    """
    word_count = max(2, min(5, word_count))
    digit_count = max(0, min(6, digit_count))

    digits = "".join(random.choice(string.digits) for _ in range(digit_count)) if digit_count else ""
    words = random.sample(_WORDS, word_count)

    parts = [digits]
    mnemonic_parts = [f'<span style="color:#FFB800">{digits}</span>']

    for word in words:
        prefix = word[:_LETTERS_PER_WORD]
        prefix_cap = prefix.capitalize()
        parts.append(_transliterate(prefix_cap))

        if len(word) > _LETTERS_PER_WORD:
            rest = word[_LETTERS_PER_WORD:]
            hint = (
                f'<span style="color:#FFB800">{prefix_cap}</span>'
                f'<span style="color:#546e7a">{rest}</span>'
            )
        else:
            hint = f'<span style="color:#FFB800">{word.capitalize()}</span>'

        mnemonic_parts.append(hint)

    password = "".join(parts)
    mnemonic = " &middot; ".join(mnemonic_parts)

    return password, mnemonic

if __name__ == "__main__":
    print("=== Генератор паролей (спецсимволы через ж,э,б,ю,х,ъ) ===\n")
    for _ in range(6):
        pwd, hint = generate_password()
        import re
        plain_hint = re.sub(r"<[^>]+>", "", hint)
        print(f"  ({len(pwd):2d} зн.)  {pwd}")
        print(f"           {plain_hint}\n")
