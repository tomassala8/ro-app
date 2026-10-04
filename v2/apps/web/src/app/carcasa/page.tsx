// Esqueleto: se sustituye en la Fase 3 del plan por la carcasa (menú lateral, cabecera, ⌘K, «ver como»).
export default function Inicio() {
  return (
    <main className="mx-auto max-w-xl p-8">
      <div className="rounded-lg border border-line bg-card p-5 shadow-sm">
        <h1 className="text-[20px] leading-7 font-bold text-ink">App de RO · v2</h1>
        <p className="text-mid">Next + Nest + Postgres. El plan está en migracion/PLAN_MAESTRO.md.</p>
      </div>
    </main>
  );
}
