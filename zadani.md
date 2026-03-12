LODĚ
Naimplementujte hru „Lodě“ pro dva hráče pomocí Pythonu a REST API (např. pomocí frameworku FastAPI nebo Flask).
Požadavky:

-   Na začátku každého kola vygenerujte hrací plochu na základě vstupních parametrů:

-   Jméno hráče 1
-   Jméno hráče 2
-   Velikost hracího pole:

-   minimální rozměr: 10
-   maximální rozměr: 20

-   Pro každého hráče se náhodně umístí následující lodě, libovolně svisle nebo vodorovně orientované. Lodě se nesmí dotýkat žádnou stranou ani rohem:

-   2× jedno pole [X]
-   2× dvě pole [XX]
-   1× tři pole [XXX]
-   1× tvar:
-   [X]
-   [XXX]
-     [X]
-   1× tvar:
-   [XXXX]
-     [X]

-   Hra probíhá v jednotlivých tazích, kdy se na server předávají následující parametry:

-   Pozice X
-   Pozice Y

-   Server odpovídá stavem dle zásahu:

-   Voda
-   Zásah
-   Potopena celá

-   Hráči se střídají v jednotlivých tazích. Pokud je odpověď „Voda“, pokračuje druhý hráč; jinak pokračuje hráč, který právě táhl.
-   Hra končí ve chvíli, kdy jeden z hráčů nemá žádnou loď ani její část k dispozici.

Výstup:

-   REST API s endpointy pro:

-   vytvoření nové hry,
-   provedení tahu,
-   získání stavu hry.

-   Data přenášejte ve formátu JSON.
