import { Lock } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api/auth.api";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("superadmin");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(username, password);
      navigate("/", { replace: true });
    } catch {
      setError("نام کاربری یا رمز عبور اشتباه است");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid h-screen place-items-center bg-slate-950 px-4 text-white">
      <form onSubmit={submit} className="glass-panel w-full max-w-sm rounded-xl p-6">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-xl bg-cyan-300 text-slate-950">
          <Lock size={25} />
        </div>
        <h1 className="mt-5 text-center text-2xl font-black">ورود به TelegramOnline</h1>
        <p className="mt-2 text-center text-sm text-slate-400">پنل خصوصی مانیتورینگ بازار خودرو</p>
        <div className="mt-6 grid gap-3">
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="h-11 rounded-lg border border-white/10 bg-slate-950/70 px-3 text-sm outline-none focus:border-cyan-300/60"
            placeholder="نام کاربری"
          />
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            type="password"
            className="h-11 rounded-lg border border-white/10 bg-slate-950/70 px-3 text-sm outline-none focus:border-cyan-300/60"
            placeholder="رمز عبور"
          />
          {error && <div className="rounded-lg bg-rose-500/15 p-3 text-sm text-rose-100">{error}</div>}
          <button
            disabled={loading}
            className="h-11 rounded-lg bg-cyan-300 font-black text-slate-950 transition hover:bg-white disabled:opacity-60"
          >
            {loading ? "در حال ورود..." : "ورود"}
          </button>
        </div>
      </form>
    </div>
  );
}
