import hashlib
import re

from app.domain.models import AcceptanceCriterion, BacklogData, Epic, Feature, UserStory

_AC_SPLIT_PATTERNS = [
    r"^\s*[✓✔☑√]\s+",
    r"^\s*[-–—•·]\s+",
    r"^\s*\d+[.)]\s+",
    r"^\s*\*\s+",
    r"^\s*>\s+",
]

_AC_NOISE_PREFIX = re.compile(r"^[\s✓✔☑√\-–—•·\*>\d.)\u2022\u2023\u25E6\u2043\u2219]+")


def _generate_id(prefix: str, text: str, index: int) -> str:
    hash_input = f"{prefix}:{text}:{index}"
    return f"{prefix}_{hashlib.md5(hash_input.encode()).hexdigest()[:8]}"


def parse_acceptance_criteria(raw: str | list | None, story_id: str) -> list[AcceptanceCriterion]:
    if not raw:
        return []
    if isinstance(raw, list):
        raw_items = [str(item).strip() for item in raw if item and str(item).strip()]
    else:
        raw_items = _split_ac_text(str(raw))

    criteria = []
    for idx, item in enumerate(raw_items):
        original = item
        cleaned = _clean_criterion_text(item)
        if not cleaned:
            continue
        criteria.append(
            AcceptanceCriterion(
                id=_generate_id(f"{story_id}_ac", cleaned, idx),
                text=cleaned,
                original_text=original,
            )
        )
    return criteria


def _split_ac_text(text: str) -> list[str]:
    lines = text.splitlines()
    has_bullets = any(
        re.match(pat, line)
        for line in lines
        for pat in _AC_SPLIT_PATTERNS
        if line.strip()
    )

    if has_bullets:
        items: list[str] = []
        current = ""
        for line in lines:
            is_bullet = any(re.match(pat, line) for pat in _AC_SPLIT_PATTERNS)
            if is_bullet:
                if current.strip():
                    items.append(current.strip())
                current = line
            elif line.strip():
                current += " " + line.strip()
        if current.strip():
            items.append(current.strip())
        return items
    return [line.strip() for line in lines if line.strip()]


def _clean_criterion_text(text: str) -> str:
    cleaned = _AC_NOISE_PREFIX.sub("", text).strip()
    cleaned = cleaned.rstrip(".")
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned


def _get(obj: dict, *keys, default="") -> str:
    for key in keys:
        val = obj.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def _get_id(obj: dict, prefix: str, fallback_text: str, index: int) -> str:
    for key in ("id", "Id", "ID", "_id", "storyId", "featureId", "epicId"):
        val = obj.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return _generate_id(prefix, fallback_text, index)


def normalize_backlog(raw_response: dict | list) -> BacklogData:
    if isinstance(raw_response, dict):
        for wrapper in ("data", "result", "payload", "response", "backlog"):
            if wrapper in raw_response and isinstance(raw_response[wrapper], (dict, list)):
                raw_response = raw_response[wrapper]
                break

    if isinstance(raw_response, dict):
        raw_epics = raw_response["epics"] if "epics" in raw_response else [raw_response]
    elif isinstance(raw_response, list):
        raw_epics = raw_response
    else:
        raw_epics = []

    epics = [_parse_epic(raw_epic, idx) for idx, raw_epic in enumerate(raw_epics)]
    backlog = BacklogData(epics=epics)
    backlog.compute_totals()
    return backlog


def _parse_epic(raw: dict, idx: int) -> Epic:
    title = _get(raw, "title", "name", "epicTitle", "epic", "Epic", default=f"Epic {idx + 1}")
    epic_id = _get_id(raw, "epic", title, idx)
    description = _get(raw, "description", "desc", "summary")
    raw_features = raw.get("features") or raw.get("Features") or raw.get("feature_list") or []
    features = [_parse_feature(f, epic_id, fidx) for fidx, f in enumerate(raw_features)]
    return Epic(id=epic_id, title=title, description=description, features=features)


def _parse_feature(raw: dict, epic_id: str, idx: int) -> Feature:
    title = _get(raw, "title", "name", "featureTitle", "feature", "Feature", default=f"Feature {idx + 1}")
    feature_id = _get_id(raw, f"{epic_id}_feat", title, idx)
    description = _get(raw, "description", "desc", "summary")
    raw_stories = (
        raw.get("user_stories")
        or raw.get("userStories")
        or raw.get("stories")
        or raw.get("UserStories")
        or []
    )
    stories = [_parse_story(s, feature_id, sidx) for sidx, s in enumerate(raw_stories)]
    return Feature(id=feature_id, title=title, description=description, user_stories=stories)


def _parse_story(raw: dict, feature_id: str, idx: int) -> UserStory:
    title = _get(
        raw,
        "title",
        "name",
        "storyTitle",
        "story",
        "UserStory",
        "user_story",
        "summary",
        default=f"User Story {idx + 1}",
    )
    story_id = _get_id(raw, f"{feature_id}_story", title, idx)
    description = _get(raw, "description", "desc", "body", "content", "as_a")
    raw_ac = (
        raw.get("acceptance_criteria")
        or raw.get("acceptanceCriteria")
        or raw.get("AcceptanceCriteria")
        or raw.get("criteria")
        or raw.get("ac")
        or raw.get("AC")
        or None
    )
    criteria = parse_acceptance_criteria(raw_ac, story_id)
    return UserStory(id=story_id, title=title, description=description, acceptance_criteria=criteria)
