# core — processing pipeline modules:
#   classify  file type/junk/binary/aux rules
#   intake    recursive archive unpacking (zip/rar/7z/tar)
#   convert   document routing through the services registry
#   ocr       vision OCR orchestration
#   markdown  Markdown builders (combined / individual / tree / stats)
#   research  optional Gemini deep-research report
#   pipeline  orchestrates: intake → convert → ocr → markdown → output
