from pathlib import Path
from silnik import wczytaj_baze, wnioskuj_w_przod, wnioskuj_wstecz

baza = wczytaj_baze(Path(__file__).parent.parent / "wiedza" / "konfigurator_komputera.json")

PRZYPADKI = [
    ({"zastosowanie": "gry", "mobilnosc": "stacjonarny", "priorytet": "wydajnosc", "budzet": 3000}, "tani i wydajny komputer stacjonarny do gier", ["R1", "R4"]),
    ({"zastosowanie": "biuro", "mobilnosc": "przenosny", "budzet": 2000}, "tani laptop do biura", ["R1", "R25"]),
    ({"zastosowanie": "gry", "mobilnosc": "stacjonarny", "priorytet": "wydajnosc", "budzet": 3500}, "tani i wydajny komputer stacjonarny do gier", ["R1", "R4"]),
    ({"zastosowanie": "gry", "mobilnosc": "stacjonarny", "priorytet": "wydajnosc", "budzet": None}, None, []),
    ({"zastosowanie": "gry", "mobilnosc": "stacjonarny", "priorytet": "cisza", "budzet": 3000}, "tani i cichy komputer stacjonarny do gier", ["R1", "R7"]),
]

ok = 0
for nr, (wejscie, oczekiwane, oczekiwany_slad) in enumerate(PRZYPADKI, start=1):
    if nr == 5:
        r4 = next(r for r in baza["reguly"] if r["id"] == "R4")
        r4["jesli"] = [w for w in r4["jesli"] if w[0] != "priorytet"]
        baza["reguly"].remove(r4)
        baza["reguly"].append(r4)
    fakty, slad = wnioskuj_w_przod(baza, wejscie)
    w_przod_ok = fakty.get("konfiguracja") == oczekiwane and (oczekiwany_slad is None or slad == oczekiwany_slad)

    zadane = []
    def zapytaj(atrybut, powod):
        zadane.append(atrybut)
        return wejscie[atrybut]
    wstecz = wnioskuj_wstecz(baza, "konfiguracja", {}, zapytaj, [])
    wstecz_ok = wstecz == oczekiwane and len(zadane) == len(set(zadane))

    status = "OK " if w_przod_ok and wstecz_ok else "BŁĄD"
    ok += w_przod_ok and wstecz_ok
    print(f"[{status}] {wejscie} -> w przód: {fakty.get('konfiguracja')}, wstecz: {wstecz}, pytań: {len(zadane)}")

print(f"\nZaliczone przypadki: {ok}/{len(PRZYPADKI)}")