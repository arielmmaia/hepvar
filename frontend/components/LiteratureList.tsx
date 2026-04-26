import clsx from "clsx";
import type { LiteratureHit } from "@/lib/types";

const LANG_LABEL: Record<string, { flag: string; name: string; tone: string }> = {
  en: { flag: "🇬🇧", name: "English", tone: "bg-hairline/40 text-ink2" },
  pt: { flag: "🇧🇷", name: "Portuguese", tone: "bg-leaf/15 text-leaf" },
  es: { flag: "🇪🇸", name: "Spanish", tone: "bg-amber/15 text-amber" },
  it: { flag: "🇮🇹", name: "Italian", tone: "bg-teal/15 text-teal" },
  fr: { flag: "🇫🇷", name: "French", tone: "bg-oxblood/10 text-oxblood" },
};

export function LiteratureList({ hits }: { hits: LiteratureHit[] }) {
  if (!hits || hits.length === 0) {
    return <p className="text-muted text-sm italic serif-italic">No literature hits across PubMed and Europe PMC.</p>;
  }
  return (
    <ul className="divide-y hairline">
      {hits.slice(0, 12).map((h) => {
        const lang = LANG_LABEL[h.language] ?? LANG_LABEL.en;
        const url = h.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${h.pmid}/` : h.doi ? `https://doi.org/${h.doi}` : "#";
        return (
          <li key={(h.pmid ?? h.doi ?? h.title) + h.title} className="py-3">
            <div className="flex items-center gap-2 mb-1 text-[11px] font-mono">
              <span className={clsx("rounded-full px-2 py-[1px]", lang.tone)}>{lang.flag} {lang.name}</span>
              {h.is_case_report && <span className="rounded-full px-2 py-[1px] bg-oxblood/10 text-oxblood">case report</span>}
              {h.is_functional_study && <span className="rounded-full px-2 py-[1px] bg-teal/10 text-teal">functional</span>}
              {h.year && <span className="text-muted">{h.year}</span>}
              {h.relevance_score > 0 && <span className="ml-auto text-muted">rel {h.relevance_score.toFixed(1)}</span>}
            </div>
            <a href={url} target="_blank" rel="noreferrer" className="text-[14px] text-ink hover:text-oxblood leading-snug block">
              {h.title}
            </a>
            {h.journal && <p className="text-[12px] text-muted italic serif-italic mt-0.5">{h.journal}</p>}
          </li>
        );
      })}
    </ul>
  );
}
