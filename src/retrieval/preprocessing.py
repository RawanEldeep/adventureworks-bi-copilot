"""Text cleaning and tokenization shared by schema indexing and query retrieval."""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize

for _resource, _path in [
    ("stopwords", "corpora/stopwords"),
    ("wordnet", "corpora/wordnet"),
    ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger"),
    ("punkt", "tokenizers/punkt"),
]:
    try:
        nltk.data.find(_path)
    except LookupError:
        nltk.download(_resource)


Stop = set(stopwords.words("english"))
Stop.discard("no")
Stop.discard("not")
Stop.discard("never")

Lemma = WordNetLemmatizer()

Re_Camel = re.compile(r"([a-z0-9])([A-Z])")
Re_NonAlph = re.compile(r"[^a-zA-Z0-9\s]")
Re_Space = re.compile(r"\s+")




def SplitCamelCase(word: str) -> list[str]:
    """"SalesOrderDetail" -> ["Sales", "Order", "Detail"]; no-ops on plain lowercase words."""
    return Re_Camel.sub(r"\1 \2", word).split()


def WordNetPos(tag):
    if tag.startswith("J"):
        return wordnet.ADJ
    if tag.startswith("V"):
        return wordnet.VERB
    if tag.startswith("R"):
        return wordnet.ADV
    return wordnet.NOUN


def SafeLemmatization(w: str, pos_tag_: str) -> str:
    if pos_tag_ == "NNP" or w.endswith("ss"):
        return w
    return Lemma.lemmatize(w, WordNetPos(pos_tag_))


def CleanText(T: str) -> str:
    T = Re_Camel.sub(r"\1 \2", T)
    T = T.lower()
    T = Re_NonAlph.sub("", T)
    T = Re_Space.sub(" ", T).strip()
    return T


def TextProcessing(T: str) -> list[str]:
    T = str(T)
    T = CleanText(T)
    tokens = word_tokenize(T)

    tokens = [
        w for w in tokens
        if len(w) > 1 and w not in Stop and not w.isnumeric()
    ]

    tagged = pos_tag(tokens)
    return [SafeLemmatization(w, tag) for w, tag in tagged]

"""
if __name__ == "__main__":
    tests = [
        "How many customers do we have?",
        "SalesOrderDetail",
        "What is the average product list price?",
        "Show me sales by territory",
    ]
    for t in tests:
        print(f"{t!r} -> {TextProcessing(t)}")
"""

