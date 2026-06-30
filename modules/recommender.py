"""관심사 기반 추천 엔진 (FR-10)"""


def reorder_summaries(
    summaries: dict[str, dict],
    interest_scores: dict[str, int],
) -> dict[str, dict]:
    """관심도 점수 높은 테마가 앞에 오도록 summaries 재정렬."""
    def score(item):
        return interest_scores.get(item[0], 0)

    return dict(sorted(summaries.items(), key=score, reverse=True))


def get_top_articles(
    summaries: dict[str, dict],
    interest_scores: dict[str, int],
    top_n: int = 3,
) -> list[dict]:
    """
    관심도 높은 테마의 기사를 최대 top_n개 추천.
    클릭 데이터가 없으면 빈 리스트.
    """
    if not interest_scores:
        return []

    # 점수 높은 테마 순으로 기사 수집
    sorted_themes = sorted(interest_scores.items(), key=lambda x: x[1], reverse=True)
    recommendations = []

    for theme_id, score in sorted_themes:
        if theme_id not in summaries:
            continue
        articles = summaries[theme_id].get("articles", [])
        theme_name = summaries[theme_id].get("theme_name", theme_id)
        for article in articles[:2]:
            recommendations.append({
                **article,
                "theme_id":        theme_id,
                "recommend_reason": theme_name,
                "interest_score": score,
            })
        if len(recommendations) >= top_n:
            break

    return recommendations[:top_n]
