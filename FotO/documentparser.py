import os
import re
from docx import Document

# Configuration
DOCX_PATH = "FotOS2E12.docx"
OUTPUT_DIR = "episodes"
INDEX_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "episodeindex.html")

EPISODE_HEADER_PATTERN = re.compile(r"^S(\d+)E(\d+):\s*(.+)$", re.IGNORECASE)

# Names/Subtitles for Seasons (Add or edit as needed)
SEASON_NAMES = {
    "1": "Rusthenge",
    "2": "Seven Dooms"
}

def escape_html(text):
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )

def generate_episode_html(season, episode, title, paragraphs):
    story_paragraphs = []
    for p in paragraphs:
        clean_p = p.strip()
        if not clean_p or set(clean_p).issubset({"-", "_", "*", "="}):
            continue
        story_paragraphs.append(f"    <p>{escape_html(clean_p)}</p>")

    story_body = "\n".join(story_paragraphs)
    default_image = f"media/images/default{season}.png"

    return f"""<h2 class="episode-title">Season {season}, Episode {episode}: {escape_html(title)}</h2>

<!-- DEFAULT IMAGE STUB -->
<section class="gallery-section">
    <div class="image-grid">
        <div class="gallery-item">
            <img src="{default_image}" alt="Season {season} Episode {episode}" onerror="this.src='https://via.placeholder.com/400x250?text=Default+Image'">
        </div>
    </div>
</section>

<!-- MAIN STORY TEXT -->
<div class="story-text">
{story_body}
</div>

<!-- COLLAPSIBLE GM NOTES STUB -->
<button class="collapsible-btn">GM Notes <span class="icon">+</span></button>
<div class="collapsible-content">
    <div class="gm-notes">
        <strong>GM Notes:</strong> Notes for Season {season}, Episode {episode}.
    </div>
</div>
"""

def generate_index_html(episodes):
    """Builds the episode index snippet broken down by collapsible seasons."""
    # Group episodes by Season
    seasons = {}
    for ep in episodes:
        s = ep["season"]
        if s not in seasons:
            seasons[s] = []
        seasons[s].append(ep)

    index_lines = []
    
    # Iterate through seasons in numerical order
    for s_num in sorted(seasons.keys(), key=int):
        season_title = SEASON_NAMES.get(str(s_num), f"Season {s_num}")
        # Keep Season 1 open by default
        open_attr = " open" if str(s_num) == "1" else ""
        
        index_lines.append(f'<details class="season-accordion"{open_attr}>')
        index_lines.append(f'    <summary class="season-title">Season {s_num}: {escape_html(season_title)}</summary>')
        index_lines.append('    <ul class="nav-list episode-list">')
        
        for ep in seasons[s_num]:
            filename = ep["filename"]
            title = escape_html(ep["title"])
            ep_num = ep["episode"]
            index_lines.append(
                f'        <li><button class="ep-btn" data-src="episodes/{filename}">Ep. {ep_num}: {title}</button></li>'
            )
            
        index_lines.append('    </ul>')
        index_lines.append('</details>\n')

    return "\n".join(index_lines)

def parse_docx(docx_file):
    if not os.path.exists(docx_file):
        print(f"Error: Could not find '{docx_file}'. Check the file path.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    doc = Document(docx_file)
    current_ep = None
    all_episodes = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        match = EPISODE_HEADER_PATTERN.match(text)
        
        if match:
            if current_ep:
                save_episode(current_ep)
                all_episodes.append(current_ep)

            season_num = match.group(1)
            episode_num = match.group(2)
            ep_title = match.group(3).strip()
            filename = f"s{season_num}e{episode_num}.html"
            
            current_ep = {
                "season": season_num,
                "episode": episode_num,
                "title": ep_title,
                "filename": filename,
                "paragraphs": []
            }
        else:
            if current_ep:
                current_ep["paragraphs"].append(text)

    if current_ep:
        save_episode(current_ep)
        all_episodes.append(current_ep)

    # Generate and write episodeindex.html
    index_content = generate_index_html(all_episodes)
    with open(INDEX_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(index_content)

    print(f"\nGenerated {len(all_episodes)} episode HTML files.")
    print(f"Generated index file at: {INDEX_OUTPUT_PATH}")

def save_episode(ep):
    filepath = os.path.join(OUTPUT_DIR, ep["filename"])
    content = generate_episode_html(ep["season"], ep["episode"], ep["title"], ep["paragraphs"])
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    parse_docx(DOCX_PATH)