import { formatNumber, numberToPersianWords, parseFormattedNumber } from "../../utils/format";

interface Props {
  label: string;
  value?: number;
  placeholder?: string;
  suffix?: string;
  onChange: (value?: number) => void;
}

export default function FormattedNumberInput({
  label,
  value,
  placeholder,
  suffix,
  onChange,
}: Props) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-slate-400">{label}</span>
      <input
        inputMode="numeric"
        value={value === undefined ? "" : formatNumber(value, "en")}
        onChange={(event) => onChange(parseFormattedNumber(event.target.value))}
        placeholder={placeholder}
        className="mt-2 h-11 w-full rounded-lg border border-white/10 bg-slate-950/70 px-3 text-sm text-white outline-none transition focus:border-cyan-300/60 focus:ring-2 focus:ring-cyan-300/10"
      />
      <span className="mt-1 block min-h-5 text-xs text-cyan-100/70">
        {value ? `${numberToPersianWords(value)}${suffix ? ` ${suffix}` : ""}` : " "}
      </span>
    </label>
  );
}
