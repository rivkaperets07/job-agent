from src.models import Classification

TOP_APPLY_COUNT = 5


def build_digest_html(classifications: list[Classification], date_str: str) -> str:
    relevant = [c for c in classifications if c.relevant and not c.is_likely_fake]
    fakes = [c for c in classifications if c.is_likely_fake]
    top_apply = sorted(
        (c for c in classifications if not c.is_likely_fake),
        key=lambda c: c.apply_probability,
        reverse=True,
    )[:TOP_APPLY_COUNT]

    parts = [f"<h1>Resumen de trabajo — {date_str}</h1>"]

    parts.append(f"<h2>Más relevantes ({len(relevant)})</h2>")
    parts.append(_section(relevant, show_apply=False))

    parts.append(f"<h2>Mayor probabilidad de aplicar ({len(top_apply)})</h2>")
    parts.append(_section(top_apply, show_apply=True))

    parts.append(f"<h2>Posibles avisos falsos ({len(fakes)})</h2>")
    parts.append(_section(fakes, show_fake_reasons=True))

    if not classifications:
        parts.append("<p>No llegaron avisos nuevos hoy.</p>")

    return "\n".join(parts)


def _section(
    items: list[Classification], show_apply: bool = False, show_fake_reasons: bool = False
) -> str:
    if not items:
        return "<p><em>Nada por acá hoy.</em></p>"

    rows = []
    for c in items:
        job = c.job
        line = (
            f'<li><a href="{job.url}">{job.title}</a> — {job.company}'
            f' ({job.location})<br>'
        )
        if show_apply:
            line += f"Probabilidad de aplicar: {c.apply_probability}% — {c.apply_reasons}<br>"
        else:
            line += f"{c.relevance_reason}<br>"
        if show_fake_reasons and c.fake_reasons:
            line += f"Señales: {', '.join(c.fake_reasons)}<br>"
        line += "</li>"
        rows.append(line)
    return "<ul>\n" + "\n".join(rows) + "\n</ul>"
