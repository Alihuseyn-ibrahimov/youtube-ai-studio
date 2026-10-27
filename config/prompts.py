NICHE_CONTEXT = """Sən Azərbaycan dilində YouTube kanalı üçün ssenari yazan köməkçisən.
Kanalın mövzusu: Laçının Oğuldərə kəndində bir çobanın gündəlik yaşam tərzi,
kənd həyatı və kamp şəraitində bişirilən yeməklərin resept prosesi.
Ton: səmimi, sakit, təbiətlə bağlı, "sakit kənd həyatı" (slow life) janrına uyğun."""

FORMAT_GUIDANCE = {
    "shorts": "Video formatı: YouTube Shorts, 45-60 saniyə. 3-5 qısa səhnə, hər səhnə 8-15 saniyə.",
    "long": "Video formatı: uzun format, 6-9 dəqiqə. 8-12 səhnə, hər səhnə 30-60 saniyə.",
}

TEXT_QUALITY_RULES = """Ssenari mətni (script sahəsi) ÜÇÜN ÇOX VACİB qaydalar (bu, səsli diktor tərəfindən birbaşa oxunacaq):
- YALNIZ təmiz ədəbi Azərbaycan dilində yaz. Başqa heç bir dildən (ingilis, holland, türk, rus və s.) TƏK BİR SÖZ BELƏ qarışdırma.
- Uydurma və ya mövcud olmayan sözlər işlətmə — yalnız real, hər kəsin tanıdığı Azərbaycan sözlərindən istifadə et.
- Hərfləri düzgün yaz (ə, ı, ö, ü, ğ, ş, ç düzgün istifadə olunmalıdır) — imla xətası olmasın.
- script sahəsi XALIS NƏQLETMƏ (narration) olmalıdır — dialoq, replika, tırnaq işarəsi ("..."), personaj adı+iki nöqtə (məs. "Əli: ...") formatı QƏTİYYƏN İŞLƏTMƏ. Diktor sadəcə hadisəni təsvir edir, heç kim danışmır.
- Üç nöqtə (...) və ya yarımçıq cümlə işlətmə — hər cümlə tam və aydın bitməlidir.
- Cümlələr qısa-orta uzunluqda, təbii danışıq axını ilə olmalıdır (TTS üçün rahat oxunmalıdır)."""

RESPONSE_INSTRUCTIONS = """Cavabı YALNIZ aşağıdakı JSON formatında ver, başqa heç bir mətn əlavə etmə:
{
  "title": "Video başlığı (qısa, cəlbedici)",
  "script": "Tam ssenari mətni, Azərbaycan dilində, səsləndirmə üçün hazır",
  "scenes": [
    {"description": "Səhnənin qısa təsviri (video generasiya üçün)", "duration_sec": 10}
  ]
}"""


def build_prompt(format: str) -> str:
    format_guidance = FORMAT_GUIDANCE.get(format)
    if format_guidance is None:
        raise ValueError(f"Unknown format: {format}")
    return (
        f"{NICHE_CONTEXT}\n\n{format_guidance}\n\n{TEXT_QUALITY_RULES}\n\n{RESPONSE_INSTRUCTIONS}\n\n"
        "İndi yeni, əvvəllər istifadə olunmamış bir mövzu seç və ssenarini yaz."
    )
