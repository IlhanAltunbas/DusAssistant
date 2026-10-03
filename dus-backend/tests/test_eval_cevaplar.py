"""Eval scriptinin çıktı biçimlendirmesi: bir biçimlendirme hatası ücretli bir çalıştırmayı yarıda kesmesin."""
import pytest

from eval.cevaplar import cevap_dili, satir_durumu

ORTAK = {"reddetti": False, "tam_dogru": False, "anahtar_kapsam": None, "hakem": {}}


@pytest.mark.parametrize(("sonuc", "beklenen"), [
    ({"reddetti": True, "anahtar_kapsam": 0.0}, "RET"),
    ({"tam_dogru": True, "anahtar_kapsam": 1.0}, "doğru"),
    ({"anahtar_kapsam": 0.5}, "kapsam 50%"),
    # Cevapsız soruda anahtar bilgi yok; reddetmeyip cevaplarsa kapsam boş kalır.
    ({"anahtar_kapsam": None}, "CEVAPLADI"),
    ({"hakem": "bütçe aşıldı"}, "-"),
])
def test_satir_durumu(sonuc, beklenen):
    assert satir_durumu({**ORTAK, **sonuc}) == beklenen


@pytest.mark.parametrize(("metin", "beklenen"), [
    ("Ante's law states that the root surface area of the abutments should be at least equal.", "en"),
    ("Destek dişlerin kök yüzey alanı, yerine konan dişlerinkine en az eşit olmalıdır.", "tr"),
    # İngilizce cevapta geçen tek bir Türkçe terim cevabı Türkçe yapmaz.
    ("The notes call this condition dişeti çekilmesi, which is gingival recession.", "en"),
    # Sadece bir isim: dil ölçülemez, hata da sayılmaz.
    ("Jens Waerhaug (1907–1980).", None),
])
def test_cevap_dili(metin, beklenen):
    assert cevap_dili(metin) == beklenen
