"""Cevap ölçümü: sistemin cevapları doğru mu, kaynaklara sadık mı, doğru dilde mi, gerektiğinde reddediyor mu?

dus-backend klasöründen çalıştırılır, .env'deki gerçek servisleri kullanır:
    python -m eval.cevaplar                 # 28 soru x 3 tekrar, hakem bütçesi $2.50
    python -m eval.cevaplar --sinir 2 --tekrar 1   # küçük deneme
    python -m eval.cevaplar --butce 1.0     # hakem harcaması üst sınırı ($)

Kodla ölçülebilenler kodla ölçülür (cevap dili, "bilgi yok" cevabı). Anlam karşılaştırması gereken
iki şey bir LLM hakeme sorulur: anahtar bilgiler cevapta var mı, cevapta kaynaklarda olmayan iddia
var mı. Hakem, cevabı üreten modelden (Azure OpenAI) farklı bir model: kendi çıktısını kayırmasın.
"""
import argparse
import json
import re
import sys
import threading
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import anthropic
import openai
from azure.core.exceptions import AzureError
from pydantic import BaseModel

from app.dil import _EN_KELIMELER, _TR_KELIMELER
from app.rag_motoru import Cevap, cevap_uret

KLASOR = Path(__file__).parent
# Maliyet hesabı ve bütçe sınırı için fiyatlar ($ / 1M token: girdi, çıktı).
HAKEM_FIYATLARI = {
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}
ESZAMANLI = 4
# anthropic 0.104'te parse() tipli sonucu (parsed_output) sadece output_format ile üretiyor; parametre
# "deprecated" uyarısı veriyor ama yerine geçen output_config.format bu sürümde tipli parse yapmıyor.
warnings.filterwarnings("ignore", message="The 'output_format' parameter is deprecated")
RET_CUMLELERI = (
    "Bu kaynakların içinde bu soruya dair bir bilgi yok",
    "There is no information about this question in these sources",
)


class Butce:
    """Hakem harcamasını sınırlar. Sınır her çağrıdan önce kontrol edilir; o sırada sürmekte olan
    en fazla ESZAMANLI çağrı tamamlanacağı için gerçek harcama sınırı biraz aşabilir."""

    def __init__(self, sinir: float, fiyat: tuple[float, float]):
        self.sinir, self.fiyat, self.harcanan = sinir, fiyat, 0.0
        self._kilit = threading.Lock()

    def izin_var(self) -> bool:
        with self._kilit:
            return self.harcanan < self.sinir

    def ekle(self, girdi: int, cikti: int) -> None:
        with self._kilit:
            self.harcanan += girdi / 1e6 * self.fiyat[0] + cikti / 1e6 * self.fiyat[1]


class AnahtarBilgiKarari(BaseModel):
    bilgi: str
    cevapta_var: bool


class HakemKarari(BaseModel):
    anahtar_bilgiler: list[AnahtarBilgiKarari]
    desteklenmeyen_iddialar: list[str]
    gerekce: str


HAKEM_TALIMATI = """You grade answers produced by a retrieval-augmented assistant for the Turkish dental \
specialty exam (periodontology). You receive the question, the source excerpts the assistant retrieved, \
the assistant's answer, and the key facts a correct answer must contain. Questions, excerpts and answers \
may be in Turkish or English, or mixed; judge meaning, not language.

1. For each key fact, decide whether the answer states it. Same meaning in any language counts, and \
equivalent numbers and units count. A vaguer, partial or contradicting statement does not count.
2. List every factual claim in the answer that the source excerpts do not support. Paraphrases and \
translations of the excerpts are supported. Framing sentences without factual content need no support. \
Judge support only against the excerpts, never against your own knowledge.

Write gerekce as one or two sentences explaining the main reason for your judgement."""


def cevap_dili(metin: str) -> str:
    # Cevap uzun bir metin; soru dilinin tespitinden farklı olarak çoğunluğa bakılır. İngilizce cevapta
    # Türkçe bir terim (ç, ş...) geçmesi cevabı Türkçe yapmaz.
    kelimeler = re.findall(r"\w+", metin.casefold())
    tr = sum(k in _TR_KELIMELER or bool(re.search(r"[çğıöşü]", k)) for k in kelimeler)
    en = sum(k in _EN_KELIMELER for k in kelimeler)
    return "tr" if tr > en else "en"


def reddetti_mi(metin: str) -> bool:
    return any(c.casefold() in metin.casefold() for c in RET_CUMLELERI)


def hakeme_sor(istemci: anthropic.Anthropic, model: str, soru: dict, cevap: Cevap) -> tuple[HakemKarari | None, dict]:
    kaynaklar = "\n\n".join(
        f"[{i}] {d.metadata.get('source')} p.{d.metadata.get('page', 0) + 1}\n{d.page_content}"
        for i, d in enumerate(cevap.dokumanlar, start=1)
    )
    gecmis = "\n".join(soru["gecmis"]) or "(none)"
    bilgiler = "\n".join(f"- {b}" for b in soru["anahtar_bilgiler"]) or "(none: the question is not answerable from the sources)"
    icerik = (
        f"<question>\n{soru['soru']}\n</question>\n\n<chat_history>\n{gecmis}\n</chat_history>\n\n"
        f"<key_facts>\n{bilgiler}\n</key_facts>\n\n<source_excerpts>\n{kaynaklar}\n</source_excerpts>\n\n"
        f"<answer>\n{cevap.metin}\n</answer>"
    )
    yanit = istemci.beta.messages.parse(
        model=model,
        max_tokens=16000,
        system=HAKEM_TALIMATI,
        messages=[{"role": "user", "content": icerik}],
        output_format=HakemKarari,
        # Hakem bir isteği güvenlik nedeniyle reddederse aynı istek başka bir modelde tekrarlanır.
        betas=["server-side-fallback-2026-07-01"],
        extra_body={"fallbacks": "default"},
    )
    kullanim = {"girdi": yanit.usage.input_tokens, "cikti": yanit.usage.output_tokens, "durma": yanit.stop_reason}
    if yanit.stop_reason == "refusal":
        return None, kullanim
    return yanit.parsed_output, kullanim


def bir_deneme(istemci: anthropic.Anthropic, model: str, butce: Butce, soru: dict, tekrar_no: int) -> dict:
    sonuc = {"id": soru["id"], "tur": soru["tur"], "dil": soru["dil"], "tekrar": tekrar_no, "kullanim": None}
    bos = {"anahtar_kapsam": None, "tam_dogru": None, "sadik": None, "dil_dogru": None, "reddetti": None}
    try:
        cevap = cevap_uret(soru["soru"], soru["gecmis"])
    except (openai.APIError, AzureError) as e:  # tek bir servis hatası bütün çalıştırmayı düşürmesin
        sonuc.update(bos, cevap=None, hakem=f"cevap üretilemedi: {type(e).__name__}")
        return sonuc
    sonuc.update(
        cevap=cevap.metin, sorgu=cevap.sorgu,
        dil_dogru=cevap_dili(cevap.metin) == soru["dil"],
        reddetti=reddetti_mi(cevap.metin),
    )
    if sonuc["reddetti"]:
        # Ret cümlesinde değerlendirilecek bilgi ya da iddia yok; hakeme gerek yok.
        sonuc.update(anahtar_kapsam=0.0, tam_dogru=False, sadik=True, hakem=None)
        return sonuc
    if not butce.izin_var():
        sonuc.update(anahtar_kapsam=None, tam_dogru=None, sadik=None, hakem="bütçe aşıldı")
        return sonuc
    try:
        karar, kullanim = hakeme_sor(istemci, model, soru, cevap)
    except anthropic.APIError as e:
        sonuc.update(anahtar_kapsam=None, tam_dogru=None, sadik=None, hakem=f"hakem hatası: {type(e).__name__}")
        return sonuc
    butce.ekle(kullanim["girdi"], kullanim["cikti"])
    sonuc["kullanim"] = kullanim
    if karar is None:
        sonuc.update(anahtar_kapsam=None, tam_dogru=None, sadik=None, hakem="hakem reddetti")
        return sonuc
    var = [k.cevapta_var for k in karar.anahtar_bilgiler]
    sonuc.update(
        anahtar_kapsam=(sum(var) / len(var)) if var else None,
        tam_dogru=bool(var) and all(var),
        sadik=not karar.desteklenmeyen_iddialar,
        hakem=karar.model_dump(),
    )
    return sonuc


def oran(degerler: list) -> str:
    degerler = [d for d in degerler if d is not None]
    return f"{sum(degerler) / len(degerler):.0%}" if degerler else "-"


def ozet(sonuclar: list[dict], model: str, butce: Butce) -> None:
    gruplar = defaultdict(list)
    for s in sonuclar:
        gruplar[(s["tur"], s["dil"])].append(s)

    print(f"\n{'Tür':11} {'Dil':3} {'n':>3}  {'tam doğru':>9} {'bilgi kapsamı':>13} {'sadık':>6} {'yanlış ret':>10} {'dil doğru':>9}")
    for (tur, dil), g in sorted(gruplar.items()):
        if tur == "cevapsiz":
            continue
        print(f"{tur:11} {dil:3} {len(g):>3}  {oran([s['tam_dogru'] for s in g]):>9} "
              f"{oran([s['anahtar_kapsam'] for s in g if not s['reddetti']]):>13} "
              f"{oran([s['sadik'] for s in g if not s['reddetti']]):>6} "
              f"{oran([s['reddetti'] for s in g]):>10} {oran([s['dil_dogru'] for s in g]):>9}")
    cevaplanabilir = [s for s in sonuclar if s["tur"] != "cevapsiz"]
    print(f"{'TOPLAM':15} {len(cevaplanabilir):>3}  {oran([s['tam_dogru'] for s in cevaplanabilir]):>9} "
          f"{oran([s['anahtar_kapsam'] for s in cevaplanabilir if not s['reddetti']]):>13} "
          f"{oran([s['sadik'] for s in cevaplanabilir if not s['reddetti']]):>6} "
          f"{oran([s['reddetti'] for s in cevaplanabilir]):>10} {oran([s['dil_dogru'] for s in cevaplanabilir]):>9}")

    cevapsiz = [s for s in sonuclar if s["tur"] == "cevapsiz"]
    if cevapsiz:
        cevap_verilen = [s for s in cevapsiz if not s["reddetti"]]
        print(f"\nCevapsız sorular: doğru ret {oran([s['reddetti'] for s in cevapsiz])} ({len(cevapsiz)} cevap); "
              f"reddetmeyenlerde kaynağa sadık {oran([s['sadik'] for s in cevap_verilen])}")

    kullanim = [s["kullanim"] for s in sonuclar if s.get("kullanim")]
    girdi = sum(k["girdi"] for k in kullanim)
    cikti = sum(k["cikti"] for k in kullanim)
    print(f"\nHakem ({model}): {len(kullanim)} çağrı, {girdi:,} girdi + {cikti:,} çıktı token, "
          f"tahmini ${butce.harcanan:.2f} / bütçe ${butce.sinir:.2f} "
          f"(çağrı başına ${butce.harcanan / max(len(kullanim), 1):.3f})")
    sorunlar = [(s["id"], s["tekrar"], s["hakem"]) for s in sonuclar if isinstance(s.get("hakem"), str)]
    for sid, tekrar, sorun in sorunlar:
        print(f"  değerlendirilemedi: {sid} #{tekrar} ({sorun})")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ayar = argparse.ArgumentParser()
    ayar.add_argument("--tekrar", type=int, default=3, help="her soru kaç kez sorulsun (cevaplar rastgele)")
    ayar.add_argument("--sinir", type=int, default=None, help="sadece ilk N soru (deneme için)")
    ayar.add_argument("--hakem", choices=list(HAKEM_FIYATLARI), default="claude-sonnet-5-5")
    ayar.add_argument("--butce", type=float, default=2.50, help="hakem harcaması üst sınırı ($)")
    arg = ayar.parse_args()

    satirlar = (KLASOR / "sorular.jsonl").read_text(encoding="utf-8").splitlines()
    sorular = [json.loads(s) for s in satirlar if s.strip()][: arg.sinir]
    istemci = anthropic.Anthropic()
    butce = Butce(arg.butce, HAKEM_FIYATLARI[arg.hakem])
    isler = [(s, t) for s in sorular for t in range(1, arg.tekrar + 1)]

    with ThreadPoolExecutor(max_workers=ESZAMANLI) as havuz:
        sonuclar = list(havuz.map(lambda is_: bir_deneme(istemci, arg.hakem, butce, *is_), isler))

    for s in sonuclar:
        if isinstance(s.get("hakem"), str):
            durum = "-"
        else:
            durum = "RET" if s["reddetti"] else ("doğru" if s["tam_dogru"] else f"kapsam {s['anahtar_kapsam']:.0%}")
        print(f"{s['id']:22} #{s['tekrar']}  {durum:12} sadık={s['sadik']}  dil={'ok' if s['dil_dogru'] else 'YANLIŞ'}")
    ozet(sonuclar, arg.hakem, butce)

    cikti = KLASOR / "yerel" / f"cevaplar_{datetime.now(UTC):%Y%m%d_%H%M%S}.json"
    cikti.parent.mkdir(exist_ok=True)
    cikti.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAyrıntı: {cikti}")


if __name__ == "__main__":
    main()
