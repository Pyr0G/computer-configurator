"""Autotest silnika. Uruchom: python se/test_silnik.py  (plik kawa.json musi leżeć w wiedza/)."""
from pathlib import Path

from silnik import wczytaj_baze, wnioskuj_w_przod, wnioskuj_wstecz

baza = wczytaj_baze(Path(__file__).parent.parent / "wiedza" / "kawa.json")

PRZYPADKI = [
    ({"temperatura": 18, "pora_dnia": "rano", "dodatek": "brak", "kofeina_ok": "tak"}, "espresso", ["R2", "R4", "R15"]),
    ({"temperatura": 30, "pora_dnia": "popołudnie", "dodatek": "czekolada", "kofeina_ok": "tak"}, "chocolate cold coffee", None),
    ({"temperatura": 10, "pora_dnia": "wieczór", "dodatek": "mleko", "kofeina_ok": "tak"}, "latte bezkofeinowe", None),
    ({"temperatura": 25, "pora_dnia": "rano", "dodatek": "mleko", "kofeina_ok": "nie"}, "mrożona kawa bezkofeinowa", None),
    ({"temperatura": 22, "pora_dnia": "popołudnie", "dodatek": "mleko", "kofeina_ok": "tak"}, "latte", None),
]

ok = 0
for wejscie, oczekiwane, oczekiwany_slad in PRZYPADKI:
    fakty, slad = wnioskuj_w_przod(baza, wejscie)
    w_przod_ok = fakty.get("kawa") == oczekiwane and (oczekiwany_slad is None or slad == oczekiwany_slad)

    zadane = []
    def zapytaj(atrybut, powod):
        zadane.append(atrybut)
        return wejscie[atrybut]
    wstecz = wnioskuj_wstecz(baza, "kawa", {}, zapytaj, [])
    wstecz_ok = wstecz == oczekiwane and len(zadane) == len(set(zadane))

    status = "OK " if w_przod_ok and wstecz_ok else "BŁĄD"
    ok += w_przod_ok and wstecz_ok
    print(f"[{status}] {wejscie} -> w przód: {fakty.get('kawa')}, wstecz: {wstecz}, pytań: {len(zadane)}")

print(f"\nZaliczone przypadki: {ok}/{len(PRZYPADKI)}")
