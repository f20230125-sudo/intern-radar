"use client";

import { useState } from "react";

import { MAX_CV_CHARS } from "@/lib/fit";

type Props = { skills: string[] | null; onMatch: (text: string | null) => void; onClose: () => void };

export function FitPanel({ skills, onMatch, onClose }: Props) {
  const [text, setText] = useState("");
  return (
    <div className="fitbox" id="fit-panel">
      <label htmlFor="cv">Paste the text of your CV</label>
      <p>
        It is read here, in your browser, against a fixed list of skills. The text is not sent anywhere and is not saved; only the list of skills found is kept,
        and only until you close this tab.
      </p>
      <textarea
        id="cv"
        value={text}
        maxLength={MAX_CV_CHARS}
        spellCheck={false}
        placeholder="Projects, skills, coursework, experience…"
        onChange={(e) => setText(e.target.value)}
      />
      {skills ? (
        <p role="status">
          {skills.length
            ? `Found ${skills.length}: ${skills.join(", ")}. Roles that name any of these are now listed first.`
            : "None of the skills on the list appear in that text. Try pasting the skills and projects sections."}
        </p>
      ) : null}
      <div className="actions" style={{ marginTop: 0 }}>
        <button type="button" className="btn" disabled={!text.trim()} style={!text.trim() ? { opacity: 0.5, cursor: "default" } : undefined} onClick={() => onMatch(text)}>
          Match roles
        </button>
        {skills ? (
          <button
            type="button"
            className="btn quiet"
            onClick={() => {
              setText("");
              onMatch(null);
            }}
          >
            Forget my CV
          </button>
        ) : null}
        <button type="button" className="btn quiet" onClick={onClose}>
          Close
        </button>
      </div>
    </div>
  );
}
