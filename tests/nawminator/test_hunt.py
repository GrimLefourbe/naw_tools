import hypothesis as hp
import hypothesis.strategies as st
import pytest
import nawminator as nm

RC1 = """Rapport de combat en chasse
Vous chassez sur un territoire inconnu.

Avant combat
Troupe en attaque : 149 620 Jeunes soldates, 33 716 Soldates, 4 104 Tirailleuses
Troupe en défense : 579 Petites araignées, 9 Limaces, 13 388 Escargots, 899 Araignées, 10 Abeilles, 1 Mante religieuse, 1 Souris, 19 Pics

Combat
Vous infligez 1 699 164 (+ 1 291 365) dégâts et vous tuez 14 906 ennemis
La défense riposte, vous infligeant 91 313 dégâts et tuant 3 224 unités

Après combat
Expérience gagnée : 4 840 Soldates, 1 115 Soldates d'élite, 136 Tirailleuses d'élite
Armée finale : 141 556 Jeunes soldates, 37 441 Soldates, 1 115 Soldates d'élite, 3 968 Tirailleuses, 136 Tirailleuses d'élite.


Vous avez chassé 191 000 cm² de terrain de chasse
Votre armée ramène les carcasses de la bataille. Vous avez rapporté 461 550 Nourriture, 263 743 Bois et 216 646 Eau .
Terrain avant : 124017 cm² et Terrain après : 315017 cm².

Difficulté de la chasse : 3 456 417."""

RC2 = """NatureAtWar
Rapport de chasse : Gagné 292 802 cm² Terrain de chasse, 198 425 Nourriture, 846 614 Bois et 370 394 Eau
02/09 09:42

Rapport de combat en chasse
Vous chassez sur un territoire inconnu.

Avant combat
Troupe en attaque : 12 811 Jeunes soldates, 58 929 Jeunes légionnaires
Troupe en défense : 3 Petites araignées, 9 Limaces, 106 Criquets, 15 686 Fourmis, 1 933 Termites, 2 Petits lézards, 7 Tétras, 4 Faisans

Combat
Vous infligez 2 754 293 (+ 2 093 263) dégâts et vous tuez 17 750 ennemis
La défense riposte, vous infligeant 196 025 dégâts et tuant 7 123 unités

Après combat
Expérience gagnée : 368 Soldates, 3 808 Légionnaires
Armée finale : 5 320 Jeunes soldates, 368 Soldates, 55 121 Jeunes légionnaires, 3 808 Légionnaires.


Vous avez chassé 292 802 cm² de terrain de chasse
Votre armée ramène les carcasses de la bataille. Vous avez rapporté 198 425 Nourriture, 846 614 Bois et 370 394 Eau .
Terrain avant : 183360 cm² et Terrain après : 476162 cm².

Difficulté de la chasse : 5 531 950."""

@pytest.mark.parametrize(
    "rc,expected",
    [
        (
            RC1, 
            nm.hunt.HuntingReport(
                124017,
                191000, 
                nm.army.Army(JS=149620, S=33716, T=4104), 
                nm.army.Army(JS=141556, S=37441, SE=1115, T=3968, TE=136),
            ),
        ),
        (
            RC2,
            nm.hunt.HuntingReport(
                183360,
                292802,
                nm.army.Army(JS=12811, JL=58929),
                nm.army.Army(JS=5320, S=368, JL=55121, L=3808),
            )
        )
    ]
)
def test_parse_hunt(rc, expected):
    assert nm.hunt.HuntingReport.from_rc(rc) == expected

@pytest.mark.skip("WIP")
@pytest.mark.parametrize(
    "hunt,levels,expected",
    [
        (
            nm.hunt.HuntingReport(
                124017,
                191000, 
                nm.army.Army(JS=149620, S=33716, T=4104), 
                nm.army.Army(JS=141556, S=37441, SE=1115, T=3968, TE=136),
            ),
            nm.levels.Levels(mandibule=14, carapace=14, dome=8, loge=8, special=3, alliance=nm.levels.AllianceType.GUERRIER),
            False
        ),
        (
            nm.hunt.HuntingReport(
                183360,
                292802,
                nm.army.Army(JS=12811, JL=58929),
                nm.army.Army(JS=5320, S=368, JL=55121, L=3808),
            ),
            nm.levels.Levels(mandibule=14, carapace=14, dome=12, loge=9, special=0, alliance=nm.levels.AllianceType.GUERRIER),
            {
                "count": -7123,
                "fdf": +2232,
                "osd": -113520,
                "osl": -124596,
            }
        )
    ]
)
def test_hunt_diff(hunt: nm.hunt.HuntingReport, levels: nm.levels.Levels, expected):
    assert hunt.diff(levels) == expected

@pytest.mark.filterwarnings("error::RuntimeWarning")
@pytest.mark.property
@hp.example(50, 107)
@hp.example(20000, 766730)
@hp.example(20000, 9446000)
@hp.example(100000, 248719)
@hp.given(
    start=st.integers(50, 2**48),
    target_difficulty=st.integers(1000, 2**54)
)
def test_max_hunt(start, target_difficulty):
    h = nm.hunt.max_hunt_amount(start, target_difficulty)
    dh = nm.formulas.hunt_difficulty(start, h+1)
    dl = nm.formulas.hunt_difficulty(start, h)
    hp.note(h)
    hp.note(dh)
    hp.note(dl)
    assert dh > target_difficulty + 3 and dl <= target_difficulty + 3

