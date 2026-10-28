import { ArrowUp, AudioLines, Bot, Mic, UserRound } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import type { Message } from "../hooks/useAssistant";

interface Props {
  messages: Message[];
  connected: boolean;
  streaming: boolean;
  speaking: boolean;
  recording: boolean;
  voiceEnabled: boolean;
  error: string;
  voiceError: string;
  onSend: (text: string) => void;
  onMic: () => void;
}

export function ChatPanel(props: Props) {
  const [text, setText] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [props.messages]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!text.trim() || props.streaming) return;
    props.onSend(text);
    setText("");
  };

  return (
    <main className="chat-panel">
      <div className="messages">
        {props.messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-orb"><Bot size={28} /></div>
            <p className="eyebrow">YOUR LOCAL DESKTOP COMPANION</p>
            <h1>How can I help?</h1>
            <p>Ask a question, or tell me to open an app, manage media, check system status, save a note, or set a timer.</p>
            <div className="suggestions">
              {["What time is it?", "System status", "Open Firefox"].map((item) => (
                <button key={item} onClick={() => props.onSend(item)}>{item}</button>
              ))}
            </div>
          </div>
        ) : props.messages.map((message, index) => (
          <article className={`message ${message.role}`} key={`${index}-${message.role}`}>
            <div className="avatar">{message.role === "user" ? <UserRound size={16} /> : <Bot size={16} />}</div>
            <div className="message-content">
              <div className="message-label">{message.role === "user" ? "You" : "Assistant"}</div>
              <p>{message.content || (props.streaming && index === props.messages.length - 1 ? <span className="typing-dots">Thinking<span>.</span><span>.</span><span>.</span></span> : "")}</p>
            </div>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>
      {(props.error || props.voiceError) && <div className="error-banner" role="alert">{props.error || props.voiceError}</div>}
      <form className={`composer ${props.speaking ? "speaking" : ""}`} onSubmit={submit}>
        <button
          type="button"
          className={`mic-button ${props.recording ? "recording" : ""}`}
          onClick={props.onMic}
          aria-label={props.recording ? "Stop recording" : "Start voice input"}
          title={props.recording ? "Stop recording" : "Start voice input"}
        >
          {props.recording ? <AudioLines size={19} className="pulse" /> : <Mic size={19} />}
        </button>
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={props.connected ? "Message your assistant..." : "Connecting to backend..."}
          aria-label="Message"
          disabled={!props.connected || props.streaming}
        />
        <button className="send-button" type="submit" disabled={!text.trim() || props.streaming || !props.connected} aria-label="Send message">
          <ArrowUp size={18} />
        </button>
      </form>
      <p className="composer-hint">{props.recording ? "Listening · click the mic to stop" : props.speaking ? "Speaking..." : "Enter to send · microphone for voice input"}</p>
      {!props.voiceEnabled && <span className="sr-only">Voice responses are disabled</span>}
    </main>
  );
}
