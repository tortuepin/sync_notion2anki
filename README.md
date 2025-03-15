# sync_notion2anki

## Description

Notionのデータベースの内容をもとにAnkiにnoteを追加するスクリプト

## Installation

```shell
pipx install .
``` 

## Configuration

### Set the Notion API token as an environment variable:

```shell
export NOTION_TOKEN=<your_notion_token>
```

### Create a `mappings.json` file with your Notion database and Anki deck mappings. See "Configuration" section below.

Create a `mappings.json` file in the same directory as the script. Example:

```json
{
  "mappings": [
    {
      "deck": "Your Deck Name",
      "model": "Basic",
      "notion_database_id": "your-notion-database-id",
      "notion_properties": {
        "Front": "Notion Property Front",
        "Back": "Notion Property Back"
      },
      "fields": {
        "Front": "Front",
        "Back": "Back"
      }
    },
    {
       "deck": "Your Deck Name2",
       ...
    }
  ]
}
```

- deck: Anki deck name.
- model: Anki note model name.
- notion_database_id: Notion database ID.
- notion_properties: Mapping of Anki fields to Notion properties.
- fields: Anki fields.

## Usage

``` shell
sync_notion2anki path/to/mappings.json
```
