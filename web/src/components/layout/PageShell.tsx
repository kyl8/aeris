export function PageShell({ children }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-zinc-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:64px_64px] opacity-30" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(255,255,255,0.03)_0%,transparent_60%)]" />
      {children}
    </div>
  )
}