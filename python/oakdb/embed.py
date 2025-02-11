from llama_cpp import Llama


class MXBAILargeEmbeddings:
    """same api as langchain embs providers"""

    def __init__(self):
        # TODO: disable network calls after download
        self.llm = Llama.from_pretrained(
            repo_id="mixedbread-ai/mxbai-embed-large-v1",
            filename="gguf/mxbai-embed-large-v1-f16.gguf",
            embedding=True,
            verbose=False,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed search docs.

        Args:
        texts: List of text to embed.

        Returns:
        List of embeddings.
        """
        assert isinstance(texts, list), "Provide a list of texts (strings)"
        fembs = []
        for text in texts:
            remb = self.llm.embed(text)
            fembs.append(remb)
        return fembs

    def embed_query(self, text: str) -> list[float]:
        """Embed query text.

        Args:
            text: Text to embed.

        Returns:
            Embedding.
        """
        assert isinstance(text, str), "Provide a string"
        remb = self.llm.embed(text)
        return remb  # pyright: ignore


# default
embedder = MXBAILargeEmbeddings()
