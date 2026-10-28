# Linux Desktop Assistant

A local-first, voice-capable desktop assistant for Linux. The Python/FastAPI backend routes known system commands before using a selectable LLM provider. The React/Vite UI provides chat streaming, microphone capture, model selection, settings, and a live command catalog.

The backend binds to `127.0.0.1` by default. Keep it on loopback unless you add authentication and deliberately configure network access. System actions are built from fixed executable names and arguments; LLM responses are never interpreted as shell commands.

## Project layout

```text
backend/app/
  api/          REST and WebSocket routes
  core/         settings, logging, and Pydantic schemas
  providers/    Ollama, OpenAI-compatible, Anthropic, Gemini
  voice/        faster-whisper/cloud STT, pyttsx3 TTS, wake phrase
  commands/     plugin discovery and one file per command skill
backend/tests/  command router and provider tests
frontend/src/
  components/   chat, microphone, settings, model picker, commands
  hooks/        WebSocket conversation and microphone state
  services/     REST client
```

## Arch Linux setup

The project supports Python 3.11 or later and Node.js. Install the system packages you plan to use:

```bash
sudo pacman -S python python-pip nodejs npm portaudio ffmpeg xdg-utils \
  playerctl brightnessctl procps-ng libnotify pipewire pipewire-pulse wireplumber espeak-ng
```

Optional X11 helpers:

```bash
sudo pacman -S wmctrl xdotool
```

`pactl` is provided by `pipewire-pulse` on a PipeWire desktop. `notify-send` comes from `libnotify`. App launch, media control, and brightness changes require the matching desktop utilities; unavailable tools produce an explicit message. `wmctrl` and `xdotool` are not currently required by the built-in skills.

Create and activate a virtual environment, then install the backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install optional offline speech packages when voice recognition and host-side speech output are wanted:

```bash
pip install -r requirements-voice.txt
```

Copy `.env.example` to `.env` and set any cloud API keys. Never commit `.env`. For offline LLM use, install Ollama separately, start its service, and pull the configured model, for example:

```bash
ollama pull llama3.2
```

Install the frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

## Run

Start both development services from the project root:

```bash
./run.sh
```

Or run them separately:

```bash
# Terminal 1, from project root
source .venv/bin/activate
uvicorn backend.app.main:app --reload

# Terminal 2
cd frontend
npm run dev
```

Open <http://127.0.0.1:5173>. The API is at <http://127.0.0.1:8000>; interactive docs are at `/docs`. For a custom manual Uvicorn bind, pass `--host` and `--port`; `run.sh` reads these from `.env` and allows exported `HOST`/`PORT` values to override them.

Run backend tests:

```bash
source .venv/bin/activate
pytest
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `HOST`, `PORT` | `127.0.0.1`, `8000` | Backend bind address and port |
| `CORS_ORIGINS` | Local Vite origins | Comma-separated browser origins |
| `ACTIVE_PROVIDER` | `ollama` | `ollama`, `openai`, `anthropic`, or `gemini` |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | `http://localhost:11434`, `llama3.2` | Local Ollama endpoint and model |
| `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` | OpenAI endpoint, empty key, `gpt-4o-mini` | OpenAI or compatible API |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Empty key, `claude-3-5-haiku-latest` | Claude Messages API |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Empty key, `gemini-2.0-flash` | Gemini API |
| `STT_PROVIDER` | `offline` | `offline` (faster-whisper) or `cloud` (OpenAI transcription) |
| `STT_MODEL`, `STT_LANGUAGE` | `small`, empty | Whisper model and optional language code; empty enables multilingual detection |
| `OPENAI_TRANSCRIPTION_MODEL` | `whisper-1` | Cloud transcription model |
| `WAKE_WORD`, `WAKE_WORD_ENABLED` | `hey assistant`, `false` | Phrase checked against transcribed speech |
| `TTS_ENABLED`, `TTS_VOICE` | `false`, empty | Optional backend pyttsx3 speech output/voice match |

The React settings use the browser's speech synthesis voices for spoken responses. Speech recognition is sent to the backend. The WebSocket accepts JSON text messages and base64-encoded audio segments.

## Voice, English, and Bangla

The browser microphone captures WebM audio and sends it to `/ws/voice`. Offline transcription uses `faster-whisper` on the CPU; its multilingual models can recognize English and Bangla. Downloaded model files are cached by faster-whisper. Set `STT_LANGUAGE=en` or `STT_LANGUAGE=bn` to force a language, or leave it empty for automatic detection. The optional cloud transcription provider requires `OPENAI_API_KEY` and sends audio to the OpenAI transcription API.

Push-to-talk records until the mic button is pressed again. Continuous mode sends six-second recording segments. Wake phrase detection is applied to the recognized transcript (it is not a separate always-on acoustic keyword engine); enable it in the settings panel. Browser microphone access generally requires localhost or HTTPS.

## System command safety and desktop support

The command router checks installed plugins before sending a message to the LLM. App launching uses a built-in whitelist; unknown app names are not executed. Website opening is passed as one URL argument to `xdg-open`. Close-app requests only target allowlisted process names with `pkill -x`. Commands do not use `shell=True`, and model-generated content is never executed as a command.

App launching through `xdg-open`, PipeWire/PulseAudio volume via `pactl`, `playerctl`, and `brightnessctl` are intended for both Wayland and X11 where the session exposes those tools. Closing apps via process names is session-independent but can close all matching app processes. Desktop environment behavior varies. Some Wayland compositors restrict global window management and brightness control; hardware permissions, polkit rules, or compositor-specific tools may be needed. Battery status is unavailable on systems without a battery sensor. Timers run in the backend process and notify through `notify-send` when installed; they do not survive a backend restart.

## Add a model provider in 5 minutes

1. Add `backend/app/providers/my_provider.py`; implement `BaseLLMProvider.generate()` and `BaseLLMProvider.stream()` with `httpx.AsyncClient`.
2. Export `get_provider_registration()` from that same module. Return a `ProviderRegistration` with a unique id, label, model getter, availability getter, and factory. The registry imports provider modules automatically.
3. Read configuration from `settings.custom_provider_config.get("my_provider", {})`. Put endpoint, model, and API-key values in `.env` as JSON under `CUSTOM_PROVIDER_CONFIG`, for example `CUSTOM_PROVIDER_CONFIG={"my_provider":{"base_url":"https://api.example.test","model":"small","api_key":"..."}}`. Do not put credentials in the source code.
4. Add a small provider parsing/selection test and document its configuration.
5. Restart the backend; `GET /models` and the React model selector discover the provider automatically. No edit to the registry is needed.

Do not put secrets in frontend code or provider source files. Provider errors are logged and surfaced as API/WebSocket errors.

## Troubleshooting

- **Microphone permission denied:** allow microphone access for the browser, verify the input in the desktop audio settings, and ensure the page is opened at `localhost`/`127.0.0.1` or HTTPS.
- **PipeWire/PulseAudio volume errors:** install and start `pipewire`, `pipewire-pulse`, and `wireplumber`; verify `pactl info` works in the same logged-in user session. Do not run the desktop audio stack as root.
- **No sound from browser TTS:** enable Voice responses in Settings and check the browser's speech synthesis voices/output device. For backend TTS, install `pyttsx3` and `espeak-ng`, then set `TTS_ENABLED=true`.
- **Offline STT package/model trouble:** install `requirements-voice.txt`, verify `ffmpeg` is installed, and allow time/network for the first model download. `small` is a multilingual model; lower resource devices can set `STT_MODEL=base`.
- **Ollama connection refused / “All connection attempts failed”:** the Ollama server is not running or `OLLAMA_BASE_URL` points to the wrong host/port. Start it with `sudo systemctl start ollama` (or `ollama serve`), check `curl http://localhost:11434/api/tags`, and verify the configured model with `ollama list`; pull it if needed, e.g. `ollama pull llama3.2`.
- **No model response:** check `GET /health`; Cloud providers only become selectable when their API key is configured.
- **App/media control unavailable:** install the utility named in the error (`xdg-utils`, `playerctl`, `brightnessctl`, `procps-ng`, `libnotify`) and confirm the desktop session exposes its control interface.
- **Port already in use:** set `PORT` for the backend. Vite uses port 5173 and is configured to fail rather than silently choose another port.
