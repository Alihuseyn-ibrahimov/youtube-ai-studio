# Faza 1: Mövzu/Ssenari Generatoru + Telegram Təsdiq Axını

**Tarix:** 2026-07-11
**Status:** Təsdiqlənib (dizayn səviyyəsində)

## Məqsəd

AI ilə YouTube kanalı üçün avtomatik məzmun istehsalı sisteminin ilk mərhələsi. Bu faza, mövzu/ssenari mətnini generasiya edən və Telegram üzərindən istifadəçi təsdiqi alan alt-sistemi əhatə edir. Sonrakı fazalarda (video generasiyası, səs effektləri, YouTube upload) bu fazanın çıxışını (təsdiqlənmiş ssenarilər) giriş kimi istifadə edəcək.

## Kontekst və niş

- **Kanal mövzusu:** Kənd həyatı və yemək videoları — Laçının Oğuldərə kəndində bir çobanın gündəlik yaşam tərzi, kamp şəraitində bişirilən yeməklər, resept prosesləri.
- **Dil:** Azərbaycan dili, AI səsləndirmə (TTS) üçün nəzərdə tutulmuş ssenari mətni.
- **Video formatları:** Həm YouTube Shorts (≤60 saniyə), həm də uzun format (5-10 dəqiqə). Format content_ideas cədvəlində saxlanılır və ssenari strukturuna (səhnə sayı, uzunluq) təsir edir.
- **Video generasiyası (gələcək faza):** Tam AI text-to-video (Runway/Kling/Luma/Veo). Hazırda pulsuz/aşağı-limitli seçimlərlə davam ediləcək — bu, faza 2-də ayrıca qərarlaşdırılacaq.

## Əhatə (Scope) — Yalnız bu faza

Daxildir:
- Niş-spesifik prompt şablonu ilə mövzu+ssenari generasiyası
- Çoxlu LLM provayder dəstəyi (Gemini əsas, Groq/Ollama fallback)
- SQLite-da ssenarilərin saxlanması (status: pending/approved/rejected)
- Telegram bot: gündəlik avtomatik təkliflər + `/generate` əmri ilə tələb üzrə generasiya
- İnline düymələrlə təsdiq/rədd/yenidən-generasiya axını

Daxil deyil (gələcək fazalar):
- Video generasiyası
- Səs effektləri/musiqi
- YouTube-a yükləmə
- Monetizasiya izləmə

## Arxitektura

Tək prosesli Python tətbiqi, long-polling Telegram bot (aiogram) + APScheduler (gündəlik cron) + SQLite. İctimai HTTPS/webhook tələb olunmur, lokal və ya kiçik serverdə birbaşa `python main.py` ilə işə düşür.

**Alternativlər və niyə rədd edildi:**
- İki ayrı skript (cron generator + ayrıca listener): daha modul, amma hazırkı miqyasda əlavə əməliyyat mürəkkəbliyi yaradır, faydası yoxdur.
- FastAPI + Telegram webhook: production-grade, amma ictimai domen/HTTPS tələb edir — ilkin faza üçün artıq mürəkkəblikdir. Gələcəkdə serverə deploy edilərkən yenidən nəzərdən keçirilə bilər.

## Layihə strukturu

```
youtube-ai-studio/
  .env.example
  requirements.txt
  main.py                    — bot + scheduler-i başladır
  config/
    settings.py               — .env-dən API açarları/parametrləri yükləyir
    prompts.py                — niş-spesifik prompt şablonları (kənd/çoban/yemək)
  core/
    db.py                     — SQLite: content_ideas cədvəli, CRUD funksiyaları
    llm/
      base.py                 — LLMProvider interfeysi (abstract)
      gemini_provider.py
      groq_provider.py
      ollama_provider.py
      router.py                — fallback zənciri: Gemini → Groq → Ollama
    script_generator.py        — prompt qurur, LLM çağırır, nəticəni parse edir (başlıq + ssenari + səhnə breakdown)
  bot/
    telegram_bot.py            — aiogram: /start, /generate əmrləri, inline keyboard handler-ləri
    scheduler.py                — APScheduler: gündəlik avtomatik generasiya job-u
  tests/
    test_script_generator.py
    test_db.py
```

## Data modeli

`content_ideas` cədvəli (SQLite):

| Sütun | Tip | Təsvir |
|---|---|---|
| id | INTEGER PK | |
| created_at | TEXT (ISO) | |
| format | TEXT | `shorts` \| `long` |
| title | TEXT | Video başlığı |
| script_text | TEXT | Tam ssenari mətni (Azərbaycan dilində, TTS üçün) |
| scenes_json | TEXT (JSON) | Səhnə-səhnə breakdown: `[{"description": "...", "duration_sec": ...}, ...]` — faza 2 (video agenti) üçün giriş |
| status | TEXT | `pending` \| `approved` \| `rejected` |
| telegram_message_id | INTEGER | Düymə callback-lərini mesaja bağlamaq üçün |

## Data axını

1. Scheduler (gündə 1 dəfə, konfiqurasiya oluna bilən saatda) və ya `/generate` əmri işə düşür.
2. `script_generator.generate()` niş konteksini (kənd/çoban/yemək) və format-ı (shorts/long) prompt şablonuna qoyub LLM router-ə göndərir.
3. Router LLM provayderlərini ardıcıl sınayır (Gemini → Groq → Ollama), ilk uğurlu cavabı qaytarır.
4. Nəticə parse olunur: başlıq, tam ssenari, səhnə breakdown.
5. SQLite-a `pending` statusu ilə yazılır.
6. Telegram-a başlıq + ssenari mətni + ✅ Təsdiqlə / ❌ Rədd et / 🔄 Yenidən düymələri ilə göndərilir, `telegram_message_id` DB-də saxlanılır.
7. İstifadəçi düyməyə basdıqda:
   - ✅ Təsdiqlə → status `approved` olur (faza 2-nin oxuyacağı queue-ya düşür)
   - ❌ Rədd et → status `rejected` olur
   - 🔄 Yenidən → yeni generasiya işə düşür, əvvəlki sətir `rejected` işarələnir

## Xəta idarəetməsi

- LLM provayderlərindən biri uğursuz olarsa (timeout, rate limit, API xətası) → router avtomatik növbəti provayderə keçir. Hamısı uğursuz olarsa, Telegram-a xəbərdarlıq mesajı göndərilir ("Bu gün mövzu generasiya edilə bilmədi, LLM xətası: ...").
- Telegram mesaj göndərilməsi uğursuz olarsa → log yazılır, exponential backoff ilə 1 dəfə retry edilir.
- Gündəlik job xəta atsa belə, prosesin özü dayanmır (scheduler job-u izolə olunmuş exception handler-lə işə salır).

## Test strategiyası

- `core/script_generator.py` və `core/db.py` Telegram SDK-dan asılı olmadan unit test oluna bilər (LLM cavabları mock edilərək).
- LLM router-in fallback məntiqi: provayderlərin bir-bir uğursuz olma ssenarisi test edilir.
- Manual/əl ilə test: real Telegram bot token ilə `/generate` əmri işə salınıb tam axının (generasiya → mesaj → düymə → status yeniləmə) işlədiyi yoxlanılacaq.

## Konfiqurasiya (.env)

```
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
GEMINI_API_KEY=
GROQ_API_KEY=
OLLAMA_HOST=http://localhost:11434
DAILY_GENERATION_HOUR=8
DAILY_VARIANTS_COUNT=2
```

## Açıq qalan suallar (gələcək fazalarda həll ediləcək)

- Video generasiya servisi seçimi və pulsuz limitlərin real məhsuldarlığa təsiri (Faza 2).
- Səs effektləri/musiqi mənbəyi (Faza 3).
- YouTube API vasitəsilə avtomatik yükləmə və monetizasiya tələbləri (Faza 4).
