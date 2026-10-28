import { useEffect, useState } from "react";
import { Activity, CircleHelp, Settings2, Sparkles } from "lucide-react";
import { ChatPanel } from "./components/ChatPanel";
import { CommandList } from "./components/CommandList";
import { ModelSelector } from "./components/ModelSelector";
import { SettingsPanel } from "./components/SettingsPanel";
import { useAssistant } from "./hooks/useAssistant";
import { useVoice, type ListeningMode } from "./hooks/useVoice";
import { api, type CommandInfo, type ModelInfo } from "./services/api";

export default function App() {
  const assistant = useAssistant();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [commands, setCommands] = useState<CommandInfo[]>([]);
  const [health, setHealth] = useState(false);
  const [modelError, setModelError] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [wakeWordEnabled, setWakeWordEnabled] = useState(false);
  const [wakeWord, setWakeWord] = useState("hey assistant");
  const [mode, setMode] = useState<ListeningMode>("push-to-talk");
  const [ttsVoice, setTtsVoice] = useState("");
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const voice = useVoice(assistant.sendAudio, mode);

  useEffect(() => {
    void Promise.all([api.models(), api.commands(), api.health()])
      .then(([availableModels, availableCommands]) => {
        setModels(availableModels);
        setCommands(availableCommands);
        setHealth(true);
      })
      .catch(() => setHealth(false));
    const loadVoices = () => setVoices(window.speechSynthesis?.getVoices() ?? []);
    loadVoices();
    window.speechSynthesis?.addEventListener("voiceschanged", loadVoices);
    return () => window.speechSynthesis?.removeEventListener("voiceschanged", loadVoices);
  }, []);

  useEffect(() => {
    assistant.updateVoicePreferences({ wakeWordEnabled, wakeWord });
  }, [assistant.updateVoicePreferences, wakeWord, wakeWordEnabled]);

  useEffect(() => {
    const last = assistant.messages[assistant.messages.length - 1];
    if (!voiceEnabled || assistant.streaming || last?.role !== "assistant" || !last.content) return;
    window.speechSynthesis?.cancel();
    const utterance = new SpeechSynthesisUtterance(last.content);
    const selected = voices.find((item) => item.voiceURI === ttsVoice);
    if (selected) utterance.voice = selected;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis?.speak(utterance);
  }, [assistant.messages, assistant.streaming, ttsVoice, voiceEnabled, voices]);

  const selectModel = async (providerId: string) => {
    try {
      await api.selectModel(providerId);
      setModels((current) => current.map((model) => ({ ...model, active: model.id === providerId })));
      setModelError("");
    } catch (error) {
      setModelError(error instanceof Error ? error.message : "Could not select that model.");
    }
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Desktop Assistant home">
          <span className="brand-mark"><Sparkles size={17} /></span>
          <span>orbit<span className="brand-muted">.assistant</span></span>
        </a>
        <div className="topbar-actions">
          <div className={`connection ${health && assistant.connected ? "online" : ""}`}>
            <Activity size={14} />
            <span>{health && assistant.connected ? "Connected" : "Offline"}</span>
          </div>
          <ModelSelector models={models} onSelect={(providerId) => void selectModel(providerId)} />
          <button className="icon-button" onClick={() => setSettingsOpen((value) => !value)} aria-label="Open settings" aria-pressed={settingsOpen}>
            <Settings2 size={18} />
          </button>
          <a className="icon-button help-link" href="https://github.com/" target="_blank" rel="noreferrer" aria-label="Help"><CircleHelp size={18} /></a>
        </div>
      </header>
      <div className="workspace">
        <ChatPanel
          messages={assistant.messages}
          connected={assistant.connected}
          streaming={assistant.streaming}
          speaking={speaking}
          recording={voice.recording}
          voiceEnabled={voiceEnabled}
          error={modelError || assistant.error}
          voiceError={voice.error}
          onSend={assistant.sendText}
          onMic={voice.toggle}
        />
        <SettingsPanel
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          voiceEnabled={voiceEnabled}
          setVoiceEnabled={setVoiceEnabled}
          wakeWordEnabled={wakeWordEnabled}
          setWakeWordEnabled={setWakeWordEnabled}
          wakeWord={wakeWord}
          setWakeWord={setWakeWord}
          mode={mode}
          setMode={setMode}
          ttsVoice={ttsVoice}
          setTtsVoice={setTtsVoice}
          voices={voices}
        />
      </div>
      <CommandList commands={commands} />
    </div>
  );
}