import pytest

from app.dil import soru_dili


@pytest.mark.parametrize(
    ("soru", "beklenen"),
    [
        # Türkçe karakter varsa kelimelere bakılmadan Türkçe.
        ("Periodontitis nasıl tedavi edilir?", "tr"),
        ("DİŞ ETİ ÇEKİLMESİ", "tr"),
        # Türkçe karakter yok ama Türkçe kelime var.
        ("Gingivitis nedir?", "tr"),
        ("Periodontitis tedavisi nelerdir", "tr"),
        # İngilizce kelimeler; büyük harf fark etmez.
        ("What is gingivitis?", "en"),
        ("HOW IS PERIODONTITIS TREATED", "en"),
        ("Explain the difference between gingivitis and periodontitis", "en"),
        # Karar verilemiyorsa varsayılan Türkçe: asıl kullanıcılar Türk öğrenciler.
        ("Periodontitis?", "tr"),
        ("", "tr"),
    ],
)
def test_soru_dili(soru, beklenen):
    assert soru_dili(soru) == beklenen


def test_turkce_kelime_ingilizce_kelimeden_once_gelir():
    # Karışık soruda Türkçe kazanır: "ne" Türkçe listede, "is" İngilizce listede.
    assert soru_dili("Periodontitis ne is") == "tr"
