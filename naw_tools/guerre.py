import naw_tools.formula as formula
from datetime import datetime, timedelta, time
from typing import TypeVar, List, Any, Tuple
import pandas as pd
import re

T = TypeVar("T", datetime, time)


def depart_to_arrival(
    depart: T,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    va: int = 0,
) -> T:
    d = timedelta(seconds=formula.duree_attaque(x1=x1, y1=y1, x2=x2, y2=y2, va=va))

    if isinstance(depart, time):
        return (datetime.combine(datetime.today(), depart) + d).time()
    else:
        return depart + d


def va_from_travel(
    depart: T,
    arrival: T,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> float:
    expected = timedelta(seconds=formula.duree_attaque(x1, y1, x2, y2, 0))
    if isinstance(depart, time):
        if isinstance(arrival, time):
            if arrival > depart:
                d = datetime.combine(datetime.today(), arrival) - datetime.combine(
                    datetime.today(), depart
                )
            else:
                d = (
                    datetime.combine(datetime.today(), arrival)
                    + timedelta(days=1)
                    - datetime.combine(datetime.today(), depart)
                )
        else:
            raise TypeError(
                f"expected type {type(depart)} but received {type(arrival)}"
            )
    elif isinstance(arrival, time):
        raise TypeError(f"expected type {type(depart)} but received {type(arrival)}")
    else:
        d = arrival - depart

    return 10 * expected / d - 10


units = [
    [r"Esclaves?", 4, 4, 3],
    [r"Maîtres? esclaves?", 6, 6, 4],
    [r"Jeunes? soldates?", 16, 8, 7],
    [r"Soldates?(?!s? d'élite)", 20, 11, 10],
    [r"Soldates? d'élite", 26, 17, 14],
    [r"Gardiennes?(?!s? d'élite)", 25, 1, 27],
    [r"Gardiennes? d'élite", 32, 1, 35],
    [r"Tirailleuses?(?!s? d'élite)", 12, 32, 10],
    [r"Tirailleuses? d'élite", 15, 40, 12],
    [r"Jeunes? légionnaires?", 40, 45, 35],
    [r"Légionnaires?(?!s? d'élite)", 55, 60, 45],
    [r"Légionnaires? d'élite", 60, 65, 50],
    [r"Jeunes? tanks?", 40, 80, 1],
    [r"Tanks?(?!s? d'élite)", 70, 140, 1],
    [r"Tanks? d'élite", 80, 160, 1],
]


def parseNawInt(s: str) -> int:
    return int(s.replace(" ", ""))


def parseArmee(s: str) -> List[int]:
    pattern = r"\W*".join([rf"(?:(\d[ \d]*) {i[0]})?" for i in units])
    print(pattern)
    return [
        parseNawInt(i) if i is not None else 0 for i in re.search(pattern, s).groups()
    ]


def parseFight(s: str) -> List[List[int]]:
    res = re.findall(
        r"^.*?infli\w+ (\d[\d ]*) \(\+ (\d[\d ]*)\) dégâts et.*? tu\w+ (\d[\d ]*) (unités?|ennemis?)\W*$",
        s,
        re.MULTILINE,
    )
    return [[parseNawInt(a), parseNawInt(b), parseNawInt(c)] for a, b, c, d in res]


def armeeStats(armee: List[int]):
    hp, atk, rip, cnt = [0] * 4
    for nb_troup, (name, uhp, uatk, urip) in zip(armee, units):
        hp += nb_troup * uhp
        atk += nb_troup * uatk
        rip += nb_troup * urip
        cnt += nb_troup

    return hp, atk, rip, cnt


def first_n_units(armee: List[int], n) -> Tuple[List[int], List[int]]:
    first = [0 for _ in range(len(units))]
    second = armee.copy()
    for i, cnt in enumerate(armee):
        amount = min(cnt, n)
        first[i] += amount
        second[i] -= amount
        n -= amount
    return first, second


def get_fight_stats(armee_atk: List[int], armee_def: List[int], fight: List[List[int]]):
    atk_stats = armeeStats(armee_atk)
    def_stats = armeeStats(armee_def)

    fr_def_kills = fight[1][2]
    fr_def_dmg = fight[1][0] + fight[1][1]
    fr_atk_kills = fight[0][2]
    fr_atk_dmg = fight[0][0] + fight[0][1]

    atk_dmg_bonus = fight[0][1] / fight[0][0]
    def_dmg_bonus = fight[1][1] / fight[1][0]

    atk_losses, _ = first_n_units(armee_atk, fr_def_kills)
    def_losses, _ = first_n_units(armee_def, fr_atk_kills)
    print(atk_losses)
    print(def_losses)
    hp_losses_atk = armeeStats(atk_losses)[0]
    hp_losses_def = armeeStats(def_losses)[0]

    if def_stats[3] == fr_atk_kills or fr_atk_kills <= 1:
        def_hp_bonus = pd.NA
    else:
        def_hp_bonus = fr_atk_dmg / hp_losses_def - 1

    if atk_stats[3] == fr_def_kills or fr_def_kills <= 1:
        atk_hp_bonus = pd.NA
    else:
        atk_hp_bonus = fr_def_dmg / hp_losses_atk - 1

    return [atk_dmg_bonus, atk_hp_bonus], [def_dmg_bonus, def_hp_bonus]


def parseRC(rc):
    attaque = re.search(r"Troupe en attaque : (.*?)\n", rc)
    defense = re.search(r"Troupe en défense : (.*?)\n", rc)
    fight = re.search(r"Combat\W+(.*)", rc, flags=re.S | re.MULTILINE | re.DOTALL)

    armee_atk = parseArmee(attaque.group(1))
    armee_def = parseArmee(defense.group(1))
    print(armee_atk)
    print(armee_def)
    stats_atk = armeeStats(armee_atk)
    stats_def = armeeStats(armee_def)

    fight = parseFight(fight.group(1))
    atk_bonuses, def_bonuses = get_fight_stats(armee_atk, armee_def, fight)

    fr_atk_kills = sum(i[2] for i in fight[::2])
    fr_def_kills = sum(i[2] for i in fight[1::2])
    atk_losses, atk_left = first_n_units(armee_atk, fr_def_kills)
    def_losses, def_left = first_n_units(armee_def, fr_atk_kills)

    stats_atk_ab = [
        stats_atk[0] * (1 + atk_bonuses[1]),
        stats_atk[1] * (1 + atk_bonuses[0]),
        stats_atk[2] * (1 + atk_bonuses[0]),
        stats_atk[3],
    ]
    stats_def_ab = [
        stats_def[0] * (1 + def_bonuses[1]),
        stats_def[1] * (1 + def_bonuses[0]),
        stats_def[2] * (1 + def_bonuses[0]),
        stats_def[3],
    ]

    armies_df = pd.DataFrame(
        columns=["", "Attaquant", "Defenseur"],
        data=list(zip([x[0].replace("s?", "").replace("(?! d'élite)", "") for x in units], armee_atk, armee_def)),
    )
    armies_df = armies_df.append(
        pd.DataFrame(
            columns=["", "Attaquant", "Defenseur"],
            data=[
                ["Vie AB", stats_atk_ab[0], stats_def_ab[0]],
                ["Attaque AB", stats_atk_ab[1], stats_def_ab[1]],
                ["Riposte AB", stats_atk_ab[2], stats_def_ab[2]],
                ["CDF", stats_atk_ab[3], stats_def_ab[3]],
            ],
        )
    ).set_index("")
    stats_atk_left = armeeStats(atk_left)
    stats_def_left = armeeStats(def_left)
    left_df = pd.DataFrame(
        columns=["", "Attaquant", "Defenseur"],
        data=list(zip([x[0].replace("s?", "").replace("(?! d'élite)", "") for x in units], atk_left, def_left)),
    )
    print(f"bonus atk: {atk_bonuses}")
    print(f"bonus def: {def_bonuses}")
    left_df = left_df.append(
        pd.DataFrame(
            columns=["", "Attaquant", "Defenseur"],
            data=[
                ["Vie AB", stats_atk_left[0] * (1 + atk_bonuses[1]), stats_def_left[0] * (1 + def_bonuses[1])],
                ["Attaque AB", stats_atk_left[1] * (1 + atk_bonuses[0]), stats_def_left[1] * (1 + def_bonuses[0])],
                ["Riposte AB", stats_atk_left[2] * (1 + atk_bonuses[0]), stats_def_left[2] * (1 + def_bonuses[0])],
                ["CDF", stats_atk_left[3], stats_def_left[3]],
            ],
        )
    ).set_index("")
    niveaux_df = pd.DataFrame(
        columns=["", "Attaquant", "Defenseur"],
        data=list(zip(["Bonus Dégats", "Bonus Vie"], [i for i in atk_bonuses], [i for i in def_bonuses]))
    )
    return armies_df.round().astype(pd.Int64Dtype()), left_df.round().astype(pd.Int64Dtype()), niveaux_df.set_index("")


def format_stats(
    armies_avant, armies_apres, niveaux, mode="string", index=False, columns=None
):
    if mode == "html":
        formatter = lambda x: x.to_html(
            classes="data",
            index=True,
            float_format=lambda i: f"{int(i):,}".replace(",", " ")
            if i >= 100
            else f"{i:,.3g}".replace(",", " "),
        )
    elif mode == "string":
        formatter = lambda x: x.to_string(
            index=True,
            float_format=lambda i: f"{int(i):,}".replace(",", " ")
            if i >= 100
            else f"{i:,.3g}".replace(",", " "),
        )
    elif mode == "csv":
        formatter = lambda x: x.to_csv(
            index=index,
            columns=columns,
            float_format=lambda i: f"{int(i):,}".replace(",", " ")
            if i >= 100
            else f"{i:,.3g}".replace(",", " "),
        )
    else:
        raise NotImplementedError(f"{mode} is not supported")
    return formatter(armies_avant), formatter(armies_apres), formatter(niveaux)


if __name__ == "__main__":
    RC = """Rapport de combat en Dôme :

    Votre colonie Ldopé[-6:368] a été attaqué par la colonie DragonBall[91:124] du joueur Bad Broly en Dôme.

    Avant combat
    Troupe en attaque : 16 456 Jeunes soldates, 35 034 Soldates, 50 164 Soldates d'élite, 104 011 Tirailleuses, 27 428 Tirailleuses d'élite
    Troupe en défense : 1 000 Jeunes soldates

    Combat
    L'assaillant vous a infligé 5 795 282 (+ 3 766 933) dégâts et vous a tué 1 000 unités.
    Vous ripostez, infligeant 700 (+ 490) dégâts et tuant 50 ennemis

    Après combat
    Expérience gagnée : aucune.
    Armée finale : Aucune.
    Pillage : Vous avez été pillé de 66 346 cm² Terrain de chasse, 2 183 387 nourritures, 7 779 654 bois, 2 827 579 eaux."""
    print(format_stats(*parseRC(RC)))
    print(
        depart_to_arrival(
            depart=time(hour=19, minute=55, second=25),
            x1=335,
            y1=370,
            x2=-56,
            y2=139,
            va=16,
        )
    )

    print(
        depart_to_arrival(
            depart=datetime.combine(
                datetime.today(), time(hour=19, minute=55, second=25)
            ),
            x1=335,
            y1=370,
            x2=-56,
            y2=139,
            va=16,
        )
    )
