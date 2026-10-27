# Task Plan: youtube-ai-studio — Faza 1 + Faza 2

## Goal
**Faza 1 (tamamlandı):** Laçının Oğuldərə kəndi/çoban həyatı/yemək nişi üçün AI ilə mövzu+ssenari generasiya edən və Telegram üzərindən təsdiq axını olan Python layihəsini, təsdiqlənmiş spesifikasiyaya (`docs/superpowers/specs/2026-07-11-phase1-script-generator-design.md`) uyğun tikmək.

**Faza 2 (aktiv):** Faza 1-də təsdiqlənmiş ssenariləri fal.ai (video) + edge-tts (səsləndirmə) + ffmpeg (birləşdirmə) ilə tam videoya çevirən və Telegram-da ikinci dəfə təsdiq alan agentini, təsdiqlənmiş spesifikasiyaya (`docs/superpowers/specs/2026-07-12-phase2-video-generation-design.md`) uyğun tikmək.

## Current Phase
Faza 1+2 TAM TAMAMLANDI, produksiyada işləyir (pulsuz Pollinations + kinematik prompt + 4 hərəkət preset-i). Qalan yol planlaşdırılıb (aşağıda Faza 3-5) — istifadəçi prioriteti seçəcək.

## Qalan Yol Xəritəsi (2026-07-12 planlaşdırıldı)

### Faza 3: Audio atmosfer (fon musiqisi + təbiət səsləri)
Məqsəd: videolara "sakit kənd həyatı" atmosferi qatmaq — narrasiyanın altına yumşaq fon musiqisi/təbiət səsləri.
- CC0/royalty-free audio kitabxanası (Pixabay Audio / Freesound-dan seçilmiş 10-15 fayl) layihəyə lokal əlavə olunur (data/audio/), kateqoriyalı: səhər/ocaq/dağ küləyi/axşam
- LLM ssenari generasiyasında hər ideyaya "mood" sahəsi əlavə olunur → uyğun ambient fayl seçilir
- ffmpeg miks: narration əsas, ambient -18dB civarı + sidechain ducking (narrasiya danışanda fon azalır)
- video_pipeline-a inteqrasiya, testlər, VPS deploy + canlı test
Təxmini həcm: kiçik-orta. Tam pulsuz.

### Faza 4: YouTube avtomatik yükləmə
Məqsəd: video ✅ təsdiqlənəndə avtomatik YouTube kanalına yüklənsin — monetizasiya yolunun son texniki addımı.
- Google Cloud layihəsində YouTube Data API v3 + OAuth (bir dəfəlik istifadəçi avtorizasiyası, refresh token VPS .env-də) — QEYD: TV Monitorinq layihəsində artıq işlək YouTube OAuth nümunəmiz var (n8n), oradakı təcrübə istifadə olunacaq
- Başlıq/təsvir/teqlər/hashtag-lər LLM ilə avtomatik generasiya (Azərbaycanca + SEO)
- İlk mərhələdə "private" yüklənir → Telegram-a link gəlir → istəsə istifadəçi public edir; sonra istəyə görə tam avto-public
- DB: youtube_video_id, upload_status sütunları; upload worker (video_status='approved' olanları götürür)
- Kvota qeydi: YouTube API upload=1600 kvota vahidi, gündəlik pulsuz 10000 → gündə ~6 upload mümkün, bizə kifayətdir
Təxmini həcm: orta. Tam pulsuz.

### Faza 5: Tam avtonom rejim + monetizasiya izləmə
Məqsəd: insan müdaxiləsini minimuma endirmək və qazancı izləmək.
- "Avto-rejim" açarı: gündə N video tam avtomatik (ssenari→video→upload), Telegram yalnız məlumatlandırır (təsdiq tələb etmir)
- Həftəlik Telegram hesabatı: neçə video, baxış/abunəçi statistikası (YouTube Analytics API)
- Shorts→uzun format keçid strategiyası (kanal böyüdükcə)
- Monetizasiya şərtlərinin izlənməsi (1000 abunəçi + 4000 saat / 10M Shorts baxışı)
Təxmini həcm: orta. Faza 4-dən sonra mənalıdır.

**Tövsiyə olunan sıra: Faza 3 → Faza 4 → Faza 5** (əvvəl məhsul keyfiyyəti, sonra nəşr avtomatikası, sonra miqyas). Alternativ: Faza 4-ü qabağa çəkmək (tez YouTube-da olmaq üçün), Faza 3-ü sonra.

### Phase 14: PollinationsProvider — tam pulsuz video
- [x] core/video/pollinations_provider.py — Pollinations-dan AI şəkil (açar yoxdur) + ffmpeg zoompan Ken Burns effekti → klip bytes; aspect_ratio→çözünürlük mapping (9:16→1080x1920 və s.), duration sərbəst (min 3s), asyncio.to_thread ilə ffmpeg
- [x] config/settings.py: VIDEO_PROVIDER sahəsi (defolt "pollinations"); core/video/factory.py: build_video_provider (pollinations/fal seçimi); main.py factory istifadə edir
- [x] tests/test_pollinations_provider.py (5 test) + tests/test_video_factory.py (4 test); mövcud Settings test helper-ləri yeniləndi
- [x] .env.example, README yeniləndi
- [x] Real uc-uca test (lokal): Pollinations şəkil çəkildi + Ken Burns → 711KB h264 1080x1920 8s klip
- [x] Tam test dəsti: 61/61 keçdi
- [x] VPS deploy (kod sync + VIDEO_PROVIDER=pollinations .env-ə + idea 1 reset + systemctl restart)
- [x] **CANLI TEST UĞURLU:** worker id=1-i götürdü → 5 səhnə üçün Pollinations AI şəkil + Ken Burns → Azərbaycan TTS mux → data/videos/1.mp4 (2.1MB, h264+aac, 21.2s) → Telegram-a göndərildi (message_id=10). TAMAMİLƏ PULSUZ, açar/ödəniş olmadan
- **Status:** complete — pulsuz video generasiyası canlı işləyir

## Phases

### Phase 1: Layihə skeleti və konfiqurasiya
- [x] Qovluq strukturunu yarat (config/, core/, core/llm/, bot/, tests/)
- [x] requirements.txt (aiogram, apscheduler, python-dotenv, google-generativeai, groq, ollama, pytest)
- [x] .env.example yarat
- [x] config/settings.py — .env yükləmə
- [x] .gitignore (.env, __pycache__, *.db)
- [x] .venv yaradıldı, requirements.txt quraşdırıldı, settings.py doğrulandı
- **Status:** complete

### Phase 2: Verilənlər bazası qatı
- [x] core/db.py — SQLite schema (content_ideas cədvəli), init_db()
- [x] CRUD funksiyaları: create_idea, update_status, set_telegram_message_id, get_by_id, get_by_telegram_message_id, get_approved
- [x] tests/test_db.py (5 test, hamısı keçdi)
- **Status:** complete

### Phase 3: LLM provayder qatı
- [x] core/llm/base.py — LLMProvider abstract interfeys (generate(prompt) -> str)
- [x] core/llm/gemini_provider.py
- [x] core/llm/groq_provider.py
- [x] core/llm/ollama_provider.py
- [x] core/llm/router.py — fallback zənciri (Gemini→Groq→Ollama) + build_default_router()
- [x] tests/test_llm_router.py (4 test, hamısı keçdi)
- [x] Real API açarları ilə smoke-test: Groq işləyir, Gemini kvota=0 xətası verir amma fallback düzgün işlədi
- **Status:** complete

### Phase 4: Ssenari generatoru
- [x] config/prompts.py — niş-spesifik prompt şablonu (kənd/çoban/yemək), format-a görə (shorts/long) struktur, JSON cavab tələbi
- [x] core/script_generator.py — prompt qurma, LLM router çağırma, cavabı parse etmə (title/script/scenes), markdown code-fence təmizləmə
- [x] tests/test_script_generator.py (6 test, hamısı keçdi — valid JSON, fenced JSON, invalid JSON, missing field, format validasiyası)
- [x] Real Groq çağırışı ilə doğrulandı: JSON düzgün parse olundu (bax: findings.md — Windows konsol kodlaşdırma və gündəlik kvota qeydləri)
- **Status:** complete

### Phase 5: Telegram bot
- [x] bot/telegram_bot.py — aiogram v3 (3.29.1) Dispatcher qurulumu
- [x] /start əmri
- [x] /generate əmri → script_generator çağırıb DB-yə yazır, mesaj göndərir (✅/❌/🔄 inline keyboard)
- [x] Callback handler-lər: approve/reject/regenerate (regenerate köhnə sətri rejected edir, eyni formatla yenisini generasiya edir)
- [x] tests/test_telegram_bot.py (3 test — keyboard strukturu, uğurlu generasiya, uğursuz generasiya xəbərdarlığı)
- [ ] Real Telegram bot token ilə manual test (Phase 7-də ediləcək, istifadəçidən bot token lazımdır)
- **Status:** complete (kodlaşdırma və unit testlər; manual canlı test Phase 7-yə saxlanılıb)

### Phase 6: Scheduler
- [x] bot/scheduler.py — AsyncIOScheduler, DAILY_GENERATION_HOUR-da DAILY_VARIANTS_COUNT sayda avtomatik generasiya, xəta izolyasiyası (try/except + log)
- [x] telegram_bot.py-dəki generasiya funksiyası public edildi (generate_and_send) ki, scheduler ondan istifadə edə bilsin
- [x] tests/test_scheduler.py (3 test — cron saatı, hər variant üçün çağırış, xəta izolyasiyası)
- [ ] main.py-a inteqrasiya (Phase 7)
- **Status:** complete

### Phase 7: İnteqrasiya, test və çatdırılma
- [x] main.py — bot + scheduler-i başladır, UTF-8 konsol konfiqurasiyası, TELEGRAM_BOT_TOKEN boş olanda aydın RuntimeError
- [x] README.md — quraşdırma, BotFather token/chat ID alma təlimatı, işə salma, test, məlum məhdudiyyətlər
- [x] pytest ilə bütün unit testlərin işləməsi (21/21 keçdi)
- [x] main.py-ın import və "token yoxdur" xəta yolu manual yoxlanıldı
- [x] Bot token .env-ə əlavə olundu; getUpdates ilə əlaqə yoxlanılarkən aşkar edildi ki, bu maşından `api.telegram.org`-a TCP bağlantısı bloklanır (DNS OK, bağlantı timeout) — Google/Groq API-lərinə çıxış isə problemsizdir
- [x] Layihə Hetzner VPS-ə (<SERVER_IP>, /root/youtube-ai-studio/) deploy edildi: tar+scp ilə kod köçürüldü, venv+requirements quraşdırıldı, .env (real tokenlər) təhlükəsiz köçürüldü (heç bir dəyər çap edilmədən)
- [x] **Canlı Telegram testi UĞURLA TAMAMLANDI:** /start işlədi, /generate işlədi (Gemini kvota xətası → Groq fallback uğurla cavab verdi, mesaj Telegram-a çatdı), ✅ Təsdiqlə düyməsi basıldı → DB-də status "approved" oldu (yoxlanıldı)
- [x] docs/superpowers/specs faylına əsasən tələblərin qarşılandığının yoxlanması (əhatə uyğundur)
- **Status:** complete — Faza 1 tam uc-uca canlı doğrulandı

### Phase 8: DB genişlənməsi (video statusu)
- [x] core/db.py: content_ideas cədvəlinə yeni sütunlar — video_status, video_path, video_telegram_message_id, video_error (SCHEMA + PRAGMA table_info yoxlaması ilə ALTER TABLE miqrasiyası, mövcud DB-lər üçün təhlükəsiz)
- [x] Yeni funksiyalar: mark_video_processing, mark_video_ready, mark_video_failed, set_video_telegram_message_id, update_video_status, reset_video_status, get_next_idea_for_video, get_by_video_telegram_message_id
- [x] tests/test_db.py-a 9 yeni test əlavə edildi (lifecycle, xəta, reset, miqrasiya legacy-schema simulyasiyası ilə) — 14/14 keçdi
- [x] Tam test dəsti: 30/30 keçdi
- **Status:** complete

### Phase 9: TTS modulu
- [x] core/tts.py — generate_narration(text, output_path, voice) -> None (edge-tts wrapper, birbaşa fayla yazır — spesifikasiyadakı "bytes" əvəzinə fayl-yolu interfeysi seçildi, çünki edge_tts.Communicate.save() nativ olaraq fayla yazır və ffmpeg-ə fayl lazımdır)
- [x] config/settings.py: fal_api_key, tts_voice, video_worker_interval_minutes, videos_dir sahələri əlavə edildi; .env.example yeniləndi
- [x] tests/test_tts.py (2 test, edge_tts.Communicate mock edilərək) — real smoke-test artıq brainstorming zamanı edilmişdi (bax findings.md)
- [x] Mövcud testlərdə Settings(...) qurulan yerlər (test_scheduler.py, test_telegram_bot.py) yeni sahələrlə yeniləndi
- [x] Tam test dəsti: 32/32 keçdi
- **Status:** complete

### Phase 10: VideoProvider interfeysi + fal.ai provayderi
- [x] core/video/base.py — VideoProvider abstract interfeys (async generate_clip)
- [x] core/video/fal_provider.py — fal.ai REST API inteqrasiyası: rəsmi sənədlərdən (docs.fal.ai/model-apis/model-endpoints/queue) dəqiq kontrakt araşdırıldı (submit→status_url poll→response_url→video.url endir), aiohttp ilə async (asyncio event loop-u bloklamamaq üçün)
- [x] Model: fal-ai/kling-video/v1.6/standard/text-to-video seçildi (aspect_ratio: 16:9/9:16/1:1, duration: yalnız "5" və ya "10" saniyə — _map_duration() ilə səhnə uzunluğu bunlara yuvarlaqlaşdırılır)
- [x] tests/test_fal_provider.py (4 test — tam axın, timeout, HTTP xətası, duration mapping)
- [x] **Diqqət:** `aioresponses` kitabxanası quraşdırılmış `aiohttp` 3.14.1 ilə uyğunsuz çıxdı (ClientResponse.__init__ dəyişikliyi) — silinib, əvəzinə əl ilə FakeResponse/FakeSession mock-ları yazıldı (bax findings.md)
- [ ] fal.ai hesabı/API açarı istifadəçidən alınacaq, real smoke-test ediləcək — İSTİFADƏÇİ QEYDİYYATDAN KEÇİR, GÖZLƏNİLİR
- **Status:** complete (kod+mock testlər; real smoke-test gözləyir)

### Phase 11: Video pipeline (orkestrasiya)
- [x] core/video_pipeline.py — TTS + hər səhnə üçün klip + ffmpeg concat/mux → final mp4 (format-a görə aspect_ratio: shorts→9:16, long→16:9)
- [x] ffmpeg subprocess çağırışları (_concat_clips, _mux_audio, _probe_duration, _run_ffmpeg), uzunluq fərqi idarəetməsi (audio uzun olsa tpad ilə freeze-frame, video uzun/bərabər olsa -shortest ilə sadə kopya)
- [x] tests/test_video_pipeline.py (10 test — orkestrasiya, boş səhnə xətası, fal.ai xətasının ötürülməsi, ffmpeg/ffprobe uğursuzluğu, concat tək/çox klip, mux hər iki budaq)
- [x] **Real ffmpeg smoke-test edildi:** sintetik test klipləri (ffmpeg testsrc) + test audio ilə real _concat_clips/_mux_audio işlədildi — 6s video + 8s audio → düzgün 8s final (h264+aac stream-ləri sağlam, ffprobe ilə doğrulandı)
- **Status:** complete

### Phase 12: Telegram video axını + video worker
- [x] bot/telegram_bot.py genişləndirildi: video_approve/video_reject/video_regenerate callback handler-ləri, _build_video_keyboard, send_video_for_review (FSInputFile ilə bot.send_video)
- [x] bot/video_worker.py — öz AsyncIOScheduler-i (bot/scheduler.py-dəki kimi), IntervalTrigger (VIDEO_WORKER_INTERVAL_MINUTES), max_instances=1, get_next_idea_for_video ilə tapıb pipeline-ı işlədir, uğurda video göndərir, xətada mark_video_failed + Telegram xəbərdarlığı
- [x] tests/test_telegram_bot.py-a 2 test əlavə edildi (video keyboard, send_video_for_review)
- [x] tests/test_video_worker.py yazıldı (4 test — boş növbə, uğurlu emal, artıq-işlənən ideanın keçilməsi, xəta+bildiriş)
- [x] Tam test dəsti: 52/52 keçdi
- **Status:** complete

### Phase 13: İnteqrasiya, VPS deploy, canlı test
- [x] main.py-a video_worker inteqrasiyası (FalAiVideoProvider yaradılır, video_worker.start() edilir, shutdown-da dayandırılır)
- [x] README.md yenilənməsi (FAL_API_KEY, TTS_VOICE, VIDEO_WORKER_INTERVAL_MINUTES, VIDEOS_DIR, fal.ai qeydiyyat təlimatı, yenilənmiş layihə strukturu)
- [x] pytest ilə bütün testlərin işləməsi (52/52)
- [x] Kod VPS-ə sync edildi (tar+scp), .venv yeni asılılıqlarla (edge-tts, aiohttp) yeniləndi
- [x] edge-tts VPS-də (Linux) real audio generasiyası ilə doğrulandı (Azərbaycan səsləri işləyir)
- [x] FAL_API_KEY .env-ə əlavə edildi, systemd xidməti yeni kodla restart edildi (scheduler + video worker hər ikisi aktiv, journalctl-da təsdiqləndi)
- [x] Canlı test edildi: video worker id=1 ideanı avtomatik götürdü → fal.ai-yə çağırış → **403 "User is locked. Reason: Exhausted balance"** (fal.ai hesab balansı bloku, KOD PROBLEMİ DEYİL). Worker düzgün mark_video_failed etdi + Telegram xəbərdarlığı göndərdi
- [x] Tam pipeline fal.ai-siz canlı doğrulandı: saxta VideoProvider (ffmpeg testsrc) ilə build_video → 5 səhnə concat + Azərbaycan TTS mux → 370KB mp4 → Telegram-a send_video uğurla. TTS+ffmpeg+Telegram video axını CANLI İŞLƏKDİR
- [ ] **BLOKER (istifadəçi tərəfi):** fal.ai/dashboard/billing-də balans/ödəniş metodu əlavə edilməlidir. Sonra idea 1-in video_status NULL-a reset edilib avtomatik təkrar götürülə bilər
- **Status:** complete (kod tam işlək, canlı doğrulanıb; fal.ai balansı istifadəçi tərəfi bloker, koddan asılı deyil)

## Key Questions
1. Gemini/Groq/Ollama Python SDK-larının konkret çağırış imzaları necədir? (Phase 3-də araşdırılacaq) — HƏLL OLUNUB
2. aiogram-ın hazırkı versiyasında (v3) inline keyboard callback strukturu necədir? (Phase 5-də araşdırılacaq) — HƏLL OLUNUB
3. fal.ai-nin dəqiq REST API kontraktı (endpoint, sorğu/cavab formatı, poll mexanizmi) necədir? — HƏLL OLUNUB (bax findings.md)
4. Hansı fal.ai modeli (Kling/LTX/SVD) kənd/çoban/yemək səhnələri üçün ən uyğun keyfiyyət/kvota balansını verir? (Phase 13-də real sınaqla, hazırda Kling v1.6 standard seçilib)

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Tək prosesli Python (aiogram long-polling + APScheduler + SQLite) | Sadə, ictimai HTTPS/webhook tələb etmir, faza 1 üçün YAGNI |
| Gemini əsas, Groq/Ollama fallback LLM provayderi | İstifadəçinin mövcud pulsuz API açarları, Azərbaycan dili keyfiyyəti üçün Gemini üstünlük |
| SQLite (fayl əsaslı) DB | Kiçik miqyas, əlavə server tələb etmir, faza 2 üçün asan oxuna bilər |
| Video generasiya seçimi bu fazaya daxil deyil | Ayrıca faza kimi planlaşdırılıb, spesifikasiyada qeyd olunub |
| Faza 2: fal.ai video provayderi | Unified API, rəsmi sənədlər, birdəfəlik $10 pulsuz kredit — kod boşa getməsin deyə VideoProvider interfeysi arxasında |
| Faza 2: edge-tts TTS üçün | Tam pulsuz, açar tələb etmir, Azərbaycan dilində 2 doğma səs birbaşa yoxlanıldı (az-AZ-BabekNeural/BanuNeural) |
| Faza 2: TTS bu fazaya daxildir, ambient səs effektləri Faza 3-ə saxlanılıb | İstifadəçi qərarı — səssiz video mənasız olardı, amma fon effektləri ayrıca genişlənmə kimi qala bilər |
| Faza 2: video worker arxa planda avtomatik (əl əmri yox) | İstifadəçi qərarı — tam avtomatlaşdırma məqsədinə uyğun, Telegram callback-i bloklamamaq üçün ayrıca APScheduler job |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- Spesifikasiya: docs/superpowers/specs/2026-07-11-phase1-script-generator-design.md
- Update phase status as you progress: pending → in_progress → complete
- Re-read this plan before major decisions (attention manipulation)
- Log ALL errors - they help avoid repetition
- **VACIB (Phase 5/7):** logging/main.py-da UTF-8 konsol konfiqurasiyası unutma (Windows cp1252 problemi, bax findings.md)
