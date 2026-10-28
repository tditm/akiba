# Akiba – Chess Arbiter Monitoring System
## Dokumentacja Użytkownika (w wersji 1.0)

---

## Spis treści

1. [Wprowadzenie](#wprowadzenie)
2. [Źródła Danych](#źródła-danych)
3. [Claims (Roszczenia)](#claims-roszczenia)
4. [Reminders (Przypomnienia)](#reminders-przypomnienia)
5. [Różnice między Claims i Reminders](#różnice-między-claims-i-reminders)
6. [System ACK (Acknowledgment)](#system-ack-acknowledgment)
7. [Powiadomienia](#powiadomienia)
8. [Pozostałe Przyciski](#pozostałe-przyciski)
9. [Board Viewer – Wizualizacja Partii](#board-viewer–wizualizacja-partii)

---

## Wprowadzenie

**Akiba** to Chess Arbiter Monitoring System dla sędziów szachowych, który automatycznie analizuje partie szachowe i wykrywa sytuacje związane z roszczeniami (claims) oraz przypomnieniami (reminders). Program obsługuje partie z różnych źródeł: plików lokalnych, stron internetowych oraz platformy LiveChessCloud.

---

## Źródła Danych

Aplikacja obsługuje **trzy typy źródeł**, które można dodać w oknie "Add Sources". **Wszystkie źródła mają funkcjonalność LIVE** - program monitoruje je co 4 sekundy:

### 1. Web URL (Opcja 0)
- Adres URL do pliku PGN na stronie internetowej  
- Przykład: `https://example.com/tournament/games.pgn`
- **LIVE:** Program pobiera plik **co 4 sekundy** w czasie rzeczywistym
- Idealne dla turniejów live, gdzie strona jest aktualizowana na bieżąco

### 2. Local File (Opcja 1)
- Ścieżka do pliku PGN na komputerze
- Przykład: `C:\Tournaments\my_games.pgn`
- **LIVE:** Program sprawdza rozmiar pliku **co 4 sekundy** - jeśli się zmieni, odczytuje ponownie
- Idealne gdy zewnętrzny program zapisuje partie do pliku w czasie rzeczywistym

### 3. LiveChessCloud Live (Opcja 2)
- Link do turnieju na platformie LiveChessCloud
- Przykład: `https://view.livechesscloud.com/#abcd1234-....`
- **LIVE:** Program pobiera partie z turnieju **co 4 sekundy** w czasie rzeczywistym (polling)
- **Numer rundy:** Domyślnie runda 1, można wybrać dowolną rundę (1-9999)
- Każda runda jest zapisywana w osobnym pliku PGN

**Podsumowanie LIVE:** Wszystkie źródła są monitorowane co 4 sekundy - Web URL i LiveChessCloud pobierają dane ponownie, Local File sprawdza czy rozmiar się zmienił.

---

## Claims (Roszczenia)

**Claims** to sytuacje, w których gracz może **złożyć oficjalne roszczenie** zgodnie z przepisami FIDE. Program automatycznie wykrywa następujące typy claims:

### Rodzaje Claims

| Typ Roszczenia | Opis | Kiedy się pojawia |
|----------------|------|-------------------|
| **3-fold repetition** | Trzykrotne powtórzenie pozycji | Gdy ta sama pozycja na szachownicy występuje po raz trzeci |
| **5-fold repetition** | Pięciokrotne powtórzenie pozycji | Gdy ta sama pozycja na szachownicy występuje po raz piąty |
| **50-move rule** | Zasada 50 ruchów | Gdy 50 ruchów minęło bez ruchu pionem i bez bicia (claimable draw) |
| **75-move rule** | Zasada 75 ruchów | Gdy 75 ruchów minęło bez ruchu pionem i bez bicia (automatyczny koniec gry) |
| **Stalemate** | Pat | Gdy gracz nie ma legalnego ruchu, ale nie jest w szachu |
| **Checkmate** | Mata | Gdy gracz jest w szach-macie |
| **Dead position** | Pozycja martwa | Gdy żaden z graczy nie może dać mata (np. król vs król) |

### Jak działa wykrywanie Claims?
- Program skanuje partie **ruch po ruchu**
- Każde roszczenie jest rejestrowane z:
  - Numerem stołu (board number)
  - Nazwami graczy
  - Numerem ruchu, gdy roszczenie powstało
  - Komentarzem wyjaśniającym (np. "First counting move: X")

---

## Reminders (Przypomnienia)

**Reminders** to **ostrzeżenia informacyjne**, które pomagają sędziemu monitorować sytuacje w turnieju. Nie są to oficjalne roszczenia, ale warto o nich wiedzieć.

### Rodzaje Reminders

| Typ Przypomnienia | Opis | Kiedy się pojawia |
|-------------------|------|-------------------|
| **2-fold repetition** | Dwukrotne powtórzenie pozycji (ostrzeżenie przed 3-fold) | Gdy ta sama pozycja występuje po raz drugi – **ostrzeżenie:** "uważaj, zaraz może być 3-fold claim" |
| **45-move reminder** | Przypomnienie przed zasadą 50-ruchową | Gdy 45 ruchów minęło bez ruchu pionem i bez bicia – **ostrzeżenie:** "za 5 ruchów będzie można złożyć 50-move claim" |
| **Time control** | Kontrola czasu nadchodząca | Osiągnięcie punktu kontrolnego po xx ruchach – sędzia powinien być przy szachownicy (np. wykonali ruch 38, za dwa ruchy kontrola 40) |
| **Low on time** | Niski czas | Gracz ma mniej sekund niż ustawiony próg (niedoczas) – **ostrzeżenie:** "zawodnik może zaraz przekroczyć czas" |
| **Flag fall reminder** | Flaga opadła (koniec czasu) | Gdy czas gracza osiągnął 0:00:00 – **alert:** "sprawdź czy flaga nie opadła na tej szachownicy!" |
| **First illegal move** | Pierwszy nielegalny ruch w partii | Wykryto nielegalny ruch w analizie PGN – **alert:** "natychmiast sprawdź sytuację na szachownicy - może być błąd w wykonaniu ruchu lub zapisie" |
| **Scoresheet change** | Zmiana zapisu partii | Osiągnięcie punktu kontrolnego po xx ruchach (np. 60) – **ostrzeżenie:** "przynieś nowe zapisy" |
| **Sofia rule violation** | Naruszenie reguł Sofii | Remis zgłoszony przed ustawionym limitem ruchu (domyślnie 30) – po 30. ruchu remis nie narusza przepisów |

### Ważne Informacje:
- **2-fold:** Ostrzeżenie, że pozycja powtórzyła się dwukrotnie. Sędzia powinien zwrócić uwagę - zawodnik może wkrótce zgłosić 3-fold repetition.
- **45-move reminder:** To nie jest sama zasada 50-ruchowa, ale ostrzeżenie, aby przygotować się na nią. Po 45 ruchach bez bicia i ruchu pionem, tylko 5 ruchów do claimable draw.
- **Time control:** Przypomnienie o nadchodzącej kontroli czasu. Jeśli kontrola jest po 40 ruchach a obecnie jest ruch 38, sędzia powinien być gotowy!
- **Low on time:** Oznacza "niedoczas" - gracz ma mniej sekund niż ustawiony próg. Sędzia powinien sprawdzić czy zawodnik może zaraz przekroczyć czas.
- **Flag fall:** Czas się skończył (0:00:00). To jest co innego niż "low on time" - to oznacza, że zegar faktycznie pokazał zero!
- **Illegal move:** Program wykrył nielegalny ruch w analizie PGN. Natychmiast sprawdź czy nie było błędu w wykonaniu ruchu lub notacji.
- **Scoresheet change:** Przypomnienie, że gracze są w trakcie wypełniania zapisów (zazwyczaj 60 pól). Sędzia powinien przynieść nowy papier.
- **Sofia rule:** Tylko zgłasza propozycje remisu przed 30. ruchem. Propozycje remisu po 30. ruchu nie naruszają przepisów.

---

## Różnice między Claims i Reminders

| Cecha | Claims (Roszczenia) | Reminders (Przypomnienia) |
|-------|---------------------|---------------------------|
| **Status** | **OBLIGATORYJNE** - nie można wyłączyć, zawsze aktywny | **OPCJONALNE** - można włączyć/wyłączyć w ustawieniach |
| **Cel** | Wykrywanie oficjalnych roszczeń zgodnie z przepisami FIDE | Pomoc sędziemu w monitorowaniu sytuacji na turnieju |
| **Konsekwencje** | Większość powoduje natychmiastowy koniec gry (checkmate, stalemate, dead position, 75-move, non-legal). 3-fold i 50-move wymagają weryfikacji sędziego z udziałem zawodników. | Tylko informacja ostrzegawcza - nie kończy gry automatycznie |
| **Wyłączalność** | ❌ NIE - claimsy są zawsze aktywne | ✅ TAK - można dezaktywować reminders |

### Kluczowe różnice w praktyce:

**Claims (zawsze aktywne):**
- Wykrywają sytuacje kończące partię zgodnie z przepisami FIDE
- Nie można ich wyłączyć - są integralną częścią systemu monitorowania
- Przykłady: Checkmate, Stalemate, Dead Position, 75-move rule, 3-fold repetition, 50-move rule

**Reminders (opcjonalne):**
- Pomagają sędziemu być przygotowanym na nadchodzące sytuacje
- Można je wyłączyć jeśli nie są potrzebne w danym turnieju
- Przykłady: 45-move reminder (ostrzeżenie przed 50-moves), Time control approaching, Low on time, Scoresheet change

### Przykład użycia:

| Sytuacja | Typ | Działanie sędziego |
|----------|-----|-------------------|
| Zawodnik zgłasza remis po powtórzeniu pozycji (3-fold) | **Claim** | Sprawdź pozycję, potwierdź lub odrzuć roszczenie |
| Program pokazuje "45 moves played" | **Reminder** | Bądź czujny, za 5 ruchów zawodnik będzie mógł zgłosić remis z 50-move rule |
| Zawodnik ma na zegarze mniej czasu niż próg (np. <30s) | **Reminder** | Podejdź do stołu - zawodnik może niedługo przekroczyć czas |
| Wykryto nielegalny ruch w partii | **Claim** | Sprawdź co się stało - zawodnik mógł pomylić ruch lub jest błąd w zapisie PGN |

---

## System ACK (Acknowledgment)

System ACK służy do **oznaczania roszczeń jako "rozstrzygnięte"**.

### Jak działa?
1. Gdy roszczenie zostaje wykryte, pojawia się w tabeli claims
2. Po rozpatrzeniu sprawy możesz oznaczyć je jako **ACK** (acknowledged)
3. Roścenie ACK pozostaje w systemie dla historii i można je przywrócić przyciskiem **"Restore Resolved Claims"**

### Przykład użycia:
- Zawodnicy zgłosili 3-fold repetition → sędzia przychodzi z blankietami zapisu, rozstrzyga sprawę → oznaczasz jako ACK ✅
- Zawodnicy minęli kontrolę czasu (50-move) bez złożenia roszczenia → sprawa nieaktualna → oznaczasz jako ACK ✅  
- Zawodnik nie złożył reklamacji na podstawie 3-fold repetition w odpowiednim momencie → sprawa nieaktualna → oznaczasz jako ACK ✅

**Uwaga:** Roścenia ACK można przywrócić przyciskiem **"Restore Resolved Claims"** jeśli okaże się, że jednak wymagają uwagi.

---

## Powiadomienia

Aplikacja posiada system **powiadomień systemowych** Windows/Mac:

### Jak zarządzać powiadomieniami?
- Menu **Options → Enable Windows/Mac notifications** (domyślnie włączone)
- Po wyłączeniu żadne claims i reminders nie wyświetlą się jako powiadomienie

### Rodzaje powiadomień:
- Low on time reminder
- Flag fall reminder  
- Time control approaching
- Scoresheet change warning
- Sofia rule violation

---

## Pozostałe Przyciski

W głównym oknie znajdują się trzy główne przyciski:

### Start (Niebieski)
- **Funkcja:** Rozpoczyna skanowanie partii i pobieranie danych ze źródeł
- Dla wszystkich źródeł uruchamia automatyczne odświeżanie co 4 sekundy

### Stop (Czerwony)  
- Przerywa skanowanie. Wpisy w tabeli ze statusem ACK nie pojawią się ponownie po naciśnieciu start.

---

## Board Viewer – Wizualizacja Partii

Board Viewer to główny interfejs do przeglądania i analizowania partii. Oto jak interpretować oznaczenia wizualne:

### Kolory i Oznaczenia w Board Viewer

| Element | Kolor/Znaczenie | Kiedy się pojawia |
|---------|-----------------|-------------------|
| **Zielona ramka szachownicy** | Pozycja powtarza się po raz trzeci lub piąty (3-fold/5-fold repetition snapshot) | Gdy pozycja na szachownicy występuje po raz 3-ci lub 5-ty – kluczowa pozycja dla roszczenia o powtórzenie |
| **Czerwona ramka szachownicy** | Nielegalny ruch wykryty w partii | Tylko wtedy, gdy jesteś na ostatnim poprawnym ruchu przed nielegalnym ruchem |
| **Żółte podświetlenie szachownicy** | Ostatni wykonany ruch | Zawsze po wykonaniu ruchu – ostatni ruch jest zaznaczony żółtym kolorem pola docelowego |
| **Żółte tło ruchu w zapisie PGN** | Aktualnie zaznaczony ruch | Po kliknięciu na konkretny ruch w zapisie poniżej szachownicy |

### Gdzie są pokazywane informacje?

#### 1. Szachownica (lewa strona)
- Pokazuje aktualną pozycję po wybranym ruchu
- **Zielona ramka** = 3-fold/5-fold repetition snapshot
- **Czerwona ramka** = nielegalny ruch w partii (oglądanie ostatniej poprawnej pozycji)

#### 2. Zapis partii PGN (prawa strona pod szachownicą)
- Lista wszystkich ruchów w formacie algebraicznym
- Kliknięcie na dowolnym ruchu przenosi szachownicę do tej pozycji
- **Żółte tło** = aktualnie zaznaczony ruch

#### 3. Informacje o czasie (pod nazwami graczy)
- Format: `Nazwisko (Czas)` 
- Pokazuje czas pozostały po **ostatnim ruchu** danego gracza (statyczny)
- Przykład: `Karpov, A. (00:15:32) – Kasparov, G. (00:42:18)`
- **Czas namysłu w ostatnim ruchu:** Pokazuje ile czasu gracz myślał nad swoim ostatnim ruchem

### Nawigacja w Board Viewer

#### Przyciski nawigacyjne:
| Przycisk | Funkcja |
|----------|---------|
| **⏮** | Pierwsza gra w liście / Początek obecnej gry |
| **◀** | Poprzednia gra / Previous ruch w grze |
| **▶** | Następna gra / Next ruch w grze |
| **⏭** | Ostatnia gra w liście / Koniec obecnej gry |

#### Nawigacja klawiaturą:
- Możesz używać strzałek **lewo/prawo** do nawigacji między partiami (gdy lista jest aktywna) lub ruchami (gdy szachownica/PGN jest aktywna)
- Strzałki **góra/dół** do przewijania listy partii

### Filtrowanie gier

- **Pole wyszukiwania:** Wpisz nazwisko gracza lub numer stołu (np. "12")
- **Checkbox "Show only active games":** Pokazuje tylko partie zakończone wynikiem `*` (trwające)

---

## Podsumowanie

Akiba to potężne narzędzie dla sędziów szachowych, które:
- ✅ Automatycznie wykrywa roszczenia i przypomnienia w partiach
- ✅ Obsługuje wiele źródeł danych jednocześnie (URL, lokalne pliki, LiveChessCloud)
- ✅ Łączy partie z różnych źródeł do jednego pliku PGN
- ✅ Wizualizuje kluczowe pozycje (3-fold/5-fold snapshots, nielegalne ruchy)
- ✅ Pozwala zarządzać rozstrzygniętymi roszczeniami przez system ACK
- ✅ Posiada powiadomienia systemowe dla ważnych zdarzeń

W razie pytań lub problemów, sprawdź logi aplikacji w katalogu `%APPDATA%\Akiba\`.

### Zbieranie Danych (Beacon)

Akiba jest wysyłanie anonimowe dane do Google Sheets w celu statystyk użytkowania. Każde kliknięcie przycisku "Start" powoduje wysłanie jednego wpisu z:
- **Device ID** - unikalny, anonimowy hash (nie można powiązać z Tobą)
- **Wersja aplikacji** - np. "1.0"  
- **System operacyjny** - np. "Windows 10"

Dane są zbierane wyłącznie w celach statystycznych (ile osób używa programu, jakie wersje). Nie zbieramy żadnych danych osobowych ani informacji o partiach szachowych.

---