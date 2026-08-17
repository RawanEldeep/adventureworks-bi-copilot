"""Text cleaning and tokenization shared by schema indexing and query retrieval."""

import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize

for _Resource, _Path in [
    ("stopwords", "corpora/stopwords"),
    ("wordnet", "corpora/wordnet"),
    ("averaged_perceptron_tagger", "taggers/averaged_perceptron_tagger"),
    ("punkt", "tokenizers/punkt"),
]:
    try:
        nltk.data.find(_Path)
    except LookupError:
        nltk.download(_Resource)


Stop = set(stopwords.words("english"))
Stop.discard("no")
Stop.discard("not")
Stop.discard("never")

Lemma = WordNetLemmatizer()

ReCamel = re.compile(r"([a-z0-9])([A-Z])")
ReNonAlph = re.compile(r"[^a-zA-Z0-9\s]")
ReSpace = re.compile(r"\s+")




def SplitCamelCase(Word: str) -> list[str]:
    """"SalesOrderDetail" -> ["Sales", "Order", "Detail"]; no-ops on plain lowercase words."""
    return ReCamel.sub(r"\1 \2", Word).split()


def WordNetPos(Tag):
    if Tag.startswith("J"):
        return wordnet.ADJ
    if Tag.startswith("V"):
        return wordnet.VERB
    if Tag.startswith("R"):
        return wordnet.ADV
    return wordnet.NOUN


def SafeLemmatization(W: str, PosTag: str) -> str:
    if PosTag == "NNP" or W.endswith("ss"):
        return W
    return Lemma.lemmatize(W, WordNetPos(PosTag))


def CleanText(T: str) -> str:
    T = ReCamel.sub(r"\1 \2", T)
    T = T.lower()
    T = ReNonAlph.sub("", T)
    T = ReSpace.sub(" ", T).strip()
    return T


def TextProcessing(T: str) -> list[str]:
    T = str(T)
    T = CleanText(T)
    Tokens = word_tokenize(T)

    Tokens = [
        W for W in Tokens
        if len(W) > 1 and W not in Stop and not W.isnumeric()
    ]

    #Tagged = pos_tag(Tokens)
    #return [SafeLemmatization(W, Tag) for W, Tag in Tagged]
    return Tokens

"""
if __name__ == "__main__":
    Tests = [
        "How many customers do we have?",
        "SalesOrderDetail",
        "What is the average product list price?",
        "Show me sales by territory",
    ]
    for T in Tests:
        print(f"{T!r} -> {TextProcessing(T)}")
"""

