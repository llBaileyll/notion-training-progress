import json
import os
import pathlib
import urllib.request
import urllib.error

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
NOTION_VERSION = "2026-03-11"
SECTIONS_DATA_SOURCE = "ac782006-f632-48fa-a034-699df316fec2"
LESSONS_DATA_SOURCE = "bbb7beff-a492-4981-ae2f-8fce6dd770df"
WIDGET_BASE = "https://llbaileyll.github.io/notion-training-progress/"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.notion.com{path}", data=data, headers=HEADERS, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(f"Notion API {e.code} for {path}: {detail}") from e


def query_data_source(data_source_id):
    results = []
    cursor = None
    while True:
        body = {"page_size": 100, "result_type": "page"}
        if cursor:
            body["start_cursor"] = cursor
        response = request("POST", f"/v1/data_sources/{data_source_id}/query", body)
        results.extend(response.get("results", []))
        if not response.get("has_more"):
            return results
        cursor = response.get("next_cursor")


def plain_text(prop):
    if not prop:
        return ""
    values = prop.get("title") or prop.get("rich_text") or []
    return "".join(item.get("plain_text", "") for item in values).strip()


def number_value(prop, default=999999):
    value = (prop or {}).get("number")
    return default if value is None else value


def relation_ids(prop):
    return [item["id"].replace("-", "") for item in (prop or {}).get("relation", []) if item.get("id")]


def list_blocks(block_id):
    results = []
    cursor = None
    while True:
        suffix = "?page_size=100"
        if cursor:
            suffix += f"&start_cursor={cursor}"
        response = request("GET", f"/v1/blocks/{block_id}/children{suffix}")
        results.extend(response.get("results", []))
        if not response.get("has_more"):
            return results
        cursor = response.get("next_cursor")


def ensure_widget(page_id, widget_url):
    blocks = list_blocks(page_id)
    for block in blocks:
        if block.get("type") == "embed":
            url = (block.get("embed") or {}).get("url", "")
            if "llbaileyll.github.io/notion-training-progress" in url:
                return False
    request(
        "PATCH",
        f"/v1/blocks/{page_id}/children",
        {
            "position": {"type": "end"},
            "children": [{"object": "block", "type": "embed", "embed": {"url": widget_url}}],
        },
    )
    return True


def main():
    section_pages = query_data_source(SECTIONS_DATA_SOURCE)
    lesson_pages = query_data_source(LESSONS_DATA_SOURCE)

    section_rows = []
    for page in section_pages:
        props = page.get("properties", {})
        section_rows.append({
            "id": page["id"].replace("-", ""),
            "page_id": page["id"],
            "name": plain_text(props.get("Section")) or "Untitled Section",
            "order": number_value(props.get("Order")),
            "lessons": [],
        })
    section_rows.sort(key=lambda x: (x["order"], x["name"].lower()))
    sections_by_id = {row["id"]: row for row in section_rows}

    lesson_names = {}
    lesson_rows = []
    for page in lesson_pages:
        props = page.get("properties", {})
        lesson_id = page["id"].replace("-", "")
        lesson_name = plain_text(props.get("Lesson")) or "Untitled Lesson"
        section_ids = relation_ids(props.get("Section"))
        lesson_rows.append({
            "id": lesson_id,
            "page_id": page["id"],
            "name": lesson_name,
            "order": number_value(props.get("Order")),
            "section_ids": section_ids,
        })
        lesson_names[lesson_id] = lesson_name

    lesson_rows.sort(key=lambda x: (x["order"], x["name"].lower()))
    for lesson in lesson_rows:
        for section_id in lesson["section_ids"]:
            if section_id in sections_by_id:
                sections_by_id[section_id]["lessons"].append(lesson["id"])

    added = 0
    for lesson in lesson_rows:
        url = f"{WIDGET_BASE}?type=lesson&id={lesson['id']}"
        if ensure_widget(lesson["page_id"], url):
            print(f"Added completion widget to lesson: {lesson['name']}")
            added += 1

    for section in section_rows:
        url = f"{WIDGET_BASE}?type=section&id={section['id']}"
        if ensure_widget(section["page_id"], url):
            print(f"Added progress widget to section: {section['name']}")
            added += 1

    config = {
        "sections": {
            row["id"]: {"name": row["name"], "lessons": row["lessons"]}
            for row in section_rows
        },
        "lessonNames": lesson_names,
    }
    output = "window.TRAINING_CONFIG = " + json.dumps(config, indent=2, ensure_ascii=False) + ";\n"
    path = pathlib.Path("progress-config.js")
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old != output:
        path.write_text(output, encoding="utf-8")
        print(f"Updated progress-config.js: {len(lesson_rows)} lessons across {len(section_rows)} sections")
    else:
        print(f"Config already current: {len(lesson_rows)} lessons across {len(section_rows)} sections")
    print(f"Notion widgets added this run: {added}")


if __name__ == "__main__":
    main()
