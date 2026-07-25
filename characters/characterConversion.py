import json
import re
from html import escape


def safe_get(data, *keys, default=None):
    """Safely traverses nested dicts, guarding against None values along the path."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def strip_inline_styles(html_content: str) -> str:
    """Strips inline style attributes to prevent layout/font glitches."""
    if not isinstance(html_content, str):
        return ""
    clean = re.sub(r'\s*style="[^"]*"', '', html_content, flags=re.IGNORECASE)
    clean = re.sub(r"\s*style='[^']*'", "", clean, flags=re.IGNORECASE)
    return clean


def format_rank(rank: int) -> str:
    """Converts PF2e proficiency ranks (0-4) to text labels."""
    ranks = {0: "Untrained", 1: "Trained", 2: "Expert", 3: "Master", 4: "Legendary"}
    return ranks.get(rank, "Untrained")


def get_rank_bonus(rank: int) -> int:
    """Returns standard PF2e rank bonuses (0, 2, 4, 6, 8)."""
    bonuses = {0: 0, 1: 2, 2: 4, 3: 6, 4: 8}
    return bonuses.get(rank, 0)


def calculate_ability_modifiers(system_data: dict) -> dict:
    """
    Extracts or calculates final ability modifiers across all Foundry PF2e schema versions:
    1. Direct integers/dicts in system.abilities.<attr> (PF2e v10/v11/v12+)
    2. Derived from legacy score (system.abilities.<attr>.value)
    3. Traverses system.build.attributes.boosts and flaws
    """
    mods = {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0}
    abilities_obj = safe_get(system_data, "abilities", default={})

    # 1. Read pre-calculated values directly from system.abilities
    if isinstance(abilities_obj, dict):
        has_valid_data = False
        for k in mods.keys():
            attr_val = abilities_obj.get(k)
            
            if isinstance(attr_val, int):
                mods[k] = attr_val
                has_valid_data = True
            elif isinstance(attr_val, dict):
                if "mod" in attr_val and isinstance(attr_val["mod"], int):
                    mods[k] = attr_val["mod"]
                    has_valid_data = True
                elif "value" in attr_val and isinstance(attr_val["value"], int):
                    mods[k] = (attr_val["value"] - 10) // 2
                    has_valid_data = True
        
        if has_valid_data:
            return mods

    # 2. Parse raw build boosts if system.abilities is empty or unpopulated
    boost_groups = safe_get(system_data, "build", "attributes", "boosts", default={})
    flaw_groups = safe_get(system_data, "build", "attributes", "flaws", default={})

    def flatten_abilities(data):
        found = []
        if isinstance(data, str) and data.lower() in mods:
            found.append(data.lower())
        elif isinstance(data, list):
            for item in data:
                found.extend(flatten_abilities(item))
        elif isinstance(data, dict):
            for val in data.values():
                found.extend(flatten_abilities(val))
        return found

    if isinstance(boost_groups, dict):
        for attr in flatten_abilities(boost_groups):
            if mods[attr] < 4:
                mods[attr] += 1
            else:
                mods[attr] += 0.5  # Partial boost handling above +4

    if isinstance(flaw_groups, dict):
        for attr in flatten_abilities(flaw_groups):
            mods[attr] -= 1

    return {k: int(v) for k, v in mods.items()}


SKILL_ABILITY_MAP = {
    "acrobatics": "dex", "arcana": "int", "athletics": "str",
    "crafting": "int", "deception": "cha", "diplomacy": "cha",
    "intimidation": "cha", "medicine": "wis", "nature": "wis",
    "occultism": "int", "performance": "cha", "religion": "wis",
    "society": "int", "stealth": "dex", "survival": "wis", "thievery": "dex"
}


def main():
    json_path = "thomasVTT.json"
    html_path = "thomas.html"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    system = data.get("system") if isinstance(data.get("system"), dict) else {}
    details = safe_get(system, "details", default={})
    saves = safe_get(system, "saves", default={})
    skills = safe_get(system, "skills", default={})
    items = data.get("items") if isinstance(data.get("items"), list) else []

    # Basic Info
    name = data.get("name", "Hans Kräfte")
    level = safe_get(details, "level", "value", default=5)
    ancestry = safe_get(details, "ancestry", "name", default="Gnome")
    heritage = safe_get(details, "heritage", "name", default="Wellspring Gnome")
    background = safe_get(details, "background", "name", default="Runelord Scholar")
    class_name = safe_get(details, "class", "name", default="Wizard")

    # Vitals
    hp = safe_get(system, "attributes", "hp", "max", default=53)
    speed = safe_get(system, "attributes", "speed", "total", default=25)
    hero_points = safe_get(system, "resources", "heroPoints", "value", default=1)

    # Ability Modifiers
    ability_mods = calculate_ability_modifiers(system)

    abilities_html = ""
    for k in ["str", "dex", "con", "int", "wis", "cha"]:
        mod = ability_mods.get(k, 0)
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        abilities_html += f"""
        <div class="stat-box">
            <span>{k.upper()}</span>
            <strong>{mod_str}</strong>
        </div>"""

    # Saving Throws Mapping: Fortitude (Trained=1), Reflex (Expert=2), Will (Expert=2)
    saves_map = [
        ("fortitude", "Fortitude", "con", 1),
        ("reflex", "Reflex", "dex", 2),
        ("will", "Will", "wis", 2)
    ]
    saves_html = ""
    for s_key, s_label, default_attr, fallback_rank in saves_map:
        s_data = safe_get(saves, s_key, default={})

        rank = safe_get(s_data, "rank", default=fallback_rank) if isinstance(s_data, dict) else fallback_rank
        attr_key = safe_get(s_data, "ability", default=default_attr) if isinstance(s_data, dict) else default_attr

        ab_mod = ability_mods.get(attr_key, 0)
        rank_bonus = get_rank_bonus(rank)
        lvl_bonus = level if rank > 0 else 0

        total = ab_mod + rank_bonus + lvl_bonus
        rank_str = format_rank(rank)

        saves_html += f"""
        <div class="stat-box">
            <span>{s_label}</span>
            <strong>+{total} ({rank_str})</strong>
        </div>"""

    # Calculate Trained & Expert Skills
    skills_html = ""
    if isinstance(skills, dict):
        sorted_skills = sorted(
            skills.items(),
            key=lambda x: safe_get(x[1], "label", default=x[0]) if isinstance(x[1], dict) else str(x[0])
        )
        for sk_key, sk_data in sorted_skills:
            if isinstance(sk_data, dict):
                rank = safe_get(sk_data, "rank", default=0)
                if rank > 0:
                    sk_name = safe_get(sk_data, "label", default=sk_key.capitalize())
                    attr_key = safe_get(sk_data, "ability", default=SKILL_ABILITY_MAP.get(sk_key.lower(), "str"))

                    ab_mod = ability_mods.get(attr_key, 0)
                    rank_bonus = get_rank_bonus(rank)
                    lvl_bonus = level if rank > 0 else 0

                    total = ab_mod + rank_bonus + lvl_bonus
                    rank_str = format_rank(rank)
                    skills_html += f"<li><strong>{escape(sk_name)}:</strong> {rank_str} (+{total})</li>"

    # Categorize Items
    spells = []
    feats = []
    equipment = []

    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        item_name = item.get("name", "Unknown Item")
        if item_type == "spell":
            spell_rank = safe_get(item, "system", "level", "value", default=0)
            spells.append((spell_rank, item_name))
        elif item_type == "feat":
            feats.append(item_name)
        elif item_type in ["equipment", "weapon", "armor"]:
            equipment.append(item_name)

    # Build Feats HTML
    feats_html = ""
    if feats:
        feats.sort()
        feats_html = "<ul class='feat-list'>" + "".join([f"<li>{escape(f)}</li>" for f in feats]) + "</ul>"
    else:
        feats_html = "<p>No feats listed.</p>"

    # Sort spells by rank & build Expandable HTML
    spells.sort(key=lambda x: x[0])
    spell_groups = {}
    for rank, s_name in spells:
        group_title = "Cantrips" if rank == 0 else f"Rank {rank}"
        spell_groups.setdefault(group_title, []).append(s_name)

    spells_html = ""
    for rank_label, spell_list in spell_groups.items():
        spells_html += f"""
        <details class="spell-group">
            <summary><strong>{rank_label}</strong> ({len(spell_list)} spells)</summary>
            <ul>
                {"".join([f"<li>{escape(sp)}</li>" for sp in spell_list])}
            </ul>
        </details>"""

    # Narrative Extraction
    bio = safe_get(details, "biography", default={})
    raw_backstory = bio.get("backstory") if isinstance(bio, dict) else ""
    if isinstance(raw_backstory, dict):
        raw_backstory = raw_backstory.get("value", "")
    backstory = strip_inline_styles(str(raw_backstory) if raw_backstory else "")

    edicts = bio.get("edicts", "") if isinstance(bio, dict) else ""
    if isinstance(edicts, dict):
        edicts = edicts.get("value", "")

    anathema = bio.get("anathema", "") if isinstance(bio, dict) else ""
    if isinstance(anathema, dict):
        anathema = anathema.get("value", "")

    # Assemble Output HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape(name)} | Character Sheet</title>
    <style>
        :root {{
            --bg-color: #1a1a1c;
            --card-bg: #242428;
            --accent-color: #4a6fa5;
            --text-color: #e1e1e6;
            --text-muted: #a0a0b0;
            --border-color: #383840;
        }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 2rem;
        }}
        .char-header {{
            text-align: center;
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1rem;
        }}
        .char-container {{
            display: grid;
            grid-template-columns: 280px 1fr;
            gap: 2rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .char-sidebar {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}
        .char-section {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1.5rem;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 0.75rem;
        }}
        .stat-box {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 0.5rem;
            text-align: center;
            display: flex;
            flex-direction: column;
        }}
        .stat-box span {{
            font-size: 0.75rem;
            color: var(--text-muted);
        }}
        .stat-box strong {{
            font-size: 1.1rem;
            color: #fff;
        }}
        .skill-list, .feat-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 0.5rem;
            list-style: none;
            padding: 0;
        }}
        details.spell-group {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 0.5rem 1rem;
            margin-bottom: 0.5rem;
            cursor: pointer;
        }}
        details.spell-group summary {{
            font-size: 1rem;
            color: var(--text-color);
            outline: none;
        }}
        details.spell-group ul {{
            margin-top: 0.5rem;
            padding-left: 1.2rem;
        }}
        ul {{
            margin-top: 0.5rem;
            padding-left: 1.2rem;
        }}
        .portrait-placeholder {{
            width: 100%;
            height: 320px;
            background: #2a2a30;
            border: 2px solid var(--accent-color);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>

    <header class="char-header">
        <h1>{escape(name)}</h1>
        <p>Level {level} {escape(heritage)} {escape(class_name)}</p>
    </header>

    <main class="char-container">
        <aside class="char-sidebar">
            <div class="portrait-placeholder">
                <p>[ Portrait ]</p>
            </div>

            <div class="char-section">
                <h3>Vitals</h3>
                <p><strong>HP:</strong> {hp}</p>
                <p><strong>Speed:</strong> {speed} ft</p>
                <p><strong>Hero Points:</strong> {hero_points}</p>
            </div>

            <div class="char-section">
                <h3>Heritage & Background</h3>
                <p><strong>Ancestry:</strong> {escape(ancestry)}</p>
                <p><strong>Heritage:</strong> {escape(heritage)}</p>
                <p><strong>Background:</strong> {escape(background)}</p>
            </div>
        </aside>

        <div class="char-main">
            <section class="char-section">
                <h2>Ability Modifiers</h2>
                <div class="stat-grid">
                    {abilities_html}
                </div>
            </section>

            <section class="char-section">
                <h2>Saving Throws</h2>
                <div class="stat-grid">
                    {saves_html}
                </div>
            </section>

            <section class="char-section">
                <h2>Trained & Expert Skills</h2>
                <ul class="skill-list">
                    {skills_html if skills_html else "<li>No trained skills parsed.</li>"}
                </ul>
            </section>

            <section class="char-section">
                <h2>Feats & Special Abilities</h2>
                {feats_html}
            </section>

            <section class="char-section">
                <h2>Spellbook & Prepared Spells</h2>
                {spells_html if spells_html else "<p>No spells found in export.</p>"}
            </section>

            {(f'<section class="char-section"><h2>Edicts & Anathema</h2><p><strong>Edicts:</strong> {escape(str(edicts))}</p><p><strong>Anathema:</strong> {escape(str(anathema))}</p></section>') if edicts or anathema else ''}

            <section class="char-section">
                <h2>Backstory</h2>
                <div>
                    {backstory if backstory else "<p>No backstory recorded.</p>"}
                </div>
            </section>
        </div>
    </main>

</body>
</html>"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Successfully generated {html_path} from {json_path}")


if __name__ == "__main__":
    main()