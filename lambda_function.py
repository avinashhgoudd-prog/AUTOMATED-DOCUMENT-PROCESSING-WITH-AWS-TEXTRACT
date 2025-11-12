import json
import boto3
import logging
from botocore.exceptions import BotoCoreError, ClientError
from parser import (
    extract_text,
    map_word_id,
    extract_table_info,
    get_key_map,
    get_value_map,
    get_kv_map,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    try:
        textract = boto3.client("textract")
    except (BotoCoreError, ClientError) as e:
        logger.error("Could not initialize Textract client: %s", str(e))
        return {"statusCode": 500, "body": "Textract client error."}

    try:
        # Defensive extraction of S3 info
        file_obj = event.get("Records", [{}])[0]
        bucketname = file_obj.get("s3", {}).get("bucket", {}).get("name")
        filename = file_obj.get("s3", {}).get("object", {}).get("key")
        if not bucketname or not filename:
            raise ValueError("Missing bucket or key in event.")

        logger.info(f"Bucket: {bucketname} ::: Key: {filename}")

        try:
            response = textract.analyze_document(
                Document={
                    "S3Object": {
                        "Bucket": bucketname,
                        "Name": filename,
                    }
                },
                FeatureTypes=["FORMS", "TABLES"],
            )
        except (BotoCoreError, ClientError) as tex_err:
            logger.error("Textract API Error: %s", tex_err)
            return {"statusCode": 502, "body": f"Textract error: {str(tex_err)}"}

        logger.debug("Textract response: %s", json.dumps(response, default=str))

        # Safe parsing
        raw_text = extract_text(response, extract_by="LINE")
        word_map = map_word_id(response)
        table = extract_table_info(response, word_map)
        key_map = get_key_map(response, word_map)
        value_map = get_value_map(response, word_map)
        final_map = get_kv_map(key_map, value_map)

        logger.info("Table extraction: %s", json.dumps(table, default=str))
        logger.info("Final key-value map: %s", json.dumps(final_map, default=str))
        logger.info("Raw text: %s", raw_text)

        # Return some result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "table": table,
                "keyValueMap": final_map,
                "text": raw_text,
                "message": "Document processed successfully."
            }),
        }

    except Exception as ex:
        logger.error("Unhandled error: %s", str(ex))
        return {"statusCode": 500, "body": "Unhandled exception: " + str(ex)}
