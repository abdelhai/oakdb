import pytest
from oakdb import Oak
import random

# Setup fixtures
@pytest.fixture
def db():
    oak = Oak(":memory:")
    db = oak.Base("lembeddb")
    db.enable_vector()

    sentences = [
        "Machine learning is transforming industries across the globe.",
        "Python is a versatile programming language used in data science and web development.",
        "Natural language processing enables computers to understand human language.",
        "Artificial intelligence continues to advance rapidly in recent years.",
        "Cloud computing provides scalable and flexible infrastructure for businesses.",
        "Cybersecurity is crucial in protecting digital assets and information.",
        "Renewable energy technologies are becoming more efficient and affordable.",
        "Blockchain technology offers transparent and secure transaction methods.",
        "Data visualization helps in understanding complex information quickly.",
        "Quantum computing promises to revolutionize computational capabilities."
    ]


    for sent in sentences:
        db.add({"text": sent, "score": random.randint(20,100)})

    yield db

    # # Cleanup
    db.drop("lembeddb")


def test_simple_vsearch(db):
    assert db.vsearch("ai", filters={"score__gt": 20}, distance="L1")
    assert db.vsearch("ai", filters={"score__lt": 20}).total == 0
