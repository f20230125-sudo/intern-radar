import type { FactKey, Kind, Role } from "./schema";

export const KIND_LABEL: Record<Kind, string> = {
  internship: "Internship",
  graduate: "Graduate programme",
  first_job: "First job",
};

export const KIND_PLURAL: Record<Kind, string> = {
  internship: "Internships",
  graduate: "Graduate programmes",
  first_job: "First jobs",
};

export const KIND_SHORT: Record<Kind, string> = {
  internship: "Internships",
  graduate: "Graduate",
  first_job: "First jobs",
};

export const KIND_NOTE: Record<Kind, string> = {
  internship: "A placement for someone still studying.",
  graduate: "A programme for people finishing or just finished.",
  first_job: "An ordinary job whose posting says it is open to someone with little or no experience.",
};

// The order facts are shown in: what decides whether a student can apply comes first.
export const FACT_ORDER: FactKey[] = ["eligibility", "start", "duration", "pay", "stage", "mode", "deadline"];

export const FACT_NAME: Record<FactKey, string> = {
  eligibility: "Who can apply",
  start: "Starts",
  duration: "Length",
  pay: "Pay",
  stage: "For",
  mode: "Where you work",
  deadline: "Apply by",
};

export const SYSTEM_NAME: Record<string, string> = {
  greenhouse: "Greenhouse",
  lever: "Lever",
  ashby: "Ashby",
  workable: "Workable",
  workday: "Workday",
  amazon: "amazon.jobs",
};

export function placeLine(role: Role): string {
  const names = role.places.map((p) => (p.emirate === "UAE" ? "UAE" : p.emirate));
  const more = role.elsewhere > 0 ? ` + ${role.elsewhere} elsewhere` : "";
  return names.join(", ") + more;
}

/** The short facts shown on a row, in order, without eligibility (which has its own treatment). */
export function rowFacts(role: Role): { key: FactKey; text: string }[] {
  const out: { key: FactKey; text: string }[] = [];
  for (const key of FACT_ORDER) {
    if (key === "eligibility" || key === "mode") continue;
    const fact = role.facts[key];
    if (!fact) continue;
    const text =
      key === "start" ? (fact.value === "immediate" ? "Starts now" : `Starts ${fact.label}`) : key === "deadline" ? `Apply by ${fact.label}` : fact.label;
    out.push({ key, text });
  }
  return out;
}
