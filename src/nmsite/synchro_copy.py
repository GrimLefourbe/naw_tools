import nawminator as nm
import pandas as pd
import datetime as dt


def _format_colonie_link(base_url: str, x: int | str, y: int | str, colo_name: str) -> str:
    """BBCode [url=...] link - for format_copy_data_table, forum-only."""
    return f"[url={base_url}/attaque-{x}-{y}]{colo_name}[/url]"


def _format_header(player: pd.Series, va: int, depart: dt.datetime, base_url: str) -> str:
    """Builds the "Cible: ... / VA: ... / Heure de départ: ..." BBCode header for
    format_copy_data_table, linking the Cible colonie to its attack page."""
    base_tdc = player["tdc"]
    base_pos = player[["x", "y"]]
    colonie = _format_colonie_link(base_url=base_url, x=base_pos["x"], y=base_pos["y"], colo_name=player["colo_name"])

    return (
        f"""Cible: [joueur]{player["player_name"]}[/joueur]({colonie})[[alliance]{player["alliance"]}[/alliance]] [{":".join(str(i) for i in base_pos)}]\n"""
        f"""VA: {va}\n"""
        f"""Heure de départ: {depart.strftime("%H:%M:%S")} - TDC: {nm.utils.format_naw_int(base_tdc)}\n"""
    )


_DISCORD_MESSAGE_LIMIT = 2000

_ANSI_ESC = "\x1b"
_ANSI_RESET = f"{_ANSI_ESC}[0m"
_ANSI_BOLD_GREEN = f"{_ANSI_ESC}[1;32m"
_ANSI_BOLD_RED = f"{_ANSI_ESC}[1;31m"


def _discord_row_widths(targets: pd.DataFrame) -> dict[str, int]:
    """Widths for the fields safe to pad/align: Horaire, Durée, and Pos's x/y."""
    # Never contain emoji (unlike Joueur/Colonie, which can), so len(str(value)) is a
    # reliable measure of their rendered width in a monospace font. A first attempt
    # padded every column including Joueur/Colonie and misaligned everything past an
    # emoji.
    # zip(*()) can't unpack into pos_xs, pos_ys when targets is empty (zero rows) -
    # default to empty tuples instead, same as max(..., default=0) below handles the
    # empty case for the other fields.
    positions = [str(p).split(":") for p in targets["Pos"]]
    pos_xs, pos_ys = zip(*positions) if positions else ((), ())
    return {
        "Horaire": max((len(str(v)) for v in targets["Horaire"]), default=0),
        "Durée": max((len(str(v)) for v in targets["Durée"]), default=0),
        # x and y measured separately, not the whole "x:y" string: their digit counts
        # vary independently (e.g. "1:2" vs "23:45") - see _format_discord_row.
        "PosX": max((len(x) for x in pos_xs), default=0),
        "PosY": max((len(y) for y in pos_ys), default=0),
    }


def _format_discord_row(h, d, j, c, a, p, t, cible_alliance: str, widths: dict[str, int], use_ansi: bool) -> str:
    """Same field order/punctuation as format_copy_data_text's rows, with Horaire/
    Durée/Pos padded to align vertically across rows; Joueur/Colonie/TDC stay
    free-width."""
    horaire = str(h).ljust(widths["Horaire"])
    # Right-justified (leading spaces), not left: durations switch unit sets by
    # magnitude ("24M 46S" vs "6h 11m 21s") - left-justifying would line short
    # durations up under the START of longer ones (the hours digit) instead of their
    # end. Right-justifying lines up the last unit letter instead (S under s, M
    # under m before it).
    duree = str(d).rjust(widths["Durée"])
    # x and y split and right-justified independently, not the whole "x:y" string as
    # one unit: their digit counts vary independently, so padding the combined
    # string can't line up the ":" when both sides differ in width at once.
    pos_x, pos_y = str(p).split(":")
    pos = f"{pos_x.rjust(widths['PosX'])}:{pos_y.rjust(widths['PosY'])}"
    alli = str(a)
    if use_ansi:
        # Bold+color combined into one escape prefix (e.g. "\x1b[1;32m") - green if
        # Alli matches the Cible's own alliance (ally), red otherwise (enemy).
        color = _ANSI_BOLD_GREEN if a == cible_alliance else _ANSI_BOLD_RED
        horaire = f"{color}{horaire}{_ANSI_RESET}"
        alli = f"{color}{alli}{_ANSI_RESET}"
    # use_ansi=False (the 2000-character fallback) leaves Horaire/Alli unstyled: a
    # plain (non-ansi) code block disables Discord's markdown parsing entirely, same
    # as it disables ANSI outside the ansi-tagged fence, so ** would just show as
    # literal asterisks there.
    return f"{horaire} - {duree}: [{pos}] {j}[{alli}]({c}) - {t}"


def format_copy_data_text(targets: pd.DataFrame, player: pd.Series, va: int, depart: dt.datetime, base_url: str) -> str:
    """Universal/safe fallback text, fully plain (no markdown at all) - readable
    pasted anywhere (Discord, plain text editors, the forum, etc), not just Discord
    specifically. format_copy_data_discord is the ANSI-colored, Discord-specific
    alternative; format_copy_data_table is the BBCode, forum-only one."""
    base_tdc = player["tdc"]
    base_pos = player[["x", "y"]]
    attack_url = f"{base_url}/attaque-{base_pos['x']}-{base_pos['y']}"
    copy_data = (
        f"""Cible: {player["player_name"]} ({player["colo_name"]}) [{player["alliance"]}] [{":".join(str(i) for i in base_pos)}]\n"""
        f"""Attack: {attack_url}\n"""
        f"""VA: {va}\n"""
        f"""Heure de départ: {depart.strftime("%H:%M:%S")} - TDC: {nm.utils.format_naw_int(base_tdc)}\n"""
    )
    copy_data += f"{"-"*30}\n"
    copy_data += "\n".join(
        [f"{h} - {d}: [{p}] {j}[{a}]({c}) - {t}" for h, d, j, c, a, p, t in targets.itertuples(index=False)]
    )
    return copy_data


def format_copy_data_discord(
    targets: pd.DataFrame, player: pd.Series, va: int, depart: dt.datetime, base_url: str
) -> str:
    """Discord-specific text: bold header, ANSI-colored/aligned rows in a ```ansi
    code block. Richer than format_copy_data_text, but its raw ANSI escape bytes are
    NOT safe pasted anywhere other than Discord (unlike format_copy_data_text's plain
    markdown, which degrades gracefully everywhere)."""
    base_tdc = player["tdc"]
    base_pos = player[["x", "y"]]
    attack_url = f"{base_url}/attaque-{base_pos['x']}-{base_pos['y']}"
    # Bare URL on its own line, not a [text](url) masked link: masked links turned
    # out to silently stop rendering - even elsewhere in the same message - when
    # certain special characters appear in the link text, or when a second ANSI
    # escape sequence appears anywhere in the message. A bare URL still auto-embeds
    # as a clickable link (wrapped in <> to suppress the preview-card embed) and has
    # shown none of that fragility. Only the Cible gets a link at all (the target
    # being synced to, not one of the attackers) - per-row colonie links aren't
    # valuable enough to bother with here.
    header = (
        f"""Cible: **{player["player_name"]}** ({player["colo_name"]}) [{player["alliance"]}] [{":".join(str(i) for i in base_pos)}]\n"""
        f"""Attack: <{attack_url}>\n"""
        f"""VA: {va}\n"""
        f"""Heure de départ: {depart.strftime("%H:%M:%S")} - TDC: {nm.utils.format_naw_int(base_tdc)}\n"""
    )
    cible_alliance = player["alliance"]
    widths = _discord_row_widths(targets)
    ansi_rows = "\n".join(
        _format_discord_row(h, d, j, c, a, p, t, cible_alliance, widths, use_ansi=True)
        for h, d, j, c, a, p, t in targets.itertuples(index=False)
    )
    copy_data = header + "\n```ansi\n" + ansi_rows + "\n```"
    if len(copy_data) > _DISCORD_MESSAGE_LIMIT:
        # An unrecognized ```ansi block just shows as a plain monospace code block on
        # clients that don't support it (confirmed - this is exactly what happens on
        # mobile, which doesn't render ANSI colors) - but past Discord's 2000-
        # character message limit, it falls back to a file upload instead, whose
        # preview stays readable for plain text but is garbled by raw ANSI escape
        # bytes. So drop ANSI past that limit - still fenced (unlike
        # format_copy_data_text, which never uses a code block) so the row alignment
        # survives, just not bolded/colored.
        plain_rows = "\n".join(
            _format_discord_row(h, d, j, c, a, p, t, cible_alliance, widths, use_ansi=False)
            for h, d, j, c, a, p, t in targets.itertuples(index=False)
        )
        copy_data = header + "\n```\n" + plain_rows + "\n```"
    return copy_data


def format_copy_data_table(
    targets: pd.DataFrame, player: pd.Series, va: int, depart: dt.datetime, base_url: str
) -> str:
    """Same header as format_copy_data_text, followed by a hand-authored [table]
    BBCode block: one header row of column names, one row per target. Forum-only,
    BBCode-only output - Joueur/Alli/Colonie cells carry links, Durée/TDC/Pos are
    aligned, none of which would make sense pasted anywhere else."""
    # Hand-authored rather than produced via the forum's paste-from-Sheets
    # auto-converter: that converter only recognizes HTML starting with <table>, and
    # even then only ever header-styles the first row - everything else becomes a
    # plain data row. It can't make this shape, so we build the exact BBCode grammar
    # it itself produces instead.
    header_cells = " ".join(f"[th]{col}[/th]" for col in targets.columns)
    lines = [_format_header(player, va, depart, base_url=base_url), "[table]", f"[tr] {header_cells} [/tr]"]
    for h, d, j, c, a, p, t in targets.itertuples(index=False):
        x, y = p.split(":")
        colonie_link = _format_colonie_link(base_url=base_url, x=x, y=y, colo_name=c)
        # One line per row, cells space-separated, rather than one tag per line: the
        # forum's editor is a plain textarea, so the converter's own one-tag-per-line
        # style would be unreadable here before the post goes out.
        row_cells = " ".join(
            [
                f"[td][b]{h}[/b][/td]",
                f"[td][right]{d}[/right][/td]",  # right-aligned
                f"[td][joueur]{j}[/joueur][/td]",
                f"[td]{colonie_link}[/td]",  # linked to the attack page
                f"[td][alliance]{a}[/alliance][/td]",
                f"[td][center]{p}[/center][/td]",  # centered
                f"[td][right]{t}[/right][/td]",  # right-aligned
            ]
        )
        lines.append(f"[tr] {row_cells} [/tr]")
    lines.append("[/table]")
    return "\n".join(lines)
