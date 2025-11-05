✅ - Fix the import structure so everything is consistent. We need to run all features of this little application from one main file?
[] - Implement Semantic Weighting and Keyword extraction:
```
    prioritize salient words, use TF-IDF, RAKE, or KeyBERT:

    RAKE (Rapid Automatic Keyword Extraction):

    from rake_nltk import Rake
    r = Rake()
    r.extract_keywords_from_text("who would win in a fight, an ogre or an umber hulk")
    r.get_ranked_phrases()
    # ['fight', 'ogre', 'umber hulk']


    KeyBERT (uses BERT embeddings to find meaningful keywords):

    from keybert import KeyBERT
    kw_model = KeyBERT()
    kw_model.extract_keywords("who would win in a fight, an ogre or an umber hulk")
    # [('ogre', 0.7), ('umber hulk', 0.68), ('fight', 0.65)]
```
[] include YAML in the markdown that gets copied to metadata in the chunks to help LLM decypher tables. During table conversion to JSON, we can get the LLM doing the converting to provide the instructions for understanding the table.
[] Rate limiter!
[] Update query_must for monsters - instead of splitting the name, let's drop any text after " (" and use that for query_must.contain
[] Apache.
[] JSON return, with debug/diagnostic output as a separate property from the actual answer.
[] Update diagnostic output to include which book a chunk comes from, and the complete heading hierarchy.
[] Convert all of the print/echo calls to a logging object. Ask for a good, generic object we can use. We'll need to store log messages for debug output.
[] Add a delete collection feature to clear out old test data.
[] Add another feature to chunk metadata, "further reading" or something like that, where we can add a reference to a chunk that will be relevant even if it's not semantically similar.
[] Need to know - can I update the metadata for just one chunk? Can I retrieve just one chunk by chunk ID or similar
[] Maybe reduce the minimum number of chunks to zero instead of two. ?