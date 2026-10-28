import { Settings2, Volume2, X } from "lucide-react";
import type { ListeningMode } from "../hooks/useVoice";

interface Props {
  open: boolean;
  onClose: () => void;
  voiceEnabled: boolean;
  setVoiceEnabled: (value: boolean) => void;
  wakeWordEnabled: boolean;
  setWakeWordEnabled: (value: boolean) => void;
  wakeWord: string;
  setWakeWord: (value: string) => void;
  mode: ListeningMode;
  setMode: (value: ListeningMode) => void;
  ttsVoice: string;
  setTtsVoice: (value: string) => void;
  voices: SpeechSynthesisVoice[];
}

export function SettingsPanel(props: Props) {
  if (!props.open) return null;
  return (
    <aside className="settings-panel" aria-label="Assistant settings">
      <div className="panel-title">
        <div><Settings2 size={17} /> <h2>Settings</h2></div>
        <button className="icon-button" onClick={props.onClose} aria-label="Close settings"><X size={17} /></button>
      </div>
      <label className="setting-row">
        <span><Volume2 size={16} /> Voice responses</span>
        <input type="checkbox" checked={props.voiceEnabled} onChange={(event) => props.setVoiceEnabled(event.target.checked)} />
      </label>
      <label className="setting-field">
        <span>Listening mode</span>
        <select value={props.mode} onChange={(event) => props.setMode(event.target.value as ListeningMode)}>
          <option value="push-to-talk">Push to talk</option>
          <option value="continuous">Continuous (6-second segments)</option>
        </select>
      </label>
      <label className="setting-row">
        <span>Require wake phrase</span>
        <input type="checkbox" checked={props.wakeWordEnabled} onChange={(event) => props.setWakeWordEnabled(event.target.checked)} />
      </label>
      <label className="setting-field">
        <span>Wake phrase</span>
        <input value={props.wakeWord} onChange={(event) => props.setWakeWord(event.target.value)} disabled={!props.wakeWordEnabled} />
      </label>
      <label className="setting-field">
        <span>Speech voice</span>
        <select value={props.ttsVoice} onChange={(event) => props.setTtsVoice(event.target.value)} disabled={!props.voices.length}>
          <option value="">System default</option>
          {props.voices.map((voice) => <option key={voice.voiceURI} value={voice.voiceURI}>{voice.name} ({voice.lang})</option>)}
        </select>
      </label>
      <p className="settings-note">Voice playback uses your browser’s speech engine. Speech recognition runs on the backend.</p>
    </aside>
  );
}
