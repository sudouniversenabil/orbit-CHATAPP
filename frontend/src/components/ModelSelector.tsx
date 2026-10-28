import { Cpu } from "lucide-react";
import type { ModelInfo } from "../services/api";

interface Props {
  models: ModelInfo[];
  onSelect: (providerId: string) => void;
}

export function ModelSelector({ models, onSelect }: Props) {
  const active = models.find((model) => model.active)?.id ?? "";
  return (
    <label className="model-select">
      <Cpu size={15} aria-hidden="true" />
      <span className="sr-only">AI model</span>
      <select value={active} onChange={(event) => onSelect(event.target.value)} aria-label="Select AI model">
        {models.map((model) => (
          <option key={model.id} value={model.id} disabled={!model.available}>
            {model.name} · {model.model}
            {!model.available ? " (not configured)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
