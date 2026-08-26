# Notion Training Progress

Browser-only progress tracking widget for the Mindly CRM Training Hub.

Progress is stored in each visitor's browser using `localStorage`. No user account or backend is required.

## Embed modes

- Lesson: `?type=lesson&id=NOTION_LESSON_PAGE_ID`
- Section: `?type=section&id=NOTION_SECTION_PAGE_ID`
- Overall: `?type=overall`

Optional: add `&compact=1` for a smaller card.

## Important

The public page must be served from a stable origin. Clearing site data, using another browser/device, or private browsing will not carry progress across.