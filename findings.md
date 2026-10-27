# Findings & Decisions

## Requirements
<!-- Captured from user request -->
- Kanal nişi: Laçının Oğuldərə kəndi, çobanın gündəlik həyatı, kamp yeməkləri/reseptlər
- Dil: Azərbaycan, AI TTS üçün ssenari mətni
- Video format: həm Shorts (≤60s), həm uzun format (5-10 dəq) — fazalı yanaşma, əvvəl Shorts
- Video generasiyası: tam AI text-to-video (gələcək fazada, hazırda pulsuz seçimlərlə)
- LLM: istifadəçinin Groq və Gemini pulsuz API açarları var, Ollama-ya açıqdır
- Telegram: həm gündəlik avtomatik, həm /generate əmri ilə on-demand
- Faza 1 əhatəsi: yalnız mövzu/ssenari generasiyası + Telegram təsdiq axını (video/səs/upload sonrakı fazalarda) — TAMAMLANDI
- Faza 2 tələbləri: video provayder = fal.ai; TTS Faza 2-yə daxildir (ambient effektlər Faza 3-ə saxlanılıb); hazır video Telegram-a göndərilib ikinci dəfə təsdiq alınır; video generasiyası ssenari təsdiqindən sonra avtomatik, arxa planda başlayır

## Research Findings
<!-- Key discoveries during exploration -->
- Sistemdə "python" alias-ı Windows Store shim-inə işarə edir və işləmir; "py" launcher-i istifadə olunmalıdır (py -m venv, py -m pip)
- GEMINI_API_KEY və GROQ_API_KEY artıq istifadəçinin sistem mühit dəyişənləri kimi qurulub (dəyərlər qeyd edilmir — təhlükəsizlik), .env faylı olmasa da settings.py bunları oxuyur
- requirements.txt (aiogram, APScheduler, python-dotenv, google-generativeai, groq, ollama, pytest) .venv-də uğurla quraşdırıldı, Python 3.14.0
- **Faza 2 araşdırması (2026-07-12):** Tam pulsuz/limitsiz text-to-video API bazarda yoxdur — Runway (125 kredit bir dəfəlik), Kling (66/gün təkrarlanan), Luma (5/gün), Hailuo (200 bir dəfəlik), fal.ai ($10 bir dəfəlik, unified API). fal.ai seçildi (unified API, rəsmi sənədlər).
- **edge-tts birbaşa yoxlanıldı** (WebSearch nəticələrinə etibar etmək əvəzinə): `.venv/Scripts/python.exe -m edge_tts --list-voices` Azərbaycan üçün iki səs qaytardı — `az-AZ-BabekNeural` (kişi), `az-AZ-BanuNeural` (qadın). Test cümləsi ilə mp3 generasiyası uğurla nəticələndi (41KB fayl), açar/hesab tələb olunmur.
- **ffmpeg mövcudluğu təsdiqləndi:** həm lokal Windows mühitdə (8.1.2, gyan.dev build), həm Hetzner VPS-də (8.0.1, Ubuntu paketi) — Faza 2 üçün əlavə quraşdırma lazım deyil.
- **fal.ai REST API kontraktı** (WebFetch ilə docs.fal.ai-dən): POST `https://queue.fal.run/{model-id}` (header `Authorization: Key $FAL_KEY`) → `{request_id, status_url, response_url}` qaytarır. GET `status_url` ilə poll (`IN_QUEUE`→`IN_PROGRESS`→`COMPLETED`). GET `response_url` nəticəni qaytarır, video modelləri üçün `{"video": {"url": "..."}}`.
- **Model seçimi:** `fal-ai/kling-video/v1.6/standard/text-to-video`. Giriş: `prompt` (məcburi), `duration` (yalnız "5" və ya "10" saniyə — sərbəst ədəd deyil!), `aspect_ratio` (16:9/9:16/1:1), `negative_prompt`, `cfg_scale`. Bizim scenes_json-dakı duration_sec (8-15 saniyə aralığı) bu iki dəyərdən birinə yuvarlaqlaşdırılmalıdır (`_map_duration()` funksiyası: ≤7→"5", >7→"10").
- **aioresponses kitabxanası uyğunsuzluğu:** quraşdırılmış aiohttp 3.14.1-in `ClientResponse.__init__()` artıq `stream_writer` keyword arqumenti tələb edir, aioresponses 0.7.9 (ən son versiya) bunu vermir → `TypeError`. PyPI-də daha yeni versiya yoxdur. Həll: aioresponses silinib, tests/test_fal_provider.py-də əl ilə FakeResponse/FakeSession sinifləri yazılıb (aiohttp.ClientSession-u patch edərək) — asılılıq əlavə etmədən, tam nəzarətlə. Gələcəkdə oxşar aiohttp-mock ehtiyacı olsa bu nümunədən istifadə et, aioresponses-a etibar etmə.
- **fal.ai balansı bloku (2026-07-12 canlı test):** fal.ai API açarı VPS-ə qoyuldu, real çağırış edildi — `403 Forbidden`, body: `{"detail":"User is locked. Reason: Exhausted balance. Top up your balance at fal.ai/dashboard/billing."}`. Yəni fal.ai hesabının pulsuz krediti mövcud deyil/tükənib, ödəniş metodu/balans əlavə edilməlidir. Kod düzgün işləyir (Faza 1-dəki Gemini kvota=0 ilə eyni pattern): worker sorğunu göndərdi, 403 aldı, mark_video_failed etdi, Telegram-a xəbərdarlıq göndərdi — spam yoxdur (failed status təkrar götürülmür).
- **Tam pipeline canlı doğrulandı (fal.ai istisna olmaqla):** VPS-də saxta VideoProvider (ffmpeg testsrc ilə real klip qaytaran) ilə build_video işlədildi — 5 səhnə → concat → Azərbaycan TTS narrasiyası mux → 370KB mp4 → Telegram-a send_video ilə uğurla göndərildi. Deməli TTS + ffmpeg + Telegram video axını canlı işləkdir, yeganə bloklu nöqtə fal.ai balansıdır.
- **PULSUZ ALTERNATİV (2026-07-12, istifadəçi qərarı):** fal.ai balans tələb etdiyi üçün tam pulsuz yola keçildi. **Pollinations AI** (image.pollinations.ai) — açar/qeydiyyat/ödəniş tələb ETMİR, sadəcə URL: `https://image.pollinations.ai/prompt/{quoted}?width=W&height=H&nologo=true&model=flux&seed=S`. Birbaşa yoxlandı: 60-90KB JPEG, ~1.5 saniyədə. Qeyd: bəzən çözünürlüyü aşağı salır (576x1024 qaytardı 1080x1920 istənəndə) amma ffmpeg scale/crop bunu düzəldir. Video (ltx-2) Pollinations-da Pollen krediti tələb edir — istifadə etmirik, yalnız pulsuz şəkil.
- **Ken Burns yanaşması:** statik AI şəkil → ffmpeg zoompan ilə yavaş zoom hərəkəti → video klip. Komanda: `ffmpeg -loop 1 -i img.jpg -vf "scale=W:H:force_original_aspect_ratio=increase,crop=W:H,zoompan=z='min(zoom+0.0015,1.15)':d=FRAMES:s=WxH:fps=30" -t DUR -c:v libx264 -pix_fmt yuv420p out.mp4`. Real uc-uca test: 711KB h264 1080x1920 8s klip. Üstünlük: duration sərbəstdir (Kling-in 5/10s məhdudiyyəti yoxdur), "slow life" janrına uyğun. VideoProvider interfeysinə mükəmməl oturur — pipeline/worker/Telegram dəyişmədi.

## Technical Decisions
<!-- Decisions made with rationale -->
| Decision | Rationale |
|----------|-----------|
| aiogram (async) Telegram bot framework | Müasir, aktiv dəstəklənən, Python async/await ilə təbii inteqrasiya |
| APScheduler gündəlik cron üçün | Sadə, xarici asılılıq tələb etmir, in-process işləyir |
| SQLite content_ideas cədvəli status sütunu ilə (pending/approved/rejected) | Faza 2 video-agentinin approved sətirləri oxuması üçün sadə queue rolu |

## Issues Encountered
<!-- Errors and how they were resolved -->
| Issue | Resolution |
|-------|------------|
| Gemini API açarında pulsuz kvota 0-dır (429 quota exceeded, `generate_content_free_tier_requests` limit: 0) — Google AI Studio layihəsində free-tier aktiv deyil görünür | Router avtomatik Groq-a keçdi, hazırda Groq faktiki əsas provayder rolunu oynayır. İstifadəçi Google AI Studio-da kvota/billing tənzimləməsini yoxlamalıdır. Kod tərəfində dəyişiklik tələb olunmur. |
| `google-generativeai` paketi deprecated-dir (Google `google-genai`-a keçməyi tövsiyə edir, "all support has ended") | Hələlik işləkdir (FutureWarning ilə), funksionallığa təsir etmir. Gələcəkdə `google-genai`-a miqrasiya nəzərdən keçirilə bilər, hazırkı fazada bloker deyil. |
| Windows konsolunun defolt kodlaşdırması (cp1252) Azərbaycan hərflərini (ı, ə, ğ, ş və s.) çap edərkən UnicodeEncodeError verir | Tətbiq kodunda deyil, yalnız ad-hoc test skriptində (print) baş verdi. Phase 5/7-də logging və əsas giriş nöqtəsi UTF-8 ilə konfiqurasiya olunacaq (məs. `sys.stdout.reconfigure(encoding="utf-8")` və ya PYTHONIOENCODING=utf-8), Telegram mesajları bundan təsirlənmir (API UTF-8 istifadə edir) |
| Real smoke-testdə Groq-un gündəlik token kvotası (TPD: 100000) demək olar tükənmişdi (99712 istifadə olunub), Gemini free-tier=0, Ollama lokal işə salınmayıb — üç provayder də eyni anda uğursuz oldu | Kod səviyyəsində problem deyil: router düzgün olaraq bütün provayderləri sınadı və aydın `AllProvidersFailedError` atdı (hər provayderin ayrıca xəta mesajı ilə). Real istifadədə Groq/Gemini gündəlik kvotalarının sıfırlanmasını gözləmək və ya lokal Ollama qurmaq lazımdır |
| Bu Windows maşınından `api.telegram.org`-a TCP bağlantısı timeout verir (DNS düzgün həll olunur — 149.154.166.110 — amma bağlantı qurulmur), halbuki Google/Groq API-lərinə çıxış problemsizdir | Sandbox/mühit problemi deyil, konkret Telegram-a şəbəkə filtrasiyası (Azərbaycanda bəzi provayderlərdə Telegram məhdudlaşdırılması adi haldır). Nəticə: bu mühitdən botun canlı Telegram testini apara bilmədim. İstifadəçi qərarı: canlı test təxirə salınıb, bot Hetzner VPS-ə (TV Monitorinq üçün istifadə olunan) deploy ediləndə orada sınanacaq — VPS şəbəkəsi filtrasiyaya məruz qalmır |

## Video provayder seçimləri — 2026-07-12 tam araşdırma (yekun)
Bu istifadəçi üçün "tam avtomatik + yüksək keyfiyyət + pulsuz" MÜMKÜN DEYİL. Hər seçim:
- **fal.ai** (Kling 1.6 std, $0.056/san): rəsmi API var, kod hazır, işləyir — amma balans tələb edir. ~$0.84-2.80/video (5 səhnə × 5-10san). $5 ≈ 2-6 video.
- **NVIDIA cosmos3-nano**: "Free Endpoint" görünür amma hosted API HƏLƏ CANLI DEYİL (NVIDIA forumu təsdiqləyir, bütün yollar 404). Açar 121 modelə çıxış verir (LLM/VLM) amma video generator yox. Açar keçərlidir, saxlanılmır.
- **Nano Banana / Gemini image (gemini-2.5-flash-image)**: gündə 500 pulsuz şəkil OLARDI, amma bu istifadəçinin Google hesabında `free_tier limit: 0` (2 fərqli açarla təsdiq). Bu, hesab/layihə səviyyəli problemdir, təzə açar düzəltmir — başqa Google hesabı və ya billing lazımdır.
- **ElevenLabs**: Azərbaycan (Eleven v3) dəstəyi var, amma pulsuz ayda 10k simvol (~2-3 video) + pulsuz API-də səs kitabxanası bağlı → avtomatlaşma üçün yararsız. edge-tts daha praktik.
- **SYNTX.ai**: 90+ model (Kling3/Veo3.1/Seedance), ekstra keyfiyyət — AMMA developer API YOX, yalnız Telegram/veb manual. Avtomatlaşma mümkün deyil.
- **Midjourney**: rəsmi API yox (2026), pulsuz tarif yox, yalnız qeyri-rəsmi ToS-pozan wrapper-lər (ban riski). İstifadə edilməyəcək.
- **Pollinations + edge-tts**: TAM PULSUZ, açarsız, avtomatik, İŞLƏYİR. Keyfiyyət "orta" (şəkil+hərəkət, real video yox). İstifadəçi bunu saxlayıb keyfiyyətini maksimallaşdırmağı seçdi (kinematik prompt + 4 hərəkət preset-i əlavə edildi).

**Nəticə:** avtomatlaşma rəsmi API tələb edir. Yüksək-keyfiyyətli tanınmış alətlər (Midjourney/SYNTX) qəsdən API vermir. Real qərar: pulsuz Pollinations (orta keyfiyyət) VƏ YA fal.ai balans (yaxşı keyfiyyət, pullu). Nano Banana yalnız işlək Google hesabı ilə açılır.

## Resources
<!-- URLs, file paths, API references -->
- Spesifikasiya: C:\Users\Alihuseyn Ibrahimov\PycharmProjects\youtube-ai-studio\docs\superpowers\specs\2026-07-11-phase1-script-generator-design.md
- Layihə kökü (lokal): C:\Users\Alihuseyn Ibrahimov\PycharmProjects\youtube-ai-studio
- Layihə kökü (VPS, canlı): root@<SERVER_IP>:/root/youtube-ai-studio/ (SSH açarı: C:\Users\Alihuseyn Ibrahimov\.ssh\hetzner_tvmonitor) — hazırda `nohup` ilə arxa planda işləyir, systemd xidməti hələ qurulmayıb
- Telegram bot: @oghuldere_villigebot, chat_id: 7622824986

## Visual/Browser Findings
<!-- CRITICAL: Update after every 2 view/browser operations -->
-

---
*Update this file after every 2 view/browser/search operations*
