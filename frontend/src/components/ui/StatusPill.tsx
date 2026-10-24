import clsx from "clsx";

interface StatusPillProps {
  children: string;
  tone?: "amber" | "green" | "red";
}

export function StatusPill({ children, tone = "amber" }: StatusPillProps) {
  return (
    <span className={clsx("rounded px-2 py-1 font-mono text-[10px] font-bold uppercase tracking-wider", {
      "bg-amber-950 text-term-gold": tone === "amber",
      "bg-emerald-950 text-term-up": tone === "green",
      "bg-red-950 text-term-down": tone === "red"
    })}>
      {children}
    </span>
  );
}
