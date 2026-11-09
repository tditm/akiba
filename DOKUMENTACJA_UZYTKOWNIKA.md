# Akiba – Chess Arbiter Monitoring System
## Dokumentacja Użytkownika (Wersja 1.1)

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
10. [Analiza Fair-Play](#analiza-fair-play)

---

## Wprowadzenie

**Akiba** to system monitorowania dla sędziów szachowych, który automatycznie analizuje partie szachowe w czasie rzeczywistym i ostrzega sędziów o ważnych sytuacjach wymagających uwagi. Traktuj go jako niezależne narzędzie, oparte na live transmisjach szachowych, które pomaga sędziom podejmować świadome decyzje podczas turniejów.

---

## Źródła Danych

Aplikacja obsługuje **trzy typy źródeł**, które można dodać w oknie dialogowym "Add Sources". **Wszystkie źródła mają funkcjonalność LIVE** - program monitoruje je co 4 sekundy:

### 1. Web URL
- Adres URL do pliku PGN na stronie internetowej  
- Przykład: `https://example.com/tournament/games.pgn`
- **LIVE:** Program pobiera plik **co 4 sekundy** w czasie rzeczywistym
- Idealne dla live turniejów, gdzie strona jest aktualizowana ciągle

### 2. Local File
- Ścieżka do pliku PGN na Twoim komputerze
- Przykład: `C:\Tournaments\my_games.pgn`
- **LIVE:** Program sprawdza rozmiar pliku **co 4 sekundy** - jeśli się zmieni, ponownie odczytuje plik
- Idealne gdy zewnętrzny program zapisuje partie do pliku w czasie rzeczywistym

### 3. LiveChessCloud Live
- Link do turnieju na platformie LiveChessCloud
- Przykład: `https://view.livechesscloud.com/#abcd1234-....`
- **LIVE:** Program pobiera partie z turnieju **co 4 sekundy** w czasie rzeczywistym (polling)
- **Numer rundy:** Domyślnie runda 1, możesz wybrać dowolną rundę
- Każda runda jest zapisywana do osobnego pliku PGN

**Podsumowanie LIVE:** Wszystkie źródła są monitorowane co 4 sekundy - Web URL i LiveChessCloud ponownie pobierają dane, Local File sprawdza czy rozmiar się zmienił.

---

## Claims (Roszczenia)

**Claims** to sytuacje, w których gra szachowa kończy się natychmiast lub gracz może **złożyć oficjalne roszczenie** zgodnie z przepisami FIDE. Program automatycznie wykrywa następujące typy claims:

### Rodzaje Claims

| Typ Roszczenia | Opis | Kiedy się pojawia |
|----------------|------|-------------------|
| **3-fold repetition** | Pozycja powtórzona trzy razy | Gdy ta sama pozycja na szachownicy występuje po raz trzeci (reklamacja remisu) |
| **5-fold repetition** | Pozycja powtórzona pięć razy | Gdy ta sama pozycja na szachownicy występuje po raz piąty (automatyczny koniec gry) |
| **50-move rule** | Zasada 50 ruchów | Po 50 ruchach bez ruchu pionem lub bicia (reklamacja remisu) |
| **75-move rule** | Zasada 75 ruchów | Po 75 ruchach bez ruchu pionem lub bicia (automatyczny koniec gry) |
| **Stalemate** | Pat | Gdy gracz nie ma legalnego ruchu, ale nie jest w szachu (automatyczny koniec gry) |
| **Checkmate** | Szach-mat | Gdy gracz jest zaszachowany (automatyczny koniec gry) |
| **Dead position** | Pozycja martwa | Gdy żaden z graczy nie może dać mata (automatyczny koniec gry) |

### Jak Działa Wykrywanie Claims?
- Program skanuje partie **ruch po ruchu**
- Każde roszczenie jest rejestrowane z:
  - Numerem stołu
  - Nazwiskami graczy
  - Numerem ruchu, gdy roszczenie wystąpiło
  - Komentarzem wyjaśniającym

---

## Reminders (Przypomnienia)

**Reminders** to ostrzeżenia informacyjne, które pomagają sędziemu przygotować się na nadchodzące sytuacje lub informują o możliwych naruszeniach przepisów, które muszą zostać zweryfikowane przez sędziego. NIE kończą one gry automatycznie, ale wymagają uwagi sędziego.

### Rodzaje Reminders

| Typ Przypomnienia | Opis | Kiedy się pojawia |
|-------------------|------|-------------------|
| **Two fold repetition** | Pozycja powtórzona dwukrotnie (ostrzeżenie przed 3-fold) | Gdy ta sama pozycja występuje po raz drugi - **Ostrzeżenie:** "Uważaj, gracz może wkrótce zgłosić 3-fold repetition" |
| **45-move reminder** | Ostrzeżenie przed zasadą 50-ruchową | Po 45 ruchach bez ruchu pionem lub bicia - **Ostrzeżenie:** "Za 5 ruchów będzie możliwe zgłoszenie 50-move claim" |
| **Time control warning** | Nadchodząca kontrola czasu | 2 ruchy przed osiągnięciem kontroli czasu (np. przy ruchu 38 dla kontroli przy ruchu 40) - "Uważaj, sędzia powinien być przy szachownicy" |
| **Low on time** | Gracz ma mało czasu pozostałego | Gdy gracz ma mniej czasu niż Twój ustawiony próg - "Ostrzeżenie, gracz może wkrótce przekroczyć czas" |
| **Flag fall reminder** | Wykryto opadnięcie chorągiewki (czas minął) | Gdy czas gracza osiąga 0:00:00 - **Alert:** "Sprawdź czy zawodnik nie przekroczył czasu na tej szachownicy!" |
| **Illegal move warning** | Wykryto nielegalny ruch w grze | Gdy program wykryje nielegalny ruch w PGN - **Alert:** "Natychmiast sprawdź sytuację na szachownicy - może być nielegalny ruch lub błąd w zapisie" |
| **Scoresheet change warning** | Blankiet zapisu partii prawie pełny | Gdy gracze zapisali już rubryki dla wszystkich ruchów (np. 55 ruchów) - "Przynieś nowe zapisy" |
| **Sofia rule violation** | Nielegalna zgoda na remis | Remis dokonany przed ruchem 30 (domyślne ustawienie, regulowane przez sędziego) |
| **Possible incorrect result** | Ogłoszony wynik partii nie pasuje do oceny Stockfisha | Gdy zapisany wynik w nagłówkach PGN (1-0, 0-1, 1/2-1/2) znacznie różni się od oceny silnika dla pozycji końcowej - **Alert:** "Sprawdź wynik partii - ocena pozycji sugeruje inny rezultat" |

---

## Analiza Fair-Play

**Analiza Fair-Play** to narzędzie do wstępnej oceny, które pomaga sędziom zidentyfikować potencjalnie podejrzane partie. System analizuje ruchy każdego gracza niezależnie i przypisuje jeden z trzech poziomów ryzyka:

### Poziomy Ryzyka

| Poziom | Kolor | Akcja |
|--------|-------|-------|
| **LOW** | 🟢 Zielony | Brak |
| **MEDIUM** | 🟠 Pomarańczowy | Zalecana rutynowa obserwacja |
| **HIGH** | 🔴 Czerwony | Zalecana dalsza weryfikacja |

### Jak Uruchomić Analizę Fair-Play

1. Otwórz plik PGN w Board Viewer
2. Kliknij prawym przyciskiem myszy na dowolną partię na liście gier
3. Wybierz **"Fair-Play Analysis"** z menu kontekstowego
4. Zobacz wyniki z wskaźnikami poziomu ryzyka dla Białych i Czarnych

### Wyświetlane Wyniki

Analiza pokazuje osobne wyniki dla każdego gracza w tym:
- **T1 (Top Match Rate)** - Procent ruchów zgodnych z #1 wyborem Stockfisha
- **BR (Blunder Resistance)** - Odporność na błędy (0-100%)
- **APL (Average Point Loss)** - Średni błąd w punktach
- **SPI (Sigmoidal Precision Index)** - Sigmoidalny indeks precyzji (~50 = norma ludzka)

Poziom ryzyka jest określany przez progi T1/BR LUB SPI, whichever triggers first.

🛡️ **SPI (Sigmoidal Precision Index) — Beta Version**

This tool is intended strictly for arbiters and is currently in its scaling phase. The data below does not imply any rule violation. Drawing conclusions from a single game carries high statistical risk; therefore, system outputs, if any, should be treated solely as suggestions for further routine actions.

---

## Różnice między Claims i Reminders

| Cecha | Claims | Reminders |
|-------|--------|-----------|
| **Status** | **OBOWIĄZKOWE** - nie można wyłączyć, zawsze aktywne | **OPCJONALNE** - można włączyć/wyłączyć w ustawieniach |
| **Cel** | Wykrywanie potencjalnych roszczeń lub automatycznych końcówek gry zgodnie z przepisami FIDE | Pomoc sędziemu w monitorowaniu sytuacji turniejowych |
| **Częstotliwość** | Powtarza się tak długo, jak trwa warunek | Jednorazowo dla konkretnego typu (nie powtarza się) |
| **Konsekwencje** | Większość powoduje natychmiastowy koniec gry (checkmate, stalemate, dead position, 75-move, 5-fold). 3-fold i 50-move wymagają weryfikacji sędziego z udziałem graczy. | Tylko ostrzeżenie informacyjne - NIE kończy gry automatycznie |

---

## System ACK (Acknowledgment)

System ACK pozwala oznaczyć claims lub reminders jako "rozwiązane" po ich obsłudze. Pomaga to utrzymać czystą tabelę wspisów i skupić się na aktywnych problemach.

### Jak Działa?
1. Gdy claim lub reminder jest wyzwolony, pojawia się w tabeli claims
2. Po rozwiązaniu sytuacji możesz oznaczyć go jako **ACK** (acknowledged) ✅, używając prawego przycisku myszy
3. Rozwiązane (ACK) ✅ claims i reminders mogą być usunięte z tabeli claims za pomocą przycisku **"Clear Resolved (Claims)"**

---

## Pozostałe Przyciski

W głównym oknie znajdują się trzy główne przyciski:

### Start (Niebieski)
- **Funkcja:** Rozpoczyna skanowanie gier i pobieranie danych ze źródeł
- Dla wszystkich źródeł włącza automatyczne odświeżanie co 4 sekundy

### Stop (Czerwony)  
- Zatrzymuje skanowanie

### Przycisk Clear Resolved Claims
- Czyści wszystkie potwierdzone claims i reminders z tabeli

---

## Powiadomienia

Aplikacja zawiera system powiadomień, aby ostrzec sędziów o ważnych zdarzeniach:

### Rodzaje Powiadomień

| Typ Powiadomienia | Kiedy się aktywuje | Cel |
|-------------------|---------------------|-----|
| **Wykryto roszczenie** | Gdy wykryta zostanie sytuacja roszczenia (3-fold, 50-move, checkmate itp.) | Ostrzeżenie sędziego o weryfikacji i obsłudze roszczenia |
| **Aktywowano przypomnienie** | Gdy spełniony jest warunek przypominania (nielegalny ruch, niski czas, naruszenie reguł Sofii) | Informacja sędziego o sytuacjach wymagających uwagi |

### Zachowanie Powiadomień
- Powiadomienia pojawiają się jako alerty systemowe wymagające potwierdzenia
- Alert dźwiękowy można skonfigurować w ustawieniach aplikacji
- Krytyczne powiadomienia (checkmate, flag fall) mają wyższy priorytet
- Powiadomienia mogą być włączone lub wyłączone

---

## Board Viewer – Wizualizacja Partii

Board Viewer to główny interfejs do przeglądania i analizowania gier. Oto jak interpretować oznaczenia wizualne:

### Kolory i Oznaczenia w Board Viewer

| Element | Kolor/Znaczenie | Kiedy się pojawia |
|---------|-----------------|-------------------|
| **Zielona ramka szachownicy** | Pozycja powtórzona 3. lub 5. raz (3-fold/5-fold repetition snapshot) | Gdy pozycja na szachownicy występuje po raz 3-ci lub 5-ty |
| **Niebieska ramka szachownicy** | 50 lub 75 ruchów od nieodwracalnego ruchu (50-moves/75-moves snapshot) | Gdy minęło 50 lub 75 ruchów od ostatniego ruchu pionem lub bicia |
| **Czerwona ramka szachownicy** | Wykryto nielegalny ruch w grze | Wskazuje pozycję po ostatnim legalnym ruchu (nielegalny ruch jest dodany w zapisie) |
| **Żółte podświetlenie szachownicy** | Ostatni wykonany ruch | Zawsze po wykonaniu ruchu - pole docelowe ostatniego ruchu jest podświetlone na żółto |

### Kolory i Oznaczenia w zapisie partii (scoresheet)

| Element | Kolor/Znaczenie | Kiedy się pojawia |
|---------|-----------------|-------------------|
| **Zielone oznaczenie tekstu** | Pozycja powtórzona 3. lub 5. raz (konkretne ruchy) | Gdy pozycja na szachownicy występuje po raz 3-ci lub 5-ty |
| **Niebieskie oznaczenie tekstu** | 50 lub 75 ruchów od nieodwracalnego ruchu (konkretne ruchy) | Gdy minęło 50 lub 75 ruchów od ostatniego ruchu pionem lub bicia |
| **Czerwone oznaczenie tekstu** | Wykryto nielegalny ruch w grze (konkretny ruch) | Gdy wykonano nielegalny ruch lub wystąpił błąd zapisu |
| **Żółte tło** | Obecnie zaznaczony ruch | Po kliknięciu na konkretny ruch w notacji poniżej szachownicy |

### Informacje o Czasie (pod nazwami graczy)

- Format: `Nazwisko (Pozostały Czas)` + `Ostatni ruch (Czas namysłu)`
- Pokazuje pozostały czas po ostatnim ruchu każdego gracza **pozostały czas** (czas jest statyczny)
- Pokazuje jak długo gracz myślał nad swoim ostatnim ruchem **czas namysłu w ostatnim ruchu**

### Nawigacja w Board Viewer

#### Przyciski nawigacyjne:
| Przycisk | Funkcja |
|----------|---------|
| **⏮** | Pierwsza gra na liście / Początek obecnej gry |
| **◀** | Poprzednia gra / Poprzedni ruch w grze |
| **▶** | Następna gra / Następny ruch w grze |
| **⏭** | Ostatnia gra na liście / Koniec obecnej gry |

#### Nawigacja klawiaturą:
- Użyj **strzałek lewo/prawo** do nawigacji między grami (gdy lista jest aktywna) lub ruchami (gdy szachownica/PGN jest aktywna)
- Użyj **strzałek góra/dół** do przewijania listy gier

### Filtrowanie Gier

- **Pole wyszukiwania:** Wpisz nazwisko gracza lub numer stołu (np. "12")
- **Checkbox "Show only active games":** Pokazuje tylko gry z wynikiem `*` (trwające)

---

## Podsumowanie

Akiba to potężne narzędzie dla sędziów szachowych, które:
- ✅ Automatycznie wykrywa claims i reminders w grach
- ✅ Obsługuje wiele źródeł danych jednocześnie (URL, pliki lokalne, LiveChessCloud)
- ✅ Łączy gry z różnych źródeł do jednego pliku PGN
- ✅ Wizualizuje kluczowe pozycje (3-fold/5-fold snapshots, nielegalne ruchy)
- ✅ Pozwala zarządzać rozwiązанными claims przez system ACK
- ✅ Posiada system powiadomień dla ważnych zdarzeń

### Zbieranie Danych

Pliki danych są przechowywane w katalogu `%APPDATA%\Akiba\`.

**Beacons**

Aplikacja Akiba wysyła anonimowe dane do Google Sheets w celu statystyk użytkowania. Każde kliknięcie przycisku "Start" wysyła jeden wpis zawierający:
- **Device ID** - unikalny, anonimowy hash (nie można powiązać z Tobą)
- **Wersja aplikacji** - np. "1.1"  
- **System operacyjny** - np. "Windows 11"

Dane są zbierane wyłącznie w celach statystycznych (ile osób używa programu, które wersje). NIE zbieramy żadnych danych osobowych ani informacji o partiach szachowych.

---