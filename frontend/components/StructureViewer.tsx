"use client";
import { useEffect, useRef } from "react";

export function StructureViewer({ pdbUrl, position, refAa, altAa }: {
  pdbUrl: string | null | undefined;
  position?: number | null;
  refAa?: string | null;
  altAa?: string | null;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!pdbUrl || !ref.current) return;
    let viewer: any = null;
    let cancelled = false;

    (async () => {
      const mod: any = await import("3dmol/build/3Dmol.js");
      const $3Dmol = mod.default ?? mod;
      const data = await fetch(pdbUrl).then((r) => r.text());
      if (cancelled || !ref.current) return;
      viewer = $3Dmol.createViewer(ref.current, {
        backgroundColor: "0xfbf9f4",
      });
      viewer.addModel(data, "pdb");
      viewer.setStyle({}, { cartoon: { color: "spectrum" } });
      if (position) {
        viewer.setStyle({ resi: position }, { stick: { colorscheme: "redCarbon" }, cartoon: { color: "spectrum" } });
        viewer.addLabel(`${refAa ?? "?"}→${altAa ?? "?"} @${position}`, {
          position: { resi: position }, backgroundColor: "0x5E1A1A",
          backgroundOpacity: 0.85, fontColor: "white", fontSize: 11,
        });
        viewer.zoomTo({ resi: position });
      } else {
        viewer.zoomTo();
      }
      viewer.render();
    })();

    return () => {
      cancelled = true;
      try { viewer?.clear(); } catch { /* noop */ }
    };
  }, [pdbUrl, position, refAa, altAa]);

  if (!pdbUrl) {
    return (
      <div className="h-[280px] rounded-xl border-2 border-dashed hairline flex items-center justify-center text-muted text-sm italic serif-italic">
        no AlphaFold reference structure
      </div>
    );
  }

  return (
    <div className="relative h-[320px] rounded-xl border hairline overflow-hidden bg-bg">
      <div ref={ref} className="absolute inset-0" />
      <div className="absolute bottom-2 right-2 font-mono text-[10px] text-muted uppercase tracking-[0.2em]">
        AlphaFold-EBI · 3Dmol.js
      </div>
    </div>
  );
}
