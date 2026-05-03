import nawminator as nm

import pandas as pd
import pytest

test_string_data_1 = """
Distance	Durée	Coordonnées	Terrain	Colonie	Joueur	Alliance	État
Distance	Durée	Coordonnées	Terrain	Colonie	Joueur	Alliance	État
0	0s	[-40:-20]	2,093,882	Fuqit	Fuqit	SDS	Libre
82	01H 58m 24s	[-111:22]	531,063	NeedFloods	Jack-Sparrow	RDP	Vassal de DeadShot
85	02H 01m 58s	[-104:36]	2,096,077	-Rium	Naasceth	RDP	Libre
"""

test_string_data_2 = """
Distance	Durée	Coordonnées	Terrain	Colonie	Joueur	Alliance	État
Distance	Durée	Coordonnées	Terrain	Colonie	Joueur	Alliance	État
0	0s	[-40:-20]	2,093,882	Fuqit	Fuqit	SDS	Libre
82	01H 58m 24s	[-111:22]	531,063	NeedFloods	Jack Sparrow	RDP	Vassal de DeadShot
85	02H 01m 58s	[-104:36]	2,096,077	-Rium	Naasceth	RDP	Libre
"""

test_string_data_3 = """
Distance	Durée	Coordonnées	Terrain	Colonie	Joueur	Alliance	État
Distance	Durée	Coordonnées	Terrain	Colonie	Joueur	Alliance	État
0	0s	[-40:-20]	2,093,882	Fuqit	Fuqit	SDS	Libre
82	01H 58m 24s	[-111:22]	531,063	NeedFloods	Jack Sparrow	RDP	Vassal de DeadShot
85	02H 01m 58s	[-104:36]	2,096,077	-Rium	Naasceth	RDP	Libre
159	03H 27m 39s	[37:119]	712,872	Fuqit	Fuqit	SDS	Vassal de Jack Sparrow
"""

test_source_code_data_1 = """
<tr style='color:blue;font-weight:bold;'>
    <td>74</td>
    <td class="blur">xxmxxs</td>
    <td>[-70:148]</td>
    <td>215,191</td>
    <td><a style='color:blue;font-weight:bold;' href='attaque--70-148'>A flooder</a></td>
    <td><a style='color:blue;font-weight:bold;' href="profil-430"> <b>lesage</b></a></td>
    <td><a style='color:blue;font-weight:bold;' href="descriptionalliance-DGSE"> <b>DGSE</b></a></td>
    <td>Libre</td>
</tr>

<tr style='color:blue;font-weight:bold;'>
    <td>75</td>
    <td class="blur">xxmxxs</td>
    <td>[-70:143]</td>
    <td>60,187</td>
    <td><a style='color:blue;font-weight:bold;' href='attaque--70-143'>Bastion</a></td>
    <td><a style='color:blue;font-weight:bold;' href="profil-29"> <b>Yvahra</b></a></td>
    <td><a style='color:blue;font-weight:bold;' href="descriptionalliance-LGN"> <b>LGN</b></a></td>
    <td>Libre</td>
</tr>

<tr style='color:black;font-weight:bold;'>
    <td>79</td>
    <td class="blur">xxmxxs</td>
    <td>[74:120]</td>
    <td>49</td>
    <td><a style='color:black;font-weight:bold;' href='attaque-74-120'>Citadelle</a></td>
    <td><a style='color:black;font-weight:bold;' href="profil-334"> <b>Jajaja</b></a></td>
    <td><a style='color:black;font-weight:bold;' href="descriptionalliance-"> <b></b></a></td>
    <td>Vassal de <a href='profil-661'> <b>rabinou</b></a></td>
</tr>
"""

@pytest.mark.parametrize(
    "text,expected",
    [
        (
            test_string_data_1,
            pd.DataFrame(
                [
                    ["[-40:-20]", 2_093_882, "Fuqit", "Fuqit", "SDS"],
                    ["[-111:22]", 531_063, "NeedFloods", "Jack-Sparrow", "RDP"],
                    ["[-104:36]", 2_096_077, "-Rium", "Naasceth", "RDP",],
                ],
                columns=["coord", "tdc", "colo_name", "player_name", "alliance"],
            ),
        ),
        (
            test_string_data_2,
            pd.DataFrame(
                [
                    ["[-40:-20]", 2_093_882, "Fuqit", "Fuqit", "SDS"],
                    ["[-111:22]", 531_063, "NeedFloods", "Jack Sparrow", "RDP"],
                    ["[-104:36]", 2_096_077, "-Rium", "Naasceth", "RDP",],
                ],
                columns=["coord", "tdc", "colo_name", "player_name", "alliance"],
            ),            
        ),
        (
            test_string_data_3,
            pd.DataFrame(
                [
                    ["[-40:-20]", 2_093_882, "Fuqit", "Fuqit", "SDS"],
                    ["[-111:22]", 531_063, "NeedFloods", "Jack Sparrow", "RDP"],
                    ["[-104:36]", 2_096_077, "-Rium", "Naasceth", "RDP",],
                    ["[37:119]", 712_872, "Fuqit", "Fuqit", "SDS"],
                ],
                columns=["coord", "tdc", "colo_name", "player_name", "alliance"],
            ),            
        )
    ],
)
def test_parse_text(text: str, expected: pd.DataFrame):
    pd.testing.assert_frame_equal(nm.parsing.parse_joueurs_text(text), expected)


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            test_source_code_data_1,
            pd.DataFrame(
                [
                    ["[-70:148]", 215_191, "A flooder", "lesage", "DGSE"],
                    ["[-70:143]", 60_187, "Bastion", "Yvahra", "LGN"],
                    ["[74:120]", 49, "Citadelle", "Jajaja", ""],
                ],
                columns=["coord", "tdc", "colo_name", "player_name", "alliance"],
            ),
        )
    ],
)
def test_parse_source_code(text: str, expected: pd.DataFrame):
    pd.testing.assert_frame_equal(nm.parsing.parse_joueurs_sourcecode(text), expected)
