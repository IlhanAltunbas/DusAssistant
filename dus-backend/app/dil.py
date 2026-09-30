import re

# Dil koddan belirlenir, modele sorulmaz. "Sorunun dilinde cevap ver" talimatına rağmen model
# İngilizce soruların bir kısmına Türkçe cevap veriyordu; açık bir "Answer in English" çok daha
# güvenilir. Uygulama sadece Türkçe ve İngilizce destekliyor.
# Ayrı modülde: rag_motoru import edilince LLM ve arama istemcileri kurulur; bu fonksiyon onlar
# olmadan test edilebilsin.
_TR_HARFLER = re.compile(r"[çğıöşüÇĞİÖŞÜ]")
# Türkçe karakter içermeyen Türkçe sorular için ("Gingivitis nedir?").
_TR_KELIMELER = {
    "nedir", "nelerdir", "neden", "nedenleri", "hangi", "hangisi", "hangileri", "ne", "kac", "mi", "mu",
    "midir", "mudur", "ve", "ile", "bu", "bunlar", "bunlardan", "bunu", "tedavi", "tedavisi", "belirtileri",
    "tanimi", "anlat", "anlatir", "misin", "olur", "olan", "veya", "daha", "peki", "tedavisinde",
}
_EN_KELIMELER = {
    "what", "which", "how", "why", "when", "where", "who", "is", "are", "was", "were", "the", "a", "an", "of",
    "for", "does", "do", "can", "explain", "describe", "and", "in", "to", "with", "between", "list", "tell",
    "me", "difference", "treated", "treatment", "these", "this", "it",
}


def soru_dili(metin: str) -> str:
    if _TR_HARFLER.search(metin):
        return "tr"
    kelimeler = set(re.findall(r"[a-z]+", metin.lower()))
    if kelimeler & _TR_KELIMELER:
        return "tr"
    if kelimeler & _EN_KELIMELER:
        return "en"
    # Karar verilemezse ("Periodontitis?"): asıl kullanıcılar Türk öğrenciler.
    return "tr"
