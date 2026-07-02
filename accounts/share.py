def build_share_message(visited_count, total=92, ground_name=None):
    pct = round(visited_count / total * 100) if total else 0
    if ground_name:
        return f"⚽ Just ticked off {ground_name}! Now at {visited_count}/{total} grounds ({pct}%) on The 92 👉"
    if visited_count <= 0:
        return "⚽ Starting my journey around all 92 football grounds in England — follow along on The 92 👉"
    if visited_count >= total:
        return f"🏆 Done! I've visited all {total} grounds in England on The 92 👉"
    return f"⚽ {visited_count}/{total} grounds visited ({pct}%) on my journey around English football. Check out my collection on The 92 👉"
