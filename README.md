# YouTube AI Studio — Automated Video Content Production

An AI system that produces content for a YouTube channel end to end. The channel's niche is the daily life of a shepherd in a village in Lachin, Azerbaijan: rural life and recipes cooked at camp.

## How it works
- **Phase 1 (done)** — generates topics and scripts with LLMs; every script is approved in Telegram before production
- **Phase 2 (current)** — turns approved scripts into full videos: AI visuals (fal.ai or Pollinations with a Ken Burns effect), Azerbaijani voice-over (edge-tts) and assembly with ffmpeg, followed by a second approval in Telegram
- **Next** — sound effects and automatic YouTube upload

## Key features
- Multi-provider LLM router (Gemini, Groq, local Ollama) with automatic fallback
- Quality checks on generated scripts, with automatic retries
- Daily scheduled generation
- Human-in-the-loop approval through a Telegram bot

## Tech stack
Python · LLMs (Gemini / Groq / Ollama) · fal.ai · edge-tts · ffmpeg · SQLite · Telegram Bot API

## Getting started
See the setup steps below: create a virtual environment, install `requirements.txt`, fill in `.env` and run `python main.py`.

---

## Azərbaycan dilində

# youtube-ai-studio

AI ilə YouTube kanalı üçün avtomatik məzmun istehsalı sistemi. Kanal nişi: Laçının
Oğuldərə kəndində bir çobanın gündəlik yaşam tərzi, kənd həyatı və kamp şəraitində
bişirilən yeməklərin resept prosesi.

**Faza 1 (tamamlandı):** mövzu/ssenari generasiyası + Telegram təsdiq axını.
Dizayn: [docs/superpowers/specs/2026-07-11-phase1-script-generator-design.md](docs/superpowers/specs/2026-07-11-phase1-script-generator-design.md)

**Faza 2 (bu repo-nun hazırkı vəziyyəti):** təsdiqlənmiş ssenariləri fal.ai (video) +
edge-tts (səsləndirmə) + ffmpeg (birləşdirmə) ilə tam videoya çevirən və Telegram-da
ikinci dəfə təsdiq alan agent. Səs effektləri və YouTube upload sonrakı fazalarda
əlavə olunacaq. Dizayn: [docs/superpowers/specs/2026-07-12-phase2-video-generation-design.md](docs/superpowers/specs/2026-07-12-phase2-video-generation-design.md)

## Quraşdırma

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

`.env` faylını doldurun:

| Dəyişən | Təsvir |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather ilə yaradılan bot tokeni |
| `TELEGRAM_CHAT_ID` | Gündəlik avtomatik mesajların göndəriləcəyi chat ID (öz istifadəçi ID-niz və ya kanal) |
| `GEMINI_API_KEY` / `GROQ_API_KEY` | LLM provayder açarları (boş buraxsanız o provayder router-də keçilir) |
| `OLLAMA_HOST` | Lokal Ollama server ünvanı (defolt `http://localhost:11434`) |
| `DAILY_GENERATION_HOUR` / `DAILY_VARIANTS_COUNT` | Gündəlik avtomatik generasiya saatı və say |
| `DB_PATH` | SQLite fayl yolu (defolt `data/youtube_studio.db`) |
| `VIDEO_PROVIDER` | Video mənbəyi: `pollinations` (pulsuz, açar tələb etmir — AI şəkil + Ken Burns hərəkət effekti) və ya `fal` (fal.ai, hesab balansı tələb edir — tam text-to-video) |
| `FAL_API_KEY` | fal.ai API açarı (yalnız `VIDEO_PROVIDER=fal` olduqda lazımdır) |
| `TTS_VOICE` | edge-tts səs adı (defolt `az-AZ-BanuNeural`, qadın; alternativ: `az-AZ-BabekNeural`, kişi) |
| `VIDEO_WORKER_INTERVAL_MINUTES` | Video worker-in nə qədər tez-tez təsdiqlənmiş ssenariləri yoxladığı (defolt 2) |
| `VIDEOS_DIR` | Hazır video fayllarının saxlandığı qovluq (defolt `data/videos`) |

Qeyd: `GEMINI_API_KEY`/`GROQ_API_KEY` sistem mühit dəyişəni kimi də qura bilərsiniz —
`.env`-dən üstün tutulur (`python-dotenv` mövcud mühit dəyişənlərini əvəz etmir).

### Telegram bot token və chat ID necə alınır

1. Telegram-da [@BotFather](https://t.me/BotFather)-a yazın, `/newbot` əmri ilə yeni bot yaradın, verilən tokeni `TELEGRAM_BOT_TOKEN`-ə qoyun.
2. Öz chat ID-nizi almaq üçün botunuza bir mesaj göndərin, sonra brauzerdə
   `https://api.telegram.org/bot<TOKEN>/getUpdates` ünvanına baxın — `"chat":{"id": ...}` sahəsindəki rəqəm sizin chat ID-nizdir.

### fal.ai API açarı necə alınır

1. [fal.ai](https://fal.ai) saytında qeydiyyatdan keçin (email və ya GitHub ilə).
2. Dashboard → Keys bölməsinə keçib "Create new key" ilə API açarı yaradın, `FAL_API_KEY`-ə qoyun.

## İşə salma

```powershell
.venv\Scripts\python main.py
```

Bot uğurla başlayanda Telegram-da `/start` və `/generate` əmrlərini sınaya bilərsiniz.
Gündəlik avtomatik generasiya `DAILY_GENERATION_HOUR`-da işə düşür (proses işlək qalmalıdır).
Ssenari ✅ ilə təsdiqlənəndən sonra video worker (hər `VIDEO_WORKER_INTERVAL_MINUTES`
dəqiqədə bir) onu avtomatik götürüb videoya çevirir və Telegram-a ✅/❌/🔄 düymələri ilə
ikinci təsdiq üçün göndərir.

## Test

```powershell
.venv\Scripts\python -m pytest -q
```

## Layihə strukturu

```
config/
  settings.py     — .env-dən konfiqurasiya yükləmə
  prompts.py      — niş-spesifik prompt şablonları
core/
  db.py           — SQLite: content_ideas cədvəli, CRUD
  script_generator.py — prompt qurma + LLM çağırma + JSON parse
  tts.py          — edge-tts wrapper (səsləndirmə)
  video_pipeline.py — TTS + klip + ffmpeg birləşdirmə orkestrasiyası
  llm/
    base.py, gemini_provider.py, groq_provider.py, ollama_provider.py, router.py
  video/
    base.py — VideoProvider interfeysi
    pollinations_provider.py — pulsuz AI şəkil (Pollinations) + ffmpeg Ken Burns
    fal_provider.py — fal.ai tam text-to-video (balans tələb edir)
    factory.py — VIDEO_PROVIDER-ə görə provayder seçimi
bot/
  telegram_bot.py — aiogram: /start, /generate, ssenari+video təsdiq düymələri
  scheduler.py    — gündəlik avtomatik ssenari generasiyası
  video_worker.py — arxa planda təsdiqlənmiş ssenariləri videoya çevirir
main.py           — entrypoint
```

## Məlum məhdudiyyətlər

- LLM provayderlərinin pulsuz kvotaları məhduddur (Groq: gündəlik token limiti,
  Gemini: Google AI Studio-da free-tier tənzimləməsindən asılı). Router avtomatik
  Gemini → Groq → Ollama ardıcıllığı ilə fallback edir, amma hər üçü eyni gündə
  tükənərsə generasiya mümkün olmur (`AllProvidersFailedError`).
- Defolt video provayderi `pollinations` tam pulsuzdur (açar/qeydiyyat/ödəniş tələb etmir):
  hər səhnə üçün AI şəkil çəkir və ffmpeg Ken Burns (yavaş zoom) effekti ilə hərəkətli klipə
  çevirir. Alternativ `fal` (tam text-to-video) hesab balansı tələb edir.
- Səs effektləri (fon/təbiət səsləri) və YouTube upload hələ implementasiya olunmayıb.
