from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import ParsedAd
from .normalizer import compact_text, normalize_text, parse_number_token


VEHICLE_PATTERNS: list[tuple[str, str, str]] = [
    ("pride_van", "پراید وانت", r"\bپراید\s*وانت\b|\bپراید\s*۱۵۱\b|\bپراید\s*151\b"),
    ("pride", "پراید", r"\bپراید\b|\bپرايد\b"),
    ("peugeot_207", "پژو 207", r"\b(?:پژو\s*)?(?:207|۲۰۷)\b"),
    ("peugeot_206", "پژو 206", r"\b(?:پژو\s*)?(?:206|۲۰۶)\b"),
    ("soren", "سورن", r"\bسورن\b|\bsoren\b"),
    ("pars", "پژو پارس", r"\bپارس\b"),
    ("dena", "دنا", r"\bدنا\b|\bdena\b"),
    ("tara", "تارا", r"\bتارا\b|\btara\b"),
    ("rana", "رانا", r"\bرانا\b"),
    ("shahin", "شاهین", r"\bشاهین\b"),
    ("quick", "کوییک", r"\bکوییک\b|\bکوئیک\b|\bquick\b"),
    ("saina", "ساینا", r"\bساینا\b"),
    ("atlas", "اطلس", r"\bاطلس\b"),
    ("sahand", "سهند", r"\bسهند\b"),
    ("tiba", "تیبا", r"\bتیبا\b"),
    ("rira", "ریرا", r"\bریرا\b"),
    ("fidelity", "فیدلیتی", r"\bفیدلیتی\b|\bfidelity\b"),
    ("dignity", "دیگنیتی", r"\bدیگنیتی\b|\bdignity\b"),
    ("respect", "رسپکت", r"\bرسپکت\b|\brespect\b"),
    ("lucano_l8", "لوکانو L8", r"\bلوکانو\s*l?\s*8\b|\blucano\s*l?\s*8\b"),
    ("lucano_l7", "لوکانو L7", r"\bلوکانو\s*l?\s*7\b|\blucano\s*l?\s*7\b|\bل7\b"),
    ("changan_cs55", "چانگان CS55", r"\bچانگان\s*cs\s*55\b|\bcs55\b"),
    ("changan_cs35", "چانگان CS35", r"\bچانگان\s*cs\s*35\b|\bcs35\b"),
    ("jack_j7", "جک J7", r"\bجک\s*j\s*7\b|\bj7\b"),
    ("jack_a5", "جک A5", r"\bجک\s*a\s*5\b|\ba5\b"),
    ("kmc_t9", "KMC T9", r"\b(?:کی\s*ام\s*سی|kmc)\s*t\s*9\b"),
    ("kmc_j7", "KMC J7", r"\b(?:کی\s*ام\s*سی|kmc)\s*j\s*7\b"),
    ("arrizo_5", "آریزو 5", r"\bآریزو\s*5\b|\barrizo\s*5\b"),
    ("arrizo_6", "آریزو 6", r"\bآریزو\s*6\b|\barrizo\s*6\b"),
    ("arrizo_8", "آریزو 8", r"\bآریزو\s*8\b|\barrizo\s*8\b"),
    ("x55", "ام وی ام X55", r"\bx\s*55\b|\bایکس\s*55\b|\bایکس55\b"),
    ("x22", "ام وی ام X22", r"\bx\s*22\b|\bایکس\s*22\b|\bایکس22\b"),
    ("mvm", "ام وی ام", r"\bام\s*وی\s*ام\b|\bmvm\b"),
    ("lamari", "لاماری", r"\bلاماری\b"),
    ("mazda_ez6", "مزدا EZ6", r"\bمزدا\s*ez\s*6\b|\bez6\b"),
    ("tank_500", "تانک 500", r"\bتانک\s*500\b|\btank\s*500\b"),
    ("corolla", "کرولا", r"\bکرولا\b|\bcorolla\b"),
    ("beijing", "بیجینگ", r"\bبیجینگ\b|\bbeijing\b"),
]

COLORS = [
    "سفید",
    "مشکی",
    "خاکستری",
    "نقره ای",
    "سیمی",
    "قرمز",
    "آبی",
    "نوک مدادی",
    "تیتانیوم",
    "سبز",
    "زرد",
    "قهوه ای",
    "پرتغالی",
]

BUYER_RE = re.compile(r"خریدار|خریدارم|می\s*خوام|میخوام|مشتری|نیاز\s*دارم")
SOLD_RE = re.compile(r"انجام\s*شد|فروخته|تمام\s*شد|تموم\s*شد|اوکی\s*شد")
SPAM_RE = re.compile(
    r"بازدید|ربات|تبلیغ|کانال\s*(?:واتساپ|روبیکا|تلگرام)|https?://|t\.me/|"
    r"بروزرسانی\s*قیمت|به\s*روزرسانی\s*قیمت|قیمت\s*خودروهای\s*پرفروش|قیمت\s*دلار|"
    r"این\s*رسانه"
)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?98|0)?9\d{9}(?!\d)")
SPACED_PHONE_RE = re.compile(
    r"(?<!\d)(?:\+?98|0)?9\d{2}(?:"
    r"[\s-]*\d{3}[\s-]*\d{4}|"
    r"[\s-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}|"
    r"[\s-]*\d{2}[\s-]*\d{2}[\s-]*\d{3}"
    r")(?!\d)"
)
NUMBER_RE = re.compile(r"(?<!\d)(\d{1,3}(?:[./,]\d{1,3}){1,3}|\d{1,5})(?!\d)")

PRICE_HINT_RE = re.compile(r"قیمت|فوری|خوش\s*قیمت|کف|زیر\s*قیمت|🔥|💰")
NON_PRICE_CONTEXT_RE = re.compile(
    r"کارکرد|تا\s*کار|کار\s*کرد|امپر|آمپر|برج|مدل|سال|نفره|پر\b|ماه|بیمه|گارانتی|"
    r"لاستیک|پلاک|کد|رمز|دونه|دستگاه|عدد|تماس|شماره|کاور|دوربین|km|کیلومتر|درجه"
)
DELIVERY_RE = re.compile(r"قابل\s*تحویل|تحویل\s*(?:روز|فردا|فردایی|الان)|فردایی|کفی|سند\s*آماده|موجود")


def split_export_messages(path: str | Path) -> list[tuple[str, str]]:
    text = Path(path).read_text(encoding="utf-8")
    pieces = re.split(r"(?m)^--- پیام\s+(\d+)\s+---\s*$", text)
    messages: list[tuple[str, str]] = []
    for idx in range(1, len(pieces), 2):
        message_id = pieces[idx].strip()
        body = pieces[idx + 1].strip()
        if body:
            messages.append((message_id, body))
    return messages


def _is_separator_line(line: str) -> bool:
    """آیا این خط فقط یک نویسه‌ی تکرارشده است؟ (مثل ______ یا ====== یا ➖➖➖➖)

    این خطوط معمولاً برای جدا کردن چند آگهی مستقل داخل یک پیام تلگرام
    استفاده می‌شوند. حداقل ۸ بار تکرار لازم است تا اشتباهی روی خطوط
    تزئینی کوتاه (مثل 🔥🔥🔥) فعال نشود.
    """
    stripped = line.strip()
    if len(stripped) < 8:
        return False
    first = stripped[0]
    if first.isalnum():
        return False
    return all(ch == first for ch in stripped)


PRICE_MARKER_CHARS = "🔴🟡🟢🔵🟠🟣⚫⚪🟤💰💵💸💲"
FULL_DATE_RE = re.compile(r"\b14\d{2}/\d{1,2}/\d{1,2}\b")


def _is_price_only_paragraph(paragraph: str) -> bool:
    """آیا این خط/پاراگراف فقط یک «خط قیمتِ مستقل» است؟

    باید نشانه‌رنگی (🔴🟡...) یا جداکننده هزارگان (./,) داشته باشد، وگرنه
    یک شماره تلفن ساده (که هم فقط رقم است) به‌اشتباه مرز آگهی حساب می‌شود.
    """
    stripped = paragraph.strip()
    if not stripped or re.search(r"[A-Za-zآ-ی]", stripped):
        return False
    if FULL_DATE_RE.search(stripped):
        return False
    digits_only = re.sub(r"\D", "", stripped)
    if not digits_only:
        return False
    if PHONE_RE.fullmatch(digits_only) or SPACED_PHONE_RE.fullmatch(stripped):
        return False
    has_marker = any(ch in stripped for ch in PRICE_MARKER_CHARS)
    has_separator = bool(re.search(r"[./,]", stripped))
    return has_marker or has_separator


def _split_by_price_lines(raw_text: str) -> list[str]:
    """پیام‌های چندتایی بدون خط جداکننده را از روی خطوطِ قیمت می‌شکند.

    هر خطِ قیمت، پایان‌بخشِ همان آگهی است (چه با خط خالی از توضیحش جدا شده
    باشد چه فقط با یک Enter). خطوط انتهایی بدون قیمت (مثل شماره تماس یا
    لینک مشترک) به آخرین آگهی می‌چسبند.
    """
    lines = raw_text.split("\n")
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        current.append(line)
        if _is_price_only_paragraph(line):
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current = []
    tail = "\n".join(current).strip()
    if tail:
        if blocks:
            blocks[-1] = blocks[-1] + "\n\n" + tail
        else:
            blocks.append(tail)
    return blocks if len(blocks) > 1 else [raw_text]


def split_multi_ad_blocks(raw_text: str) -> list[str]:
    """یک پیام تلگرام را روی خطوط جداکننده به چند «آگهی مستقل» می‌شکند.

    دو روش را امتحان می‌کند: اول خط جداکننده‌ی صریح (______)، بعد پاراگراف‌های
    قیمتِ تکرارشونده (برای پیام‌هایی که جداکننده ندارند). اگر هیچ‌کدام بیش از
    یک تکه ندهند، پیام دست‌نخورده برمی‌گردد.
    """
    lines = raw_text.split("\n")
    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if _is_separator_line(line):
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current = []
        else:
            current.append(line)
    tail = "\n".join(current).strip()
    if tail:
        blocks.append(tail)
    if len(blocks) > 1:
        return blocks
    return _split_by_price_lines(raw_text)


def detect_vehicle(text: str) -> tuple[str | None, str | None]:
    lowered = text.lower()
    for key, name, pattern in VEHICLE_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return key, name
    return None, None


def detect_trim(text: str) -> str | None:
    hints = [
        "اتومات",
        "اتوماتیک",
        "دنده ای",
        "cvt",
        "تیوفایو",
        "tu5",
        "tu3",
        "xu7p",
        "آپشنال",
        "اپشنال",
        "آبشنال",
        "v1",
        "v4",
        "پلاس",
        "سانروف",
        "دوگانه",
        "موتور پارس",
        "برقی",
        "هیدرولیک",
    ]
    found = [hint for hint in hints if re.search(rf"(?<!\w){re.escape(hint)}(?!\w)", text, re.IGNORECASE)]
    return " ".join(dict.fromkeys(found)) or None


def detect_color(text: str) -> str | None:
    for color in COLORS:
        if color in text:
            return color
    return None


def detect_year(text: str) -> int | None:
    patterns = [
        r"(?:مدل|سال)\s*(14\d{2}|40[0-9]|[789]\d)",
        r"\b(14\d{2})\b",
        r"\b(40[0-9])\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        value = int(match.group(1))
        if 400 <= value <= 409:
            return 1000 + value
        if 70 <= value <= 99:
            return 1300 + value
        if 1390 <= value <= 1409:
            return value
    match = re.search(r"\b(20[12]\d)\b", text)
    if match:
        return int(match.group(1))
    return None


def detect_month(text: str) -> int | None:
    match = re.search(r"برج\s*(\d{1,2}|روز)", text)
    if not match:
        return None
    if match.group(1) == "روز":
        return None
    value = int(match.group(1))
    return value if 1 <= value <= 12 else None


def detect_mileage(text: str) -> int | None:
    match = re.search(r"(\d{1,3}(?:[./,]\d{3})+|\d{3,6})\s*(?:تا\s*)?(?:کار|کارکرد|امپر|آمپر)", text)
    if not match:
        return None
    value = parse_number_token(match.group(1))
    if value is None:
        return None
    return value if 0 <= value <= 500000 else None


def detect_phone(text: str) -> str | None:
    match = PHONE_RE.search(text)
    if not match:
        spaced = SPACED_PHONE_RE.search(text)
        if not spaced:
            return None
        phone = re.sub(r"\D", "", spaced.group(0))
        if phone.startswith("98") and len(phone) == 12:
            return "0" + phone[2:]
        return phone
    phone = match.group(0)
    if phone.startswith("98") and len(phone) == 12:
        return "0" + phone[2:]
    return phone


def detect_delivery(text: str) -> str | None:
    matches = DELIVERY_RE.findall(text)
    if not matches:
        return None
    return " / ".join(dict.fromkeys(match.strip() for match in matches if match.strip()))


def classify_status(text: str, vehicle_key: str | None) -> str:
    if SOLD_RE.search(text):
        return "sold"
    if BUYER_RE.search(text):
        return "buyer"
    if SPAM_RE.search(text) and (
        not vehicle_key or re.search(r"بروزرسانی\s*قیمت|قیمت\s*خودروهای\s*پرفروش|قیمت\s*دلار|این\s*رسانه", text)
    ):
        return "spam"
    if "قیمت" in text and "☎" in text:
        return "call_price"
    return "sale"


def _line_for_span(text: str, start: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end].strip()


SHAMSI_YEAR_PRESENT_RE = re.compile(r"\b14\d{2}\b|(?:مدل|سال)\s*(?:14\d{2}|40[0-9]|[789]\d)\b")


def _score_price_candidate(
    text: str,
    match: re.Match[str],
    vehicle_key: str | None,
    shamsi_year_present: bool = False,
) -> tuple[int | None, int]:
    token = match.group(1)
    start, end = match.span(1)
    before = text[max(0, start - 28) : start]
    after = text[end : min(len(text), end + 28)]
    context = before + token + after
    line = _line_for_span(text, start)
    raw_value = parse_number_token(token)
    if raw_value is None:
        return None, -100
    prev_char = text[start - 1] if start > 0 else ""
    next_char = text[end] if end < len(text) else ""
    if re.search(r"[A-Za-zآ-ی]", prev_char + next_char):
        return None, -100

    if PHONE_RE.fullmatch(token):
        return None, -100
    if re.fullmatch(r"(?:140\d|40\d)/(?:1[0-2]|0?[1-9])", token):
        # نماد فشرده «سال/برج» مثل ۴۰۵/۲ یا ۱۴۰۵/۱۲ — قیمت نیست
        return None, -100
    if re.search(r"(?:\+?98|0)?9\d{9}", token):
        return None, -100
    if SPACED_PHONE_RE.search(line):
        return None, -100
    if re.search(r"تانک\s*500", line, flags=re.IGNORECASE) and token == "500":
        return None, -100

    explicit_price = bool(re.search(rf"قیمت\s*[:：\-]?\s*{re.escape(token)}", context))
    line_rest = line.replace(token, "", 1)
    mostly_number_line = not bool(re.search(r"[A-Za-zآ-ی]", line_rest))
    has_strong_non_price = bool(
        re.search(r"کارکرد|تا\s*کار|کار\s*کرد|امپر|آمپر|دونه|عدد|کاور|دوربین|km|کیلومتر|درجه", line, flags=re.IGNORECASE)
    )
    if has_strong_non_price and not explicit_price:
        return None, -60
    if NON_PRICE_CONTEXT_RE.search(line) and not PRICE_HINT_RE.search(context) and not mostly_number_line:
        return None, -25

    normalized_price = _normalize_price_value(token, raw_value, line)
    if normalized_price is None:
        return None, -100
    if not (250 <= normalized_price <= 100000):
        return None, -100
    if normalized_price >= 25000 and re.search(r"[./,]", token) and not PRICE_HINT_RE.search(context):
        return None, -60
    if 400 <= raw_value <= 409 and not explicit_price:
        return None, -60
    if 1300 <= raw_value <= 1420 and not explicit_price and not mostly_number_line:
        return None, -60
    if 2010 <= raw_value <= 2030 and not explicit_price and not mostly_number_line:
        return None, -60
    if (
        2010 <= raw_value <= 2027
        and not explicit_price
        and not re.search(r"[./,]", token)
        and not shamsi_year_present
    ):
        # عدد ۴ رقمی شبیه سال میلادی، بدون جداکننده و بدون هیچ سال شمسی در پیام
        # => این سالِ مدل خودروی وارداتی است، نه قیمت (مثل: «مزدا ez6 سفید \n ۲۰۲۵»)
        return None, -100

    score = 0
    if PRICE_HINT_RE.search(context):
        score += 20
    if mostly_number_line:
        score += 28
    if re.search(r"🔥|💰", line):
        score += 10
    if vehicle_key:
        score += 8
    if raw_value in range(400, 410) or raw_value in range(1400, 1410):
        score -= 45
    if re.search(r"برج|مدل|سال", line):
        score -= 25
    if re.search(r"کار|امپر|آمپر|km|کیلومتر", line, flags=re.IGNORECASE):
        score -= 35
    if raw_value <= 12 and not _is_bare_number_line(token, line):
        score -= 40
    return normalized_price, score


def _is_bare_number_line(token: str, line: str) -> bool:
    """آیا خط واقعاً فقط همین عدد است (بدون هیچ حرف یا رقم دیگر)؟

    قبلاً اینجا با \\D (غیر-رقم) چک می‌شد که اشتباهاً حروف فارسی را هم
    «غیر رقم» حساب می‌کرد و خطوطی مثل «سند آماده ۱ ساعته» را هم به اشتباه
    «خط تنها-عدد» تشخیص می‌داد. همچنین باید رقم دیگری هم در خط نباشد،
    وگرنه خطوطی مثل «۱۴۰۵،۲» (سال،برج) رقم دوم را قیمت حساب می‌کنند.
    """
    rest = line.replace(token, "", 1)
    return not re.search(r"[A-Za-zآ-ی0-9]", rest)


def _normalize_price_value(token: str, raw_value: int, line: str) -> int | None:
    if re.search(r"[./,]", token):
        parts = [part for part in re.split(r"[./,]", token) if part]
        if len(parts) >= 2:
            first = int(parts[0])
            second = int(parts[1])
            if len(parts) == 3 and first <= 99:
                return first * 1000 + second
            if first <= 99 and len(parts[1]) in (2, 3):
                return first * 1000 + second
            return raw_value
    if 1 <= raw_value <= 9 and _is_bare_number_line(token, line):
        return raw_value * 1000
    return raw_value


def _mask_full_dates(text: str) -> str:
    """تاریخ کامل مثل ۱۴۰۵/۰۴/۱۷ را قبل از تشخیص قیمت با فاصله جایگزین می‌کند.

    وگرنه تکه‌ی «۰۴/۱۷» از وسط تاریخ با الگوی رایج «X/YYY یعنی X۰۰۰+YYY میلیون»
    قاطی می‌شود و مثلاً عدد ۴۰۱۷ به‌جای قیمت واقعی ساخته می‌شود.
    """
    return FULL_DATE_RE.sub(lambda m: " " * len(m.group(0)), text)


def detect_price(text: str, vehicle_key: str | None) -> int | None:
    shamsi_year_present = bool(SHAMSI_YEAR_PRESENT_RE.search(text))
    text = _mask_full_dates(text)
    candidates: list[tuple[int, int]] = []
    for match in NUMBER_RE.finditer(text):
        price, score = _score_price_candidate(text, match, vehicle_key, shamsi_year_present)
        if price is not None and score >= 15:
            candidates.append((score, price))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][1]


def confidence_score(ad: ParsedAd) -> float:
    score = 0.0
    if ad.vehicle_key:
        score += 0.28
    if ad.price_million:
        score += 0.34
    if ad.phone:
        score += 0.12
    if ad.year:
        score += 0.08
    if ad.delivery:
        score += 0.05
    if ad.status == "sale":
        score += 0.13
    elif ad.status in {"buyer", "spam", "sold"}:
        score -= 0.35
    return max(0.0, min(1.0, round(score, 2)))


def build_dedup_key(normalized_text: str) -> str:
    """کلید تشخیص تکراری واقعی: فاصله/بزرگی‌کوچکی حروف/ایموجی را نادیده می‌گیرد.

    مثال: «کوییکgxrسفید...۴۲هزار» و «کوییک GXR سفید ... ۴۲ هزار 📞»
    باید یک آگهی حساب شوند، نه دو آگهی جدا.
    """
    lowered = normalized_text.lower()
    # فقط حروف فارسی، حروف انگلیسی و رقم را نگه می‌داریم؛ باقی (فاصله، ایموجی،
    # علامت‌ها) حذف می‌شود تا تفاوت‌های ظاهری روی تشخیص تکراری اثر نگذارند.
    return re.sub(r"[^0-9a-zA-Zآ-ی]", "", lowered)


def parse_message(
    source_message_id: str,
    raw_text: str,
    message_date: datetime | None = None,
    source: str = "import",
) -> ParsedAd:
    normalized = normalize_text(raw_text)
    compact = compact_text(normalized)
    vehicle_key, vehicle_name = detect_vehicle(compact)
    status = classify_status(compact, vehicle_key)
    ad = ParsedAd(
        source_message_id=source_message_id,
        raw_text=raw_text.strip(),
        normalized_text=normalized,
        dedup_key=build_dedup_key(normalized),
        source=source,
        message_date=message_date,
        vehicle_key=vehicle_key,
        vehicle_name=vehicle_name,
        trim=detect_trim(compact),
        price_million=detect_price(normalized, vehicle_key),
        year=detect_year(compact),
        month=detect_month(compact),
        color=detect_color(compact),
        mileage_km=detect_mileage(compact),
        phone=detect_phone(compact),
        status=status,
        delivery=detect_delivery(compact),
        confidence=0.0,
    )
    ad.confidence = confidence_score(ad)
    return ad


def parse_message_group(
    source_message_id: str,
    raw_text: str,
    message_date: datetime | None = None,
    source: str = "import",
) -> list[ParsedAd]:
    """پیام را (در صورت نیاز) به چند آگهی مستقل می‌شکند و هرکدام را پارس می‌کند.

    همه‌ی آگهی‌های حاصل از یک پیام، همان source_message_id واقعی را دارند
    (چون همه به یک پیام واقعی در تلگرام لینک می‌شوند)؛ تشخیص تکراری‌نبودن
    آن‌ها در دیتابیس بر عهده‌ی UNIQUE(source_message_id, raw_text) است که
    چون raw_text هر تکه فرق دارد، مشکلی پیش نمی‌آید.
    """
    blocks = split_multi_ad_blocks(raw_text)
    return [parse_message(source_message_id, block, message_date, source) for block in blocks]