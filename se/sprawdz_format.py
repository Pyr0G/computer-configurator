"""Sprawdzenie FORMATU bazy wiedzy (spotkanie 2) — gotowe narzędzie, nic tu nie uzupełniasz.

Uruchom z katalogu głównego repozytorium:
    python se/sprawdz_format.py wiedza/moja_dziedzina.json

Program sprawdza trzy rzeczy:
  1. składnię JSON (przecinki, cudzysłowy, nawiasy),
  2. kształt pliku: czy każdy atrybut i każda reguła mają wymagane pola właściwego typu,
  3. wymagania zadania Z2 (liczba reguł, trzy poziomy łańcucha, metafora i coto).
Nie sprawdza spójności wiedzy (sprzeczne lub zbędne reguły, wartości spoza listy, nieużywane
atrybuty) — to zadanie weryfikatora, który napiszesz na spotkaniu 3.
"""
import json
import re
import sys
from pathlib import Path

TYPY = {"liczba", "wybor", "wniosek"}
POROWNANIA = {">", ">=", "<", "<="}
POLA_BAZY = {"nazwa", "cel", "atrybuty", "reguly"}
POLA_ATRYBUTU = {"liczba": {"typ", "pytanie", "zakres"}, "wybor": {"typ", "pytanie", "wartosci"}, "wniosek": {"typ", "wartosci"}}
POLA_REGULY = {"id", "jesli", "to", "metafora", "coto"}
NAZWA = re.compile(r"^[a-z][a-z0-9_]*$")
MIN_REGUL = 20
MIN_POZIOMOW = 3


def jest_liczba(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def literowka(pole, znane):
    """Podpowiedź dla pola z polskim znakiem albo wielką literą, np. „wartości” → „wartosci”."""
    zamiana = str.maketrans("ąćęłńóśźż", "acelnoszz")
    kandydat = pole.lower().translate(zamiana)
    return f" — czy chodziło o '{kandydat}'?" if kandydat in znane and kandydat != pole else ""


def sprawdz_atrybuty(baza, raport):
    atrybuty = baza.get("atrybuty")
    if not isinstance(atrybuty, dict) or not atrybuty:
        raport.append(("BŁĄD", "'atrybuty' musi być niepustym słownikiem {nazwa: opis}"))
        return {}
    for nazwa, opis in atrybuty.items():
        gdzie = f"atrybut '{nazwa}'"
        if not NAZWA.match(nazwa):
            raport.append(("UWAGA", f"{gdzie}: nazwa powinna mieć tylko małe litery bez polskich znaków, cyfry i _ (np. pora_dnia)"))
        if not isinstance(opis, dict):
            raport.append(("BŁĄD", f"{gdzie}: opis musi być słownikiem, np. {{\"typ\": \"wybor\", ...}}"))
            continue
        typ = opis.get("typ")
        if typ not in TYPY:
            raport.append(("BŁĄD", f"{gdzie}: 'typ' musi być jednym z: liczba, wybor, wniosek (jest: {typ!r})"))
            continue
        for pole in opis:
            if pole not in POLA_ATRYBUTU[typ]:
                raport.append(("UWAGA", f"{gdzie}: pole '{pole}' nie jest używane przy typie {typ}{literowka(pole, POLA_ATRYBUTU[typ])}"))
        if typ in ("liczba", "wybor"):
            if not isinstance(opis.get("pytanie"), str) or not opis["pytanie"].strip():
                raport.append(("BŁĄD", f"{gdzie}: dana wejściowa musi mieć 'pytanie' (tekst pytania do użytkownika)"))
        if typ == "liczba":
            zakres = opis.get("zakres")
            if zakres is None:
                raport.append(("UWAGA", f"{gdzie}: podaj 'zakres': [min, max] — przyda się w interfejsie i generatorze danych"))
            elif not (isinstance(zakres, list) and len(zakres) == 2 and all(map(jest_liczba, zakres)) and zakres[0] < zakres[1]):
                raport.append(("BŁĄD", f"{gdzie}: 'zakres' musi mieć postać [min, max], dwie liczby bez cudzysłowu, min < max"))
        if typ in ("wybor", "wniosek"):
            wartosci = opis.get("wartosci")
            if not (isinstance(wartosci, list) and wartosci and all(isinstance(w, str) for w in wartosci)):
                poziom = "BŁĄD" if typ == "wybor" else "UWAGA"
                raport.append((poziom, f"{gdzie}: 'wartosci' musi być niepustą listą tekstów, np. [\"tak\", \"nie\"]"))
            elif len(set(wartosci)) != len(wartosci):
                raport.append(("BŁĄD", f"{gdzie}: lista 'wartosci' zawiera powtórzenia"))
    return atrybuty


def sprawdz_warunek(war, atrybuty, gdzie, raport):
    if not (isinstance(war, list) and len(war) == 3):
        raport.append(("BŁĄD", f"{gdzie}: warunek musi być trójką [atrybut, operator, wartość], jest: {war!r}"))
        return False
    atr, op, wart = war
    if not isinstance(atr, str) or not isinstance(op, str):
        raport.append(("BŁĄD", f"{gdzie}: w warunku {war!r} atrybut i operator muszą być tekstem"))
        return False
    typ = atrybuty.get(atr, {}).get("typ") if isinstance(atrybuty.get(atr), dict) else None
    if op in POROWNANIA:
        if not jest_liczba(wart):
            raport.append(("BŁĄD", f"{gdzie}: porównanie '{op}' wymaga liczby bez cudzysłowu, jest: {wart!r}"))
        if typ in ("wybor", "wniosek"):
            raport.append(("BŁĄD", f"{gdzie}: operator '{op}' działa tylko dla atrybutu typu liczba ('{atr}' ma typ {typ})"))
    elif typ == "liczba" and isinstance(wart, str):
        raport.append(("BŁĄD", f"{gdzie}: '{atr}' to liczba, a wartość {wart!r} jest tekstem — usuń cudzysłów"))
    return True


def sprawdz_reguly(baza, atrybuty, raport):
    reguly = baza.get("reguly")
    if not isinstance(reguly, list) or not reguly:
        raport.append(("BŁĄD", "'reguly' musi być niepustą listą reguł"))
        return []
    poprawne = []
    for nr, r in enumerate(reguly, start=1):
        if not isinstance(r, dict):
            raport.append(("BŁĄD", f"reguła nr {nr}: musi być słownikiem {{\"id\": ..., \"jesli\": ..., \"to\": ...}}"))
            continue
        gdzie = f"reguła {r.get('id', f'nr {nr}')}"
        ok = True
        for pole in r:
            if pole not in POLA_REGULY:
                raport.append(("UWAGA", f"{gdzie}: nieznane pole '{pole}'{literowka(pole, POLA_REGULY)}"))
        if not isinstance(r.get("id"), str) or not r["id"].strip():
            raport.append(("BŁĄD", f"{gdzie}: brak 'id' (tekst, np. \"R1\")"))
        jesli = r.get("jesli")
        if not isinstance(jesli, list) or not jesli:
            raport.append(("BŁĄD", f"{gdzie}: 'jesli' musi być niepustą listą warunków"))
            ok = False
        elif len(jesli) == 3 and isinstance(jesli[0], str):
            raport.append(("BŁĄD", f"{gdzie}: pojedynczy warunek też musi być w liście: \"jesli\": [{json.dumps(jesli, ensure_ascii=False)}]"))
            ok = False
        else:
            ok = all([sprawdz_warunek(w, atrybuty, gdzie, raport) for w in jesli]) and ok
        to = r.get("to")
        if not (isinstance(to, list) and len(to) == 2 and isinstance(to[0], str)):
            raport.append(("BŁĄD", f"{gdzie}: 'to' musi być parą [atrybut, wartość], np. [\"kawa\", \"latte\"]"))
            ok = False
        elif isinstance(atrybuty.get(to[0]), dict) and atrybuty[to[0]].get("typ") in ("liczba", "wybor"):
            raport.append(("BŁĄD", f"{gdzie}: reguła ustala '{to[0]}', który jest daną wejściową — wniosek musi mieć typ 'wniosek'"))
        if not isinstance(r.get("metafora"), str) or not r["metafora"].strip():
            raport.append(("UWAGA", f"{gdzie}: brak 'metafora' (zdanie: dlaczego ta reguła ma sens)"))
        if ok and to[0] == baza.get("cel") and not str(r.get("coto", "")).strip():
            raport.append(("UWAGA", f"{gdzie}: reguła daje decyzję końcową, a nie ma 'coto' (opis: co to jest?)"))
        if ok:
            poprawne.append(r)
    return poprawne


def poziomy(baza, reguly):
    """Najdłuższy łańcuch atrybutów: dana wejściowa = 1, wniosek = 1 + najwyższy poziom jego przesłanek."""
    pamiec = {}

    def poziom(atr, w_toku=()):
        if atr in pamiec:
            return pamiec[atr]
        if atr in w_toku:
            return 0                                   # cykl — oceni go weryfikator na spotkaniu 3
        ustalajace = [r for r in reguly if r["to"][0] == atr]
        wynik = 1 if not ustalajace else 1 + max(
            max(poziom(w[0], w_toku + (atr,)) for w in r["jesli"]) for r in ustalajace)
        pamiec[atr] = wynik
        return wynik

    return poziom(baza.get("cel"))


def sprawdz(sciezka):
    tekst = Path(sciezka).read_text(encoding="utf-8")
    try:
        baza = json.loads(tekst)
    except json.JSONDecodeError as e:
        print(f"[BŁĄD] Składnia JSON, linia {e.lineno}, kolumna {e.colno}: {e.msg}")
        print("       Najczęściej: przecinek po ostatnim elemencie, pojedyncze cudzysłowy, brak przecinka między")
        print("       elementami, komentarz w pliku. Szukaj błędu w tej linii albo tuż przed nią.")
        return 1
    if not isinstance(baza, dict):
        print("[BŁĄD] Plik musi zawierać jeden obiekt {...} z kluczami nazwa, cel, atrybuty, reguly")
        return 1

    raport = []
    for klucz in sorted(POLA_BAZY - baza.keys()):
        raport.append(("BŁĄD", f"brak klucza najwyższego poziomu '{klucz}'"))
    for klucz in sorted(baza.keys() - POLA_BAZY):
        raport.append(("UWAGA", f"nieznany klucz najwyższego poziomu '{klucz}'{literowka(klucz, POLA_BAZY)}"))
    atrybuty = sprawdz_atrybuty(baza, raport)
    cel = baza.get("cel")
    if isinstance(cel, str) and atrybuty:
        if cel not in atrybuty:
            raport.append(("BŁĄD", f"cel '{cel}' nie jest zadeklarowany w 'atrybuty'"))
        elif isinstance(atrybuty[cel], dict) and atrybuty[cel].get("typ") != "wniosek":
            raport.append(("BŁĄD", f"cel '{cel}' musi mieć typ 'wniosek' — decyzję ustalają reguły, o nią się nie pyta"))
    reguly = sprawdz_reguly(baza, atrybuty, raport)

    bledy = sum(1 for poziom_, _ in raport if poziom_ == "BŁĄD")
    for poziom_, komunikat in raport:
        print(f"[{poziom_}] {komunikat}")
    print(f"\nFormat — błędy: {bledy}, uwagi: {len(raport) - bledy}." if raport else "Format: bez błędów i uwag.")

    wszystkie = baza.get("reguly") if isinstance(baza.get("reguly"), list) else []
    lp = poziomy(baza, reguly) if reguly and isinstance(cel, str) else 0
    slowniki = [r for r in wszystkie if isinstance(r, dict)]
    decyzje = [r for r in slowniki if isinstance(r.get("to"), list) and r["to"][:1] == [cel]]
    wymagania = [
        (len(wszystkie) >= MIN_REGUL, f"co najmniej {MIN_REGUL} reguł (jest {len(wszystkie)})"),
        (lp >= MIN_POZIOMOW, f"łańcuch co najmniej {MIN_POZIOMOW} poziomów atrybutów: wejście → wniosek pośredni → cel (jest {lp})"),
        (bool(slowniki) and all(str(r.get("metafora", "")).strip() for r in slowniki), "pole 'metafora' w każdej regule"),
        (bool(decyzje) and all(str(r.get("coto", "")).strip() for r in decyzje), "pole 'coto' w każdej regule z decyzją końcową"),
    ]
    print("\nWymagania Z2:")
    for spelnione, opis in wymagania:
        print(f"  [{'TAK' if spelnione else 'NIE'}] {opis}")
    return 1 if bledy else 0


if __name__ == "__main__":
    plik = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "wiedza" / "moja_dziedzina.json"
    sys.exit(sprawdz(plik))
