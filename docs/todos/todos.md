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