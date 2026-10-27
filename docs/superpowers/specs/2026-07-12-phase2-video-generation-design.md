# Faza 2: Video Generasiya Agenti

**Tarix:** 2026-07-12
**Status:** Təsdiqlənib (dizayn səviyyəsində)
**Asılılıq:** Faza 1 (bax: [2026-07-11-phase1-script-generator-design.md](2026-07-11-phase1-script-generator-design.md)) — tamamlanıb, VPS-də canlı işləyir.

## Məqsəd

Faza 1-də təsdiqlənmiş (`status='approved'`) ssenariləri götürüb tam AI-generasiya olunmuş, Azərbaycan dilində səsləndirilmiş video fayllarına çevirən, nəticəni Telegram vasitəsilə ikinci dəfə təsdiq üçün göndərən alt-sistem. Bu fazanın çıxışı (təsdiqlənmiş videolar) sonrakı fazalarda (səs effektləri, YouTube upload) giriş kimi istifadə ediləcək.

## Kontekst və araşdırma

- **Video generasiya provayderi:** fal.ai seçildi — unified REST API, Kling/LTX/Stable Video Diffusion kimi modellərə tək açarla çıxış, rəsmi sənədlər. Qeydiyyatda $10 pulsuz kredit (bir dəfəlik, ~50-100 generasiya). Bazarda tam pulsuz/limitsiz text-to-video API mövcud deyil (Runway/Kling/Luma/Hailuo də ya bir dəfəlik, ya da kiçik gündəlik kvotalarla məhdudlaşır) — bu, layihənin qəbul etdiyi bilinən məhdudiyyətdir.
- **TTS (səsləndirmə):** `edge-tts` (pulsuz, açıqkodlu, Microsoft Edge-in "oxu" xidmətindən istifadə edir, API açarı tələb etmir) seçildi. Birbaşa yoxlanıldı: Azərbaycan dilində iki doğma səs mövcuddur — `az-AZ-BabekNeural` (kişi) və `az-AZ-BanuNeural` (qadın). Test generasiyası uğurla nəticə verdi.
- **Video birləşdirmə:** `ffmpeg` — həm lokal Windows mühitdə, həm Hetzner VPS-də mövcudluğu təsdiqləndi.
- **Əhatə qərarı:** TTS (nəqletmə səsi) bu fazaya daxildir (videonun mənalı olması üçün zəruridir). Fon/təbiət səs effektləri (ambient) Faza 3-ə saxlanılıb.
- **Çatdırılma qərarı:** Hazır video Telegram-a göndərilir və Faza 1-dəki kimi ✅/❌/🔄 düymələri ilə ikinci dəfə təsdiq alınır (avtomatik YouTube-a getmir).
- **Tetiklənmə qərarı:** Ssenari təsdiqlənən kimi (✅) video generasiyası avtomatik, arxa planda başlayır (əl ilə əmr tələb olunmur).

## Əhatə (Scope) — Yalnız bu faza

Daxildir:
- fal.ai ilə səhnə-səhnə text-to-video klip generasiyası
- edge-tts ilə tam ssenari mətninin Azərbaycan dilində səsləndirilməsi
- ffmpeg ilə klip birləşdirmə + səs mux etmə
- Arxa planda avtomatik tetiklənən video worker (approved ideaları tapıb emal edir)
- Hazır videonun Telegram-a göndərilməsi + ✅/❌/🔄 ikinci təsdiq axını

Daxil deyil (gələcək fazalar):
- Fon/təbiət səs effektləri, musiqi (Faza 3)
- YouTube-a avtomatik yükləmə, monetizasiya izləmə (Faza 4)
- Paralel/çoxlu video emalı (hazırda bir dəfəyə tək ideya)

## Arxitektura

Faza 1-in nümunəsinə uyğun: mövcud `main.py` prosesinə əlavə bir APScheduler interval job-u (video worker) qoşulur — ayrıca proses və ya servis YARADILMIR, eyni bot prosesi daxilində işləyir.

**Video worker davranışı:** hər 2 dəqiqədə bir DB-də `status='approved' AND video_status IS NULL` şərtinə uyğun BİR sətir axtarır (LIMIT 1). Tapsa, dərhal `video_status='processing'` işarələyir (təkrar götürülməsinin qarşısını almaq üçün), sonra pipeline-ı sinxron şəkildə işlədir. Növbəti job tick-i pipeline bitənə qədər gözləyir (APScheduler eyni job-un üst-üstə düşməsinə yol vermir, `max_instances=1`).

**Niyə arxa plan job-u, birbaşa callback-də deyil:** Telegram callback handler-ləri sürətli cavab qaytarmalıdır (bir neçə saniyə); video generasiyası bir neçə dəqiqə çəkə bilər (bir neçə fal.ai çağırışı + TTS + ffmpeg). Callback daxilində sinxron gözləmək Telegram-ın cavab gözləmə vaxtını poza bilər və botu bloklayar (başqa istifadəçi əmrlərini gecikdirər).

## Layihə strukturu

```
core/
  video/
    base.py            — VideoProvider interfeysi: generate_clip(prompt: str, duration_sec: int) -> bytes
    fal_provider.py     — fal.ai REST API inteqrasiyası (sorğu göndər → poll et → nəticəni endir)
  tts.py                — generate_narration(text: str, voice: str) -> bytes (edge-tts wrapper)
  video_pipeline.py      — orkestrasiya: TTS + hər səhnə üçün klip + ffmpeg concat/mux → final mp4 yolu
bot/
  video_worker.py        — APScheduler job: approved+video_status IS NULL ideanı tapır, pipeline-ı işlədir, nəticəni DB-yə yazır, Telegram-a göndərir
  telegram_bot.py         — genişlənir: video_approve/video_reject/video_regenerate callback handler-ləri
tests/
  test_video_pipeline.py  — fal.ai/ffmpeg/tts mock edilərək pipeline məntiqi testi
  test_video_worker.py    — worker-in DB seçimi + status keçidləri testi
```

## Data modeli (genişlənmə)

`content_ideas` cədvəlinə yeni sütunlar:

| Sütun | Tip | Təsvir |
|---|---|---|
| video_status | TEXT | `NULL` (hələ başlanmayıb) \| `processing` \| `ready` \| `approved` \| `rejected` \| `failed` |
| video_path | TEXT | Yerli fayl yolu, məs. `data/videos/<id>.mp4` |
| video_telegram_message_id | INTEGER | Video mesajının Telegram ID-si (düymə callback-lərini bağlamaq üçün) |
| video_error | TEXT | Son xəta mesajı (uğursuz olduqda) |

## Data axını

1. Video worker (hər 2 dəqiqə) `status='approved' AND video_status IS NULL` olan bir sətir tapır → `video_status='processing'`.
2. `video_pipeline.build_video(idea)`:
   a. `tts.generate_narration(idea.script_text)` → narrasiya mp3 faylı.
   b. Hər `scene` üçün `VideoProvider.generate_clip(scene.description, scene.duration_sec)` → yerli mp4 klip faylı (sıra ilə, ardıcıl — paralel deyil, kvota qorumaq üçün).
   c. `ffmpeg`: bütün səhnə klipləri ardıcıl birləşdirilir (concat demuxer), üzərinə narrasiya səsi mux edilir. Uzunluq fərqi olarsa: audio video-dan uzundursa son kadr dondurulur (freeze-frame padding), video audio-dan uzundursa video kəsilir.
   d. Nəticə `data/videos/<idea.id>.mp4`-ə yazılır.
3. Uğur: `video_status='ready'`, `video_path` yazılır → video Telegram-a göndərilir (✅ Təsdiqlə/❌ Rədd et/🔄 Yenidən düymələri ilə) → `video_telegram_message_id` saxlanılır.
4. Uğursuzluq (istənilən addımda): `video_status='failed'`, `video_error` yazılır → Telegram-a xəbərdarlıq mesajı.
5. İstifadəçi düyməyə basır:
   - ✅ Təsdiqlə → `video_status='approved'` (Faza 4 üçün hazır)
   - ❌ Rədd et → `video_status='rejected'`
   - 🔄 Yenidən → `video_status=NULL` (worker növbəti tick-də yenidən götürür)

## Xəta idarəetməsi

- fal.ai klip generasiyası uğursuz olarsa (kvota bitib, timeout, model xətası) → pipeline dərhal dayanır, `video_status='failed'`, xəta Telegram-a göndərilir, artıq yaradılmış qismi klip faylları silinir (yarımçıq iş qalmasın deyə).
- ffmpeg xətası (uyğunsuz kodek, boş fayl və s.) eyni şəkildə tutulur və `failed` statusuna keçir.
- Video worker `max_instances=1` ilə qurulur ki, əvvəlki pipeline bitmədən yeni tick eyni resursları paralel istifadə etməsin.
- Prosesin özü heç bir halda dayanmır (Faza 1-dəki scheduler kimi try/except ilə izolə olunur).

## Test strategiyası

- `video_pipeline.py`: fal.ai provayderi və `subprocess.run` (ffmpeg) mock edilərək — uğurlu axın, fal.ai xətası, ffmpeg xətası ssenariləri.
- `video_worker.py`: DB-də uyğun sətrin seçilməsi (`approved` + `video_status IS NULL`), status keçidlərinin düzgünlüyü.
- `tts.py`: real edge-tts çağırışı ilə smoke-test (artıq brainstorming zamanı edildi, Azərbaycan səsləri işlək).
- fal.ai inteqrasiyası üçün real API sınağı implementasiya mərhələsində ediləcək — istifadəçidən fal.ai hesabı/API açarı tələb olunacaq.

## Konfiqurasiya (.env əlavələri)

```
FAL_API_KEY=
TTS_VOICE=az-AZ-BabekNeural
VIDEO_WORKER_INTERVAL_MINUTES=2
```

## Açıq qalan suallar (gələcək fazalarda həll ediləcək)

- fal.ai-də hansı konkret modelin (Kling/LTX/SVD) ən uyğun keyfiyyət/kvota balansını verdiyi — implementasiya zamanı sınaqla müəyyənləşdiriləcək.
- Fon/təbiət səs effektləri mənbəyi və miksləmə strategiyası (Faza 3).
- YouTube API vasitəsilə avtomatik yükləmə (Faza 4).
