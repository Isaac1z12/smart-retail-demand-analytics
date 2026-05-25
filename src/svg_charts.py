from xml.sax.saxutils import escape


PALETTE = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]


def _nice_bounds(values):
    clean = [float(value) for value in values if value is not None]
    if not clean:
        return 0.0, 1.0
    lower = min(clean)
    upper = max(clean)
    if lower == upper:
        return lower - 1.0, upper + 1.0
    padding = (upper - lower) * 0.08
    return lower - padding, upper + padding


def _scale(value, src_min, src_max, dst_min, dst_max):
    if src_max == src_min:
        return (dst_min + dst_max) / 2.0
    return dst_min + (value - src_min) * (dst_max - dst_min) / (src_max - src_min)


def _svg_header(width, height):
    return [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(
            width, height, width, height
        ),
        "<style>",
        "text { font-family: Arial, sans-serif; fill: #111827; }",
        ".axis { stroke: #374151; stroke-width: 1; }",
        ".grid { stroke: #e5e7eb; stroke-width: 1; }",
        ".label { font-size: 12px; fill: #4b5563; }",
        ".title { font-size: 20px; font-weight: 700; }",
        ".legend { font-size: 12px; fill: #374151; }",
        "</style>",
    ]


def write_line_chart(path, title, x_labels, series, y_label="Value", width=960, height=520):
    margin_left = 74
    margin_right = 30
    margin_top = 70
    margin_bottom = 84
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    all_values = []
    for item in series:
        all_values.extend(item["values"])
    y_min, y_max = _nice_bounds(all_values)
    lines = _svg_header(width, height)
    lines.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    lines.append('<text class="title" x="{}" y="34">{}</text>'.format(margin_left, escape(title)))
    lines.append('<text class="label" x="{}" y="54">{}</text>'.format(margin_left, escape(y_label)))

    for step in range(5):
        y = margin_top + plot_height * step / 4.0
        value = y_max - (y_max - y_min) * step / 4.0
        lines.append('<line class="grid" x1="{}" y1="{:.2f}" x2="{}" y2="{:.2f}"/>'.format(margin_left, y, width - margin_right, y))
        lines.append('<text class="label" x="{}" y="{:.2f}" text-anchor="end">{:.1f}</text>'.format(margin_left - 10, y + 4, value))

    lines.append('<line class="axis" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(margin_left, margin_top + plot_height, width - margin_right, margin_top + plot_height))
    lines.append('<line class="axis" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(margin_left, margin_top, margin_left, margin_top + plot_height))

    point_count = max(1, len(x_labels) - 1)
    for index, label in enumerate(x_labels):
        if index % max(1, len(x_labels) // 8) == 0 or index == len(x_labels) - 1:
            x = margin_left + plot_width * index / point_count
            lines.append('<text class="label" x="{:.2f}" y="{}" text-anchor="middle">{}</text>'.format(x, height - 42, escape(str(label))))

    for series_index, item in enumerate(series):
        color = item.get("color", PALETTE[series_index % len(PALETTE)])
        points = []
        for index, value in enumerate(item["values"]):
            x = margin_left + plot_width * index / point_count
            y = _scale(float(value), y_min, y_max, margin_top + plot_height, margin_top)
            points.append("{:.2f},{:.2f}".format(x, y))
        lines.append('<polyline fill="none" stroke="{}" stroke-width="2.5" points="{}"/>'.format(color, " ".join(points)))
        legend_x = margin_left + series_index * 150
        lines.append('<rect x="{}" y="{}" width="12" height="12" fill="{}"/>'.format(legend_x, height - 24, color))
        lines.append('<text class="legend" x="{}" y="{}">{}</text>'.format(legend_x + 18, height - 14, escape(item["name"])))

    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_bar_chart(path, title, labels, values, y_label="Value", width=960, height=520):
    margin_left = 84
    margin_right = 36
    margin_top = 70
    margin_bottom = 118
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    y_min = 0.0
    y_max = max(values) * 1.12 if values else 1.0
    lines = _svg_header(width, height)
    lines.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    lines.append('<text class="title" x="{}" y="34">{}</text>'.format(margin_left, escape(title)))
    lines.append('<text class="label" x="{}" y="54">{}</text>'.format(margin_left, escape(y_label)))

    for step in range(5):
        y = margin_top + plot_height * step / 4.0
        value = y_max - (y_max - y_min) * step / 4.0
        lines.append('<line class="grid" x1="{}" y1="{:.2f}" x2="{}" y2="{:.2f}"/>'.format(margin_left, y, width - margin_right, y))
        lines.append('<text class="label" x="{}" y="{:.2f}" text-anchor="end">{:.1f}</text>'.format(margin_left - 10, y + 4, value))

    bar_gap = 14
    count = max(1, len(values))
    bar_width = max(18, (plot_width - bar_gap * (count - 1)) / count)
    for index, value in enumerate(values):
        x = margin_left + index * (bar_width + bar_gap)
        y = _scale(value, y_min, y_max, margin_top + plot_height, margin_top)
        bar_height = margin_top + plot_height - y
        color = PALETTE[index % len(PALETTE)]
        lines.append('<rect x="{:.2f}" y="{:.2f}" width="{:.2f}" height="{:.2f}" fill="{}" rx="3"/>'.format(x, y, bar_width, bar_height, color))
        label = labels[index]
        lines.append(
            '<text class="label" x="{:.2f}" y="{}" text-anchor="end" transform="rotate(-35 {:.2f} {})">{}</text>'.format(
                x + bar_width / 2.0,
                height - 46,
                x + bar_width / 2.0,
                height - 46,
                escape(str(label)),
            )
        )
    lines.append('<line class="axis" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(margin_left, margin_top + plot_height, width - margin_right, margin_top + plot_height))
    lines.append('<line class="axis" x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(margin_left, margin_top, margin_left, margin_top + plot_height))
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")

