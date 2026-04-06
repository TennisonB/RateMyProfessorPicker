# 🎓 RMP Professor Picker

A [Claude Skill](https://support.anthropic.com/en/articles/claude-ai-skills) that analyzes [Rate My Professor](https://www.ratemyprofessors.com) data to recommend the best professor for any college course.

Give it a list of professors and a school — it pulls their ratings, reviews, and difficulty scores, then ranks them using a composite algorithm that values review volume and student satisfaction alongside raw rating.

## Quick Start

### As a Claude Skill

1. Download the `.skill` file from [Releases](../../releases)
2. Drag it into a Claude conversation or install it via Settings → Skills
3. Ask: *"Who should I take for MATH 152? My options are Kahlig, Fulling, and Stecher"*

### Standalone CLI

```bash
pip install RateMyProfessorAPI

python scripts/rmp_picker.py \
  --school "University of Texas at Austin" \
  --course "CS 314" \
  --professors "Scott, Gheith, Young" \
  --top-n 3 \
  --output recommendations.md
```

## How It Works

The tool queries each professor on RateMyProfessors.com and computes a **composite score**:

```
composite = rating × confidence × take_again_bonus × difficulty_adjustment
```

| Factor | Formula | What it does |
|--------|---------|-------------|
| **Confidence** | `min(1.0, log₂(n+1) / log₂(30))` | Penalizes professors with very few reviews. Saturates around 30 reviews. |
| **Take-again bonus** | `1 + 0.15 × (would_take_again / 100)` | Up to 15% boost for high "would take again" percentage. |
| **Difficulty adj.** | `1 − 0.05 × max(0, difficulty − 3.0)` | Small penalty for difficulty above 3.0/5.0. |

**Why not just sort by rating?** A 5.0 from 2 reviews is noise. A 4.3 from 80 reviews is signal. This formula balances both.

## Output

The tool generates a polished Markdown report containing:

- 🏆 **Top Pick** with rationale
- **Rankings table** with medals (🥇🥈🥉)
- **Detailed profiles** for each professor
- ⚠️ **Not-found list** for professors missing from RMP
- **Methodology section** explaining the scoring

## Examples

```bash
# Compare physics professors at Georgia Tech
python scripts/rmp_picker.py \
  --school "Georgia Institute of Technology" \
  --course "PHYS 2211" \
  --professors "Murray, Greco, Jarrio"

# Rank CS professors at Stanford, show top 5
python scripts/rmp_picker.py \
  --school "Stanford University" \
  --course "CS 106A" \
  --professors "Sahami, Schwarz, Cain, Piech, Troccoli" \
  --top-n 5
```

## Using with Claude

When installed as a skill, Claude will:

1. Ask for your school, course, and professor names (or extract names from a screenshot you upload)
2. Run the analysis script
3. Present the Markdown report

You can say things like:
- *"Compare these professors for me: Smith, Jones, Lee at UCLA for ECON 101"*
- *"Who's the best CHEM 101 professor? Here's my schedule screenshot"* (attach image)
- *"Rate my professor options for CS 161 at SJSU"*

## Requirements

- Python 3.5+
- [`RateMyProfessorAPI`](https://github.com/Nobelz/RateMyProfessorAPI) (auto-installed by the skill)

## Project Structure

```
rmp-prof-picker/
├── SKILL.md              # Claude skill instructions
├── scripts/
│   └── rmp_picker.py     # Analysis script
└── README.md             # This file
```

## License

MIT

## Credits

- [RateMyProfessorAPI](https://github.com/Nobelz/RateMyProfessorAPI) by Nobelz — Python wrapper for RMP's GraphQL API
- Data from [RateMyProfessors.com](https://www.ratemyprofessors.com)
