#!/usr/bin/env python3

import requests
import json
import os
from notion_client import Client
import sys
import logging
from typing import Dict, List, Optional, Any, Union, TypedDict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

ANKI_CONNECT_URL: str = "http://127.0.0.1:8765"
NOTION_TOKEN: Optional[str] = os.environ.get("NOTION_TOKEN")

if not NOTION_TOKEN:
    logger.error("NOTION_TOKEN environment variable is not set.")
    sys.exit(1)

ANKI_ERROR_MESSAGE_MAP: Dict[str, str] = {
    "DUPLICATE_NOTE_ERROR": "cannot create note because it is a duplicate",
}

class AnkiConnectResult(TypedDict):
    result: Optional[Union[Dict[str, Any], str]]
    error: Optional[str]

def anki_connect_request(action: str, **params: Any) -> AnkiConnectResult:
    payload: Dict[str, Any] = {"action": action, "version": 6, "params": params}
    try:
        logger.debug(f"AnkiConnect request: {action}, params: {params}")
        response: requests.Response = requests.post(ANKI_CONNECT_URL, data=json.dumps(payload))
        response.raise_for_status()
        result: Dict[str, Any] = response.json()
        return AnkiConnectResult(result=result.get("result"), error=result.get("error"))
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to AnkiConnect: {e}")
        return AnkiConnectResult(result=None, error=str(e))

def load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filename}")
        return None

def add_note_to_anki(deck: str, model: str, fields: Dict[str, str], tags: Optional[List[str]] = None) -> Optional[Union[Dict[str, Any], str]]:
    if tags is None:
        tags = []
    params: Dict[str, Any] = {
        "note": {
            "deckName": deck,
            "modelName": model,
            "fields": fields,
            "tags": tags,
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck",
                "checkChildren": True
            }
        }
    }
    result: AnkiConnectResult = anki_connect_request("addNote", **params)
    if result["error"]:
        if ANKI_ERROR_MESSAGE_MAP["DUPLICATE_NOTE_ERROR"] in result["error"]:
            logger.debug(f"Note already exists in deck: {deck}")
            return "duplicate"
        else:
            logger.error(f"Failed to add note: {result['error']}")
            return None
    else:
        return result["result"]

def extract_field_value(notion_property: Dict[str, Any]) -> Optional[str]:
    if notion_property["type"] == "rich_text":
        if len(notion_property.get("rich_text", [])) > 0:
            return notion_property["rich_text"][0]["plain_text"]
    elif notion_property["type"] == "title":
        if len(notion_property.get("title", [])) > 0:
            return notion_property["title"][0]["plain_text"]
    elif notion_property["type"] == "unique_id":
        return str(notion_property["unique_id"]["number"])
    return None

def process_notion_data(mappings_file: str) -> None:
    notion: Client = Client(auth=NOTION_TOKEN)
    mappings: Optional[List[Dict[str, Any]]] = load_json_file(mappings_file)["mappings"]
    duplicate_count: int = 0
    deck_summary: Dict[str, Dict[str, int]] = {}  # Deck summary: counts for added and duplicate notes

    if mappings:
        for mapping in mappings:
            database_id = mapping["notion_database_id"]
            try:
                response: Dict[str, Any] = notion.databases.query(database_id=database_id)
                notion_data: List[Dict[str, Any]] = response["results"]
                logger.info(f"Notion data fetched successfully. {len(notion_data)} items found from database: {database_id}")
                logger.debug(f"Notion data: {json.dumps(notion_data, indent=2, ensure_ascii=False)}")
            except Exception as e:
                logger.error(f"Notion API error for database {database_id}: {e}")
                continue

            for item in notion_data:
                properties: Dict[str, Any] = item.get("properties", {})
                logger.debug(f"Notion item properties: {properties}")
                deck: str = mapping["deck"]  # Deck name
                anki_fields: Dict[str, str] = {}
                notion_properties_map: Dict[str, str] = mapping["notion_properties"]
                valid_item: bool = True

                for anki_field_key, notion_property_name in notion_properties_map.items():
                    notion_property: Dict[str, Any] = properties.get(notion_property_name)
                    if not notion_property:
                        logger.warning(f"Item skipped due to missing property: {notion_property_name}")
                        valid_item = False
                        break

                    value: Optional[str] = extract_field_value(notion_property)
                    if value is not None:
                        anki_fields[mapping["fields"][anki_field_key]] = value
                    else:
                        valid_item = False
                        logger.warning(f"Item skipped due to invalid property type or empty value for {notion_property_name}")
                        break

                if valid_item:
                    tags: List[str] = []
                    if "tag" in mapping["fields"]:
                        tags = properties.get(notion_properties_map.get("tag"), {}).get("multi_select", [])
                        tags = [tag.get("name") for tag in tags]

                    logger.debug(f"Adding note to Anki: deck={deck}, model={mapping['model']}, fields={anki_fields}, tags={tags}")
                    result: Optional[Union[Dict[str, Any], str]] = add_note_to_anki(deck, mapping["model"], anki_fields, tags)
                    if result == "duplicate":
                        duplicate_count += 1
                        if deck not in deck_summary:
                            deck_summary[deck] = {"Added": 0, "Duplicates": 0}
                        deck_summary[deck]["Duplicates"] += 1
                    elif result:
                        logger.debug("Note added successfully.")
                        if deck not in deck_summary:
                            deck_summary[deck] = {"Added": 0, "Duplicates": 0}
                        deck_summary[deck]["Added"] += 1
                    else:
                        logger.error("Failed to add note.")

    # Display summary: added and duplicate notes per deck
    if deck_summary:
        logger.info("Summary:")
        for deck, counts in deck_summary.items():
            logger.info(f"  Deck: {deck}, Added: {counts['Added']}, Duplicates: {counts['Duplicates']}")
    logger.info(f"Total items added: {len(notion_data) - duplicate_count}")
    logger.info(f"Total duplicates: {duplicate_count}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python sync_notion2anki.py <mappings_file_path>")
        sys.exit(1)

    mappings_file_path = sys.argv[1]
    process_notion_data(mappings_file_path)

if __name__ == "__main__":
    main()