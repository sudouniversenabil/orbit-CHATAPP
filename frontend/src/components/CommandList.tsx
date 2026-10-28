import { ChevronDown, Command, ExternalLink } from "lucide-react";
import { useState } from "react";
import type { CommandInfo } from "../services/api";

interface Props {
  commands: CommandInfo[];
}

export function CommandList({ commands }: Props) {
  const [expanded, setExpanded] = useState(false);
  return (
    <section className={`command-list ${expanded ? "expanded" : ""}`}>
      <button className="command-heading" onClick={() => setExpanded((value) => !value)} aria-expanded={expanded}>
        <span><Command size={16} /> Available commands <span className="command-count">{commands.length}</span></span>
        <ChevronDown size={16} />
      </button>
      {expanded && (
        <div className="command-grid">
          {commands.map((command) => (
            <article key={command.id} className="command-card">
              <h3>{command.name}</h3>
              <p>{command.description}</p>
              <div>{command.examples.map((example) => <span key={example}><ExternalLink size={11} /> {example}</span>)}</div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
