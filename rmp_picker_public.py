#!/usr/bin/env python3
"""
RMP Professor Picker — Analyze Rate My Professor data and recommend the best professor.

Works with any school listed on RateMyProfessors.com.

Usage:
    python rmp_picker.py \\
        --school "University of Texas at Austin" \\
        --course "CS 314" \\
        --professors "Smith, Johnson, Williams" \\
        --top-n 3 \\
        --output professor_recommendations.md

Requirements:
    pip install RateMyProfessorAPI
"""

import argparse
import math
import subprocess
import sys
from datetime import datetime


# ---------------------------------------------------------------------------
# Dependency management
# ---------------------------------------------------------------------------
def ensure_deps():
    try:
        import ratemyprofessor
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "RateMyProfessorAPI",
             "--break-system-packages", "-q"],
        )
        import ratemyprofessor
    return ratemyprofessor


# ---------------------------------------------------------------------------
# Data retrieval
# ---------------------------------------------------------------------------
def lookup_school(rmp, school_name: str):
    """Return a School object or None."""
    school = rmp.get_school_by_name(school_name)
    if school is None:
        schools = rmp.get_schools_by_name(school_name)
        if schools:
            school = schools[0]
    return school


def lookup_professor(rmp, school, name: str) -> dict:
    """
    Look up a single professor and return a dict of their RMP data.
    Returns a dict with an 'error' key if not found.
    """
    name = name.strip()
    if not name:
        return {"name": name, "error": "Empty name"}

    prof = rmp.get_professor_by_school_and_name(school, name)

    if prof is None:
        profs = rmp.get_professors_by_school_and_name(school, name)
        if profs:
            prof = profs[0]
        else:
            return {"name": name, "error": "Not found on RateMyProfessor"}

    return {
        "name": prof.name,
        "department": prof.department,
        "school": prof.school.name,
        "rating": prof.rating,
        "difficulty": prof.difficulty,
        "num_ratings": prof.num_ratings,
        "would_take_again": prof.would_take_again,  # can be None
        "error": None,
    }


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------
def compute_composite(prof: dict) -> float:
    """
    Composite score that balances rating quality with review confidence.

    Formula:
        base            = rating (0–5)
        confidence      = min(1.0, log2(num_ratings + 1) / log2(30))
        take_again_bonus = 1 + 0.15 * (would_take_again / 100)   [if available]
        difficulty_adj  = 1 - 0.05 * max(0, difficulty - 3.0)
        composite       = base * confidence * take_again_bonus * difficulty_adj

    Why?
        A 4.5 with 50 ratings beats a 5.0 with 2 ratings.
        "Would take again" is the strongest signal of real satisfaction.
        Extreme difficulty gets a small penalty, all else equal.
    """
    if prof.get("error"):
        return 0.0

    rating = prof.get("rating") or 0.0
    num_ratings = prof.get("num_ratings") or 0
    difficulty = prof.get("difficulty") or 2.5
    would_take_again = prof.get("would_take_again")

    # Confidence: log scale, saturates ~30 reviews
    if num_ratings > 0:
        confidence = min(1.0, math.log2(num_ratings + 1) / math.log2(30))
    else:
        confidence = 0.0

    # Would-take-again bonus (up to +15%)
    if would_take_again is not None and would_take_again > 0:
        ta_bonus = 1.0 + 0.15 * (would_take_again / 100.0)
    else:
        ta_bonus = 1.0

    # Difficulty adjustment: slight penalty above 3.0
    diff_adj = 1.0 - 0.05 * max(0.0, difficulty - 3.0)

    return round(rating * confidence * ta_bonus * diff_adj, 3)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def rating_bar(value: float, max_val: float = 5.0, length: int = 10) -> str:
    """Text-based rating bar for the markdown report."""
    if value is None or value == 0:
        return "N/A"
    filled = round((value / max_val) * length)
    return "█" * filled + "░" * (length - filled) + f" {value:.1f}/{max_val:.0f}"


def generate_report(course: str, school_name: str, professors: list[dict], top_n: int) -> str:
    """Generate the full markdown recommendation report."""

    found = [p for p in professors if not p.get("error")]
    not_found = [p for p in professors if p.get("error")]

    found.sort(key=lambda p: p["composite"], reverse=True)
    top_n = min(top_n, len(found))
    now = datetime.now().strftime("%B %d, %Y")

    lines = []

    # ── Header ────────────────────────────────────────────────────────────
    lines.append(f"# Professor Recommendations: {course}")
    lines.append(f"**School:** {school_name}  ")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Professors analyzed:** {len(found)} found, {len(not_found)} not found on RMP")
    lines.append("")

    # ── Top Pick ──────────────────────────────────────────────────────────
    if found:
        top = found[0]
        lines.append("---")
        lines.append("")
        lines.append("## 🏆 Top Pick")
        lines.append("")
        lines.append(f"### {top['name']}")
        lines.append(f"**Department:** {top.get('department', 'N/A')}  ")
        lines.append(f"**Rating:** {rating_bar(top['rating'])}  ")
        lines.append(f"**Difficulty:** {rating_bar(top['difficulty'])}  ")
        lines.append(f"**Total Ratings:** {top['num_ratings']}  ")
        wta = top.get("would_take_again")
        lines.append(f"**Would Take Again:** {f'{wta:.0f}%' if wta is not None else 'N/A'}  ")
        lines.append(f"**Composite Score:** {top['composite']:.2f}  ")
        lines.append("")

        reasons = []
        if top["rating"] >= 4.0:
            reasons.append(f"high overall rating ({top['rating']:.1f}/5)")
        if top["num_ratings"] >= 20:
            reasons.append(f"strong sample size ({top['num_ratings']} reviews)")
        if wta is not None and wta >= 75:
            reasons.append(f"{wta:.0f}% of students would take again")
        if top.get("difficulty") and top["difficulty"] <= 3.5:
            reasons.append(f"manageable difficulty ({top['difficulty']:.1f}/5)")

        rationale = ", ".join(reasons) if reasons else "highest composite score balancing rating, review count, and student satisfaction"
        lines.append(f"> **Why this pick?** {top['name']} stands out with {rationale}.")
        lines.append("")

    # ── Rankings Table ────────────────────────────────────────────────────
    if len(found) > 1:
        lines.append("---")
        lines.append("")
        lines.append("## Rankings")
        lines.append("")
        lines.append("| Rank | Professor | Rating | Difficulty | Reviews | Would Take Again | Composite |")
        lines.append("|:----:|:----------|:------:|:----------:|:-------:|:----------------:|:---------:|")
        for i, p in enumerate(found[:top_n], 1):
            wta_str = f"{p['would_take_again']:.0f}%" if p.get("would_take_again") is not None else "N/A"
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, str(i))
            lines.append(
                f"| {medal} | {p['name']} | {p['rating']:.1f} | {p['difficulty']:.1f} | "
                f"{p['num_ratings']} | {wta_str} | {p['composite']:.2f} |"
            )
        lines.append("")

    # ── Detail Cards ──────────────────────────────────────────────────────
    if len(found) > 1:
        lines.append("---")
        lines.append("")
        lines.append("## Detailed Profiles")
        lines.append("")
        for i, p in enumerate(found[:top_n], 1):
            lines.append(f"### {i}. {p['name']}")
            lines.append(f"- **Department:** {p.get('department', 'N/A')}")
            lines.append(f"- **Rating:** {rating_bar(p['rating'])}")
            lines.append(f"- **Difficulty:** {rating_bar(p['difficulty'])}")
            lines.append(f"- **Total Ratings:** {p['num_ratings']}")
            wta = p.get("would_take_again")
            lines.append(f"- **Would Take Again:** {f'{wta:.0f}%' if wta is not None else 'N/A'}")
            lines.append(f"- **Composite Score:** {p['composite']:.2f}")
            lines.append("")

    # ── Not Found ─────────────────────────────────────────────────────────
    if not_found:
        lines.append("---")
        lines.append("")
        lines.append("## ⚠️ Professors Not Found on RMP")
        lines.append("")
        for p in not_found:
            lines.append(f"- **{p['name']}** — {p['error']}")
        lines.append("")
        lines.append("> These professors may be new, use a different name on RMP, or teach at a branch campus listed separately.")
        lines.append("")

    # ── Methodology ───────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("The composite score balances multiple factors so that raw rating alone doesn't dominate:")
    lines.append("")
    lines.append("```")
    lines.append("composite = rating × confidence × take_again_bonus × difficulty_adjustment")
    lines.append("")
    lines.append("  confidence        = min(1.0, log₂(num_ratings + 1) / log₂(30))")
    lines.append("  take_again_bonus  = 1 + 0.15 × (would_take_again / 100)")
    lines.append("  difficulty_adj    = 1 − 0.05 × max(0, difficulty − 3.0)")
    lines.append("```")
    lines.append("")
    lines.append("- A professor with a 5.0 rating but only 2 reviews will score lower than a 4.3 with 80 reviews.")
    lines.append("- \"Would take again\" percentage provides a strong signal of real student satisfaction.")
    lines.append("- Difficulty above 3.0 incurs a small penalty — very hard courses can be great, but all else equal, manageable difficulty is preferred.")
    lines.append("")
    lines.append(f"*Data sourced from [RateMyProfessors.com](https://www.ratemyprofessors.com) on {now}.*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="RMP Professor Picker — find the best professor for your course",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rmp_picker.py --school "MIT" --course "6.006" --professors "Demaine, Devadas"
  python rmp_picker.py --school "UCLA" --course "PSYCH 100A" --professors "Lee, Park, Chen" --top-n 2
        """,
    )
    parser.add_argument("--school", required=True,
                        help="School name as listed on RateMyProfessors.com")
    parser.add_argument("--course", required=True,
                        help="Course name/number (e.g. 'MATH 152', 'Intro to CS')")
    parser.add_argument("--professors", required=True,
                        help="Comma-separated list of professor last names or full names")
    parser.add_argument("--top-n", type=int, default=3,
                        help="Number of recommendations to show (default: 3)")
    parser.add_argument("--output", default="professor_recommendations.md",
                        help="Output markdown file path (default: professor_recommendations.md)")

    args = parser.parse_args()
    rmp = ensure_deps()

    # Look up school
    print(f"🔍 Looking up school: {args.school}...")
    school = lookup_school(rmp, args.school)
    if school is None:
        print(f"❌ School '{args.school}' not found on RateMyProfessors.", file=sys.stderr)
        print("   Tip: Try the full official name (e.g. 'Massachusetts Institute of Technology' instead of 'MIT').", file=sys.stderr)
        sys.exit(1)
    print(f"✅ Found: {school.name}")

    # Look up each professor
    names = [n.strip() for n in args.professors.split(",") if n.strip()]
    print(f"\n📊 Analyzing {len(names)} professor(s)...\n")

    professors = []
    for name in names:
        print(f"  {name}...", end=" ", flush=True)
        data = lookup_professor(rmp, school, name)
        if data.get("error"):
            print(f"⚠  {data['error']}")
        else:
            data["composite"] = compute_composite(data)
            print(f"✓  Rating={data['rating']:.1f}  Reviews={data['num_ratings']}  Composite={data['composite']:.2f}")
        professors.append(data)

    # Generate report
    report = generate_report(args.course, school.name, professors, args.top_n)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ Report saved to: {args.output}")


if __name__ == "__main__":
    main()
