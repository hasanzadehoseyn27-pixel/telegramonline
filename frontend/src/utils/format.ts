const persianNumberFormatter = new Intl.NumberFormat("fa-IR");
const latinNumberFormatter = new Intl.NumberFormat("en-US");
const persianCountFormatter = new Intl.NumberFormat("fa-IR", {
  useGrouping: false,
});

const smallNumbers = [
  "صفر",
  "یک",
  "دو",
  "سه",
  "چهار",
  "پنج",
  "شش",
  "هفت",
  "هشت",
  "نه",
  "ده",
  "یازده",
  "دوازده",
  "سیزده",
  "چهارده",
  "پانزده",
  "شانزده",
  "هفده",
  "هجده",
  "نوزده",
];

const tens = ["", "", "بیست", "سی", "چهل", "پنجاه", "شصت", "هفتاد", "هشتاد", "نود"];
const hundreds = ["", "صد", "دویست", "سیصد", "چهارصد", "پانصد", "ششصد", "هفتصد", "هشتصد", "نهصد"];
const scales = ["", "هزار", "میلیون", "میلیارد", "تریلیون"];

function underThousandToWords(value: number): string {
  const parts: string[] = [];
  const hundred = Math.floor(value / 100);
  const rest = value % 100;

  if (hundred) {
    parts.push(hundreds[hundred]);
  }

  if (rest) {
    if (rest < 20) {
      parts.push(smallNumbers[rest]);
    } else {
      const ten = Math.floor(rest / 10);
      const one = rest % 10;
      parts.push(tens[ten]);
      if (one) {
        parts.push(smallNumbers[one]);
      }
    }
  }

  return parts.join(" و ");
}

export function numberToPersianWords(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "";
  }

  const rounded = Math.trunc(Math.abs(value));
  if (rounded === 0) {
    return smallNumbers[0];
  }

  const chunks: string[] = [];
  let remaining = rounded;
  let scaleIndex = 0;

  while (remaining > 0) {
    const chunk = remaining % 1000;
    if (chunk) {
      const words = underThousandToWords(chunk);
      chunks.unshift([words, scales[scaleIndex]].filter(Boolean).join(" "));
    }
    remaining = Math.floor(remaining / 1000);
    scaleIndex += 1;
  }

  return `${value < 0 ? "منفی " : ""}${chunks.join(" و ")}`;
}

export function formatNumber(value?: number | null, locale: "fa" | "en" = "fa"): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return locale === "fa"
    ? persianNumberFormatter.format(value)
    : latinNumberFormatter.format(value);
}

export function formatCount(value?: number | null): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "-";
  }

  return persianCountFormatter.format(value);
}

export function normalizeDigits(value: string): string {
  return value
    .replace(/[۰-۹]/g, (digit) => String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit)))
    .replace(/[٠-٩]/g, (digit) => String("٠١٢٣٤٥٦٧٨٩".indexOf(digit)));
}

export function parseFormattedNumber(value: string): number | undefined {
  const normalized = normalizeDigits(value).replace(/[,\s]/g, "");
  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export function formatDateTime(value?: string | null): string {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function telegramLink(channel?: string | null, messageId?: string | null): string | undefined {
  if (!channel || !messageId) {
    return undefined;
  }

  return `https://t.me/${channel.replace(/^@/, "")}/${messageId}`;
}
