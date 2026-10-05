# Provenance contract

Every important artifact identifies where it came from.

Source file minimum fields: file_id, original_filename, file_type, size_bytes, sha256, source_origin, received_date, authority_role, classification, parser, parser_version, ingestion_status.

Normalized entities carry stable IDs and, where available: source_document_id, source_page, source_table, source_record, source_file_id, extraction_method, verification_status.

Results record normalized model ID/hash, analysis run ID, solver/version, configuration, unit system, case/combination, source lineage and timestamp.

Quantitative report statements trace to a governed result/check ID and ultimately to model/run/source evidence.
