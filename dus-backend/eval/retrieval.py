"""Retrieval ölçümü: eval setindeki sorular için beklenen sayfa ilk k sonuçta mı?

dus-backend klasöründen çalıştırılır, .env'deki gerçek servisleri kullanır:
    python -m eval.retrieval

Maliyet: soru başına bir embedding, takip soruları için ek olarak bir kısa LLM çağrısı (sorgu
yeniden yazma). Sonuçların ayrıntısı eval/yerel/ altına yazılır (git'e girmez).
"""
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from app.rag_motoru import arama_sorgusu, gecmisi_cevir, retriever

KLASOR = Path(__file__).parent
KITAP_DILI = {
    "periodontoloji-4-sinif-ders-notlari-c3c3e164.pdf": "tr",
    "periodontoloji_ders_notu (1).pdf": "tr",
    "Clinical_Periodontology.pdf": "en",
    "preview-9781647240127_A39334500.pdf": "en",
}


def sorulari_oku() -> list[dict]:
    satirlar = (KLASOR / "sorular.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(s) for s in satirlar if s.strip()]


def olc(soru: dict) -> dict:
    sorgu = arama_sorgusu(soru["soru"], gecmisi_cevir(soru["gecmis"]))
    dokumanlar = retriever.invoke(sorgu)
    # Eval setinde sayfalar 1'den başlar (PDF görüntüleyici); indeks PyPDFLoader'ın 0'dan başlayan
    # numarasını saklar.
    getirilen = [(d.metadata["source"], d.metadata["page"] + 1) for d in dokumanlar]
    beklenen = {(k["dosya"], k["sayfa"]) for k in soru["beklenen_kaynaklar"]}
    sira = next((i for i, g in enumerate(getirilen, start=1) if g in beklenen), None)
    return {
        "id": soru["id"],
        "tur": soru["tur"],
        "dil": soru["dil"],
        "sorgu": sorgu,
        "getirilen": getirilen,
        "sira": sira,
        "getirilen_tr": sum(KITAP_DILI.get(d) == "tr" for d, _ in getirilen),
        "getirilen_en": sum(KITAP_DILI.get(d) == "en" for d, _ in getirilen),
    }


def ozet(sonuclar: list[dict], k: int) -> None:
    gruplar = defaultdict(list)
    for s in sonuclar:
        gruplar[(s["tur"], s["dil"])].append(s)
        gruplar[("TOPLAM", "")].append(s)

    print(f"\n{'Tür':12} {'Dil':4} {'n':>3} {'hit@' + str(k):>7} {'MRR':>6}   getirilen parçalar (TR / EN)")
    for (tur, dil), grup in sorted(gruplar.items(), key=lambda x: (x[0][0] == "TOPLAM", x[0])):
        n = len(grup)
        hit = sum(s["sira"] is not None for s in grup)
        mrr = sum(1 / s["sira"] for s in grup if s["sira"]) / n
        tr = sum(s["getirilen_tr"] for s in grup)
        en = sum(s["getirilen_en"] for s in grup)
        print(f"{tur:12} {dil:4} {n:>3} {hit:>3}/{n:<3} {mrr:>6.2f}   {tr:>3} / {en:<3}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    # Cevapsız sorularda bulunacak sayfa yok; onlar cevap ölçümünde (LLM hakem) değerlendirilir.
    sorular = [s for s in sorulari_oku() if s["cevaplanabilir"]]
    sonuclar = []
    for soru in sorular:
        sonuc = olc(soru)
        sonuclar.append(sonuc)
        durum = f"#{sonuc['sira']}" if sonuc["sira"] else "yok"
        print(f"{soru['id']:22} {soru['tur']:10} {soru['dil']}  {durum:4}  TR {sonuc['getirilen_tr']} / EN {sonuc['getirilen_en']}")

    k = len(sonuclar[0]["getirilen"]) if sonuclar else 0
    ozet(sonuclar, k)

    cikti = KLASOR / "yerel" / f"retrieval_{datetime.now(UTC):%Y%m%d_%H%M%S}.json"
    cikti.parent.mkdir(exist_ok=True)
    cikti.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nAyrıntı: {cikti}")


if __name__ == "__main__":
    main()
