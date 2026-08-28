import { Fragment, ReactNode } from "react";

// Briefings and battlecards are LLM-generated markdown, but always simple —
// headers, bold/italic, and bullet/numbered lists (see the system prompts in
// backend/app/services/briefing_service.py and battlecard_service.py). A
// full markdown library is more than that needs; this covers exactly what
// the prompts actually produce.

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|_[^_]+_)/g).filter(Boolean);
  return parts.map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (
      (part.startsWith("*") && part.endsWith("*")) ||
      (part.startsWith("_") && part.endsWith("_"))
    ) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    return <Fragment key={key}>{part}</Fragment>;
  });
}

export function renderMarkdown(markdown: string): ReactNode {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let listItems: string[] | null = null;
  let listOrdered = false;
  let paragraph: string[] = [];

  function flushParagraph() {
    if (paragraph.length === 0) return;
    const key = `p-${blocks.length}`;
    blocks.push(
      <p key={key} className="m-0">
        {renderInline(paragraph.join(" "), key)}
      </p>
    );
    paragraph = [];
  }

  function flushList() {
    if (!listItems || listItems.length === 0) {
      listItems = null;
      return;
    }
    const key = `l-${blocks.length}`;
    const items = listItems.map((item, i) => (
      <li key={`${key}-${i}`}>{renderInline(item, `${key}-${i}`)}</li>
    ));
    blocks.push(
      listOrdered ? (
        <ol key={key} className="m-0 flex flex-col gap-1 pl-5">
          {items}
        </ol>
      ) : (
        <ul key={key} className="m-0 flex flex-col gap-1 pl-5">
          {items}
        </ul>
      )
    );
    listItems = null;
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line === "") {
      flushParagraph();
      flushList();
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const key = `h-${blocks.length}`;
      blocks.push(
        <p key={key} className="m-0 text-[13px] font-semibold text-[var(--text-primary)]">
          {renderInline(heading[2], key)}
        </p>
      );
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.*)$/);
    const numbered = line.match(/^\d+[.)]\s+(.*)$/);
    if (bullet || numbered) {
      flushParagraph();
      const ordered = !!numbered;
      if (listItems && listOrdered !== ordered) flushList();
      listOrdered = ordered;
      listItems = listItems ?? [];
      listItems.push((bullet ?? numbered)![1]);
      continue;
    }

    flushList();
    paragraph.push(line);
  }
  flushParagraph();
  flushList();

  return <div className="flex flex-col gap-2.5">{blocks}</div>;
}
