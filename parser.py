import uuid
import logging

logger = logging.getLogger()

def extract_text(response, extract_by="WORD"):
    line_text = []
    try:
        for block in response.get("Blocks", []):
            if block.get("BlockType") == extract_by and block.get("Text"):
                line_text.append(block["Text"])
    except Exception as e:
        logger.error("Error in extract_text: %s", str(e))
    return line_text

def map_word_id(response):
    word_map = {}
    try:
        for block in response.get("Blocks", []):
            if block.get("BlockType") == "WORD" and block.get("Id"):
                word_map[block["Id"]] = block.get("Text", "")
            elif block.get("BlockType") == "SELECTION_ELEMENT" and block.get("Id"):
                word_map[block["Id"]] = block.get("SelectionStatus", "")
    except Exception as e:
        logger.error("Error in map_word_id: %s", str(e))
    return word_map

def extract_table_info(response, word_map):
    tables = {}
    try:
        temp_table = []
        current_table_key = None
        current_row_index = 1
        row = []
        for block in response.get("Blocks", []):
            if block.get("BlockType") == "TABLE":
                current_table_key = f"table_{uuid.uuid4().hex}"
                tables[current_table_key] = []
                temp_table = tables[current_table_key]
                current_row_index = 1
            elif block.get("BlockType") == "CELL" and current_table_key:
                row_index = block.get("RowIndex", 1)
                if row_index != current_row_index:
                    if row:
                        temp_table.append(row)
                    row = []
                    current_row_index = row_index
                cell_text = ""
                for relation in block.get("Relationships", []):
                    if relation.get("Type") == "CHILD":
                        cell_text = " ".join([word_map.get(i, "") for i in relation.get("Ids", [])])
                row.append(cell_text if cell_text else " ")
        if row and temp_table is not None:
            temp_table.append(row)
    except Exception as e:
        logger.error("Error in extract_table_info: %s", str(e))
    return tables

def get_key_map(response, word_map):
    key_map = {}
    try:
        for block in response.get("Blocks", []):
            if block.get("BlockType") == "KEY_VALUE_SET" and "KEY" in block.get("EntityTypes", []):
                value_id = []
                key_str = None
                for relation in block.get("Relationships", []):
                    if relation.get("Type") == "VALUE":
                        value_id = relation.get("Ids", [])
                    elif relation.get("Type") == "CHILD":
                        key_str = " ".join([word_map.get(i, "") for i in relation.get("Ids", [])])
                if key_str:
                    key_map[key_str] = value_id
    except Exception as e:
        logger.error("Error in get_key_map: %s", str(e))
    return key_map

def get_value_map(response, word_map):
    value_map = {}
    try:
        for block in response.get("Blocks", []):
            if block.get("BlockType") == "KEY_VALUE_SET" and "VALUE" in block.get("EntityTypes", []):
                found = False
                for relation in block.get("Relationships", []):
                    if relation.get("Type") == "CHILD":
                        v = " ".join([word_map.get(i, "") for i in relation.get("Ids", [])])
                        value_map[block["Id"]] = v
                        found = True
                if not found and block.get("Id"):
                    value_map[block["Id"]] = "VALUE_NOT_FOUND"
    except Exception as e:
        logger.error("Error in get_value_map: %s", str(e))
    return value_map

def get_kv_map(key_map, value_map):
    final_map = {}
    try:
        for key, value_ids in key_map.items():
            final_map[key] = " ".join([value_map.get(k, "") for k in value_ids])
    except Exception as e:
        logger.error("Error in get_kv_map: %s", str(e))
    return final_map
