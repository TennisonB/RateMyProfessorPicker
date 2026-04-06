---
name: rmp-prof-picker
description: >
  Analyze and recommend the best professor for a college course using Rate My Professor data.
  Use this skill whenever the user asks to compare professors, pick a professor, find the best
  professor for a class, evaluate professors, or mentions "Rate My Professor", "RMP", "who should
  I take for [course]", "best professor for [course]", "professor recommendations", or
  "professor ratings". Also trigger when the user provides a list of professor names and wants
  them ranked or compared. This skill produces a polished markdown report with a top pick and
  ranked recommendations. Default school is Texas A&M University but supports any school on RMP.
---

# RMP Professor Picker

Analyze Rate My Professor data to recommend the best professor for a given course.

## Workflow

1. **Gather inputs** from the user (ask if not provided):
   - **School name** — any school listed on RateMyProfessors.com. If the user's school is stored in Claude's memory, use that as the default.
   - **Course name** — e.g. "MATH 152", "Intro to Psychology" (used for the report header)
   - **Professor names** — comma-separated list of professors the user is choosing between
   - **Number of recommendations** — how many to rank in the report (default: 3, max: length of list)

2. **Run the analysis script**:
   ```bash
   python /path/to/skill/scripts/rmp_picker.py \
     --school "University Name" \
     --course "COURSE 101" \
     --professors "Smith, Johnson, Williams" \
     --top-n 3 \
     --output /mnt/user-data/outputs/professor_recommendations.md
   ```

3. **Present the output** markdown file to the user.

## How the Script Works

The script (`scripts/rmp_picker.py`):

1. Installs `RateMyProfessorAPI` if not present
2. Looks up the school on RMP by name
3. For each professor name, searches RMP and retrieves:
   - Overall rating (out of 5)
   - Difficulty rating (out of 5)
   - Number of ratings
   - "Would take again" percentage
   - Department
4. Computes a **composite score** that balances quality with confidence:
   - `composite = rating × confidence_weight × take_again_bonus × difficulty_adjustment`
   - **Confidence weight**: `min(1.0, log2(num_ratings + 1) / log2(30))` — professors with fewer than ~30 reviews are penalized; more reviews = more trust
   - **Take-again bonus**: `1 + 0.15 × (would_take_again / 100)` if available, else neutral
   - **Difficulty adjustment**: `1 - 0.05 × max(0, difficulty - 3.0)` — slight penalty for difficulty above 3.0
5. Ranks professors by composite score
6. Generates a markdown report with:
   - Header with course and school info
   - **🏆 Top Pick** section with rationale
   - Ranked table of all analyzed professors
   - Individual professor detail cards
   - Methodology note

## Composite Score Philosophy

A raw 5.0 rating from 2 reviews is less trustworthy than a 4.3 from 80 reviews.
The algorithm rewards:
- **High ratings** (most important factor)
- **Many reviews** (confidence — logarithmic scale so diminishing returns past ~50)
- **High "would take again"** (students voting with their feet)
- Slight penalty for **very high difficulty** (above 3.0)

## Input Modes

### Mode 1: Professor Names (Primary)
User provides professor names. The skill looks them up on RMP.

### Mode 2: Screenshot/Image Input
If the user uploads a screenshot of a class schedule (e.g. from their university's registration portal), Claude should:
1. Read the image and extract professor names from it
2. Pass those names to the script

## Edge Cases

- **Professor not found on RMP**: Report them as "Not Found" with a note
- **Too few ratings** (<3): Flag as "Insufficient Data" but still include
- **Duplicate/ambiguous names**: The script picks the best match by department if possible
- **School not found**: Error with suggestion to check spelling or try alternate names (e.g. "MIT" vs "Massachusetts Institute of Technology")
