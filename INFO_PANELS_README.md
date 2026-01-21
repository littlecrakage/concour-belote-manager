# Info Panels Configuration

## Overview

The info panels are now managed centrally through a JSON file (`info_panels.json`) instead of being hardcoded in the templates. This makes it much easier to maintain and update the help text for each page.

## File Location

The configuration file is located at:
```
info_panels.json
```

## Structure

Each page has its own entry in the JSON file with the following structure:

```json
{
  "page_name": {
    "title": "Panel Title",
    "description": "Main description text",
    "sections": [
      {
        "heading": "Section Title",
        "items": ["Item 1", "Item 2", "Item 3"]
      },
      {
        "heading": "Another Section",
        "content": "Paragraph text instead of items"
      }
    ]
  }
}
```

## Page Keys

The available page keys that match Flask route endpoints are:

- **index** - Home page
- **matches** - Match management page
- **admin** - Tournament administration page
- **ranking** - Ranking/standings page
- **teams** - Teams management page
- **team_detail** - Individual team details page
- **login** - Login page

## Fields Explanation

### Title
- The main heading of the info panel for this page
- Example: `"Gestion des Matchs"`

### Description
- The introductory text that appears under the title
- Should be a short explanation of what the page does

### Sections
Array of sections, each can have one of two formats:

#### Format 1: List Items
```json
{
  "heading": "Section Title",
  "items": ["Item 1", "Item 2", "Item 3"]
}
```

#### Format 2: Paragraph Content
```json
{
  "heading": "Section Title",
  "content": "This is a paragraph of text that will be displayed as-is."
}
```

## Editing the File

1. Open `info_panels.json` in your text editor
2. Find the page key you want to edit (e.g., "matches")
3. Update the title, description, or sections as needed
4. Save the file
5. Refresh your browser - changes take effect immediately (no server restart needed)

## Example Edit

To change the description on the matches page:

```json
{
  "matches": {
    "title": "Gestion des Matchs",
    "description": "YOUR NEW DESCRIPTION HERE",
    ...
  }
}
```

## Adding New Content

To add a new section to a page:

```json
{
  "matches": {
    ...
    "sections": [
      ...existing sections...,
      {
        "heading": "New Section Title",
        "items": ["New item 1", "New item 2"]
      }
    ]
  }
}
```

## Troubleshooting

### Changes not appearing
- Make sure you saved the JSON file
- Verify the JSON is valid (check for missing commas, quotes, brackets)
- Clear your browser cache or do a hard refresh (Ctrl+F5)

### JSON Validation
If you're unsure about the JSON syntax, you can:
1. Use an online JSON validator: https://jsonlint.com/
2. Use VS Code's built-in JSON validation
3. Check the Flask error logs for parsing errors

## Benefits

- **Easy to Maintain**: No need to edit HTML templates
- **Centralized**: All help text in one file
- **No Restart**: Changes reflect immediately after file save and browser refresh
- **Structured**: Clear format for adding new content
- **Translatable**: Easy to translate or create multiple language versions

## Integration

The Flask app automatically:
1. Loads the JSON file when it starts
2. Makes it available to all templates via the `info_panels` variable
3. Displays the correct panel content based on the current page (using Flask's `request.endpoint`)

The template determines which panel to show by matching the current route endpoint with the JSON keys.
