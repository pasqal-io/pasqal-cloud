def format_duration(seconds: float) -> str:
    """Format a duration in seconds under a minute, then down to the minute, or
    the hour once it spans days: "30 s", "2 h 5 min", "1 day 2 h"."""
    if seconds < 60:
        return f"{int(seconds)} s"

    minutes = int(seconds // 60)
    days, minutes = divmod(minutes, 24 * 60)
    hours, minutes = divmod(minutes, 60)

    parts = []
    if days:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours:
        parts.append(f"{hours} h")
    if minutes and not days:
        parts.append(f"{minutes} min")

    return " ".join(parts)
