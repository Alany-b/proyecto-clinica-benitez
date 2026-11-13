"""Indexación de PDFs institucionales y búsqueda semántica en ChromaDB.

Uso dentro del contenedor:
    python -m app.rag.indexer            # reindexa (borra y recrea la colección)
    python -m app.rag.indexer --no-reset # agrega sin borrar la colección existente
"""

from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
DEFAULT_COLLECTION = "protocolos_clinica"
DEFAULT_EMBED_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

_REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RagConfig:
    """Configuración del motor RAG, sobrescribible por variables de entorno."""

    data_dir: Path
    persist_dir: Path
    collection: str = DEFAULT_COLLECTION
    embed_model: str = DEFAULT_EMBED_MODEL
    ollama_base_url: str = DEFAULT_OLLAMA_URL

    @classmethod
    def from_env(cls) -> "RagConfig":
        return cls(
            data_dir=Path(os.getenv("DATA_DIR", str(_REPO_ROOT / "data"))),
            persist_dir=Path(
                os.getenv("CHROMA_PERSIST_DIR", str(_REPO_ROOT / "vector_store"))
            ),
            collection=os.getenv("CHROMA_COLLECTION", DEFAULT_COLLECTION),
            embed_model=os.getenv("OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL),
        )


def get_embeddings(config: RagConfig | None = None) -> OllamaEmbeddings:
    """Crea el cliente de embeddings de Ollama (`nomic-embed-text`)."""
    config = config or RagConfig.from_env()
    return OllamaEmbeddings(
        model=config.embed_model,
        base_url=config.ollama_base_url,
    )


def get_vector_store(
    config: RagConfig | None = None,
    embeddings: OllamaEmbeddings | None = None,
) -> Chroma:
    """Abre (o crea) la colección persistente de Chroma."""
    config = config or RagConfig.from_env()
    config.persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=config.collection,
        embedding_function=embeddings or get_embeddings(config),
        persist_directory=str(config.persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
    )


def load_documents(data_dir: Path) -> list[Document]:
    """Carga todos los PDFs de `data_dir` (recursivo) con PyPDFLoader."""
    if not data_dir.exists():
        raise FileNotFoundError(f"No existe el directorio de datos: {data_dir}")

    pdf_paths = sorted(data_dir.rglob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No se encontraron PDFs en: {data_dir}")

    documents: list[Document] = []
    for pdf_path in pdf_paths:
        try:
            pages = PyPDFLoader(str(pdf_path)).load()
        except Exception as exc:  # pragma: no cover - depende del PDF de entrada
            raise RuntimeError(f"No se pudo leer {pdf_path.name}: {exc}") from exc

        for page in pages:
            page_number = page.metadata.get("page")
            page.metadata["archivo"] = pdf_path.name
            page.metadata["documento"] = pdf_path.stem
            page.metadata["pagina"] = (
                int(page_number) + 1 if isinstance(page_number, int) else None
            )
            if not page.page_content.strip():
                logger.warning(
                    "Página sin texto extraíble: %s (pág. %s)",
                    pdf_path.name,
                    page.metadata["pagina"],
                )
        documents.extend(pages)
        logger.info("Cargado %s (%d páginas)", pdf_path.name, len(pages))

    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    """Divide el texto en fragmentos de 1000 caracteres con 200 de solapamiento."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = index
    return chunks


def index_pdfs(
    reset: bool = True,
    config: RagConfig | None = None,
) -> dict[str, Any]:
    """Indexa los PDFs en Chroma y devuelve estadísticas del proceso."""
    config = config or RagConfig.from_env()
    documents = load_documents(config.data_dir)
    chunks = split_documents(documents)

    logger.info(
        "Indexando %d fragmentos en la colección '%s' (%s)",
        len(chunks),
        config.collection,
        config.persist_dir,
    )
    store = get_vector_store(config)
    if reset:
        logger.info("Reset solicitado: se elimina la colección existente.")
        store.reset_collection()

    ids = store.add_documents(chunks)
    stats = {
        "archivos": len({doc.metadata["archivo"] for doc in documents}),
        "paginas": len(documents),
        "fragmentos": len(chunks),
        "ids_indexados": len(ids),
        "coleccion": config.collection,
        "persistencia": str(config.persist_dir),
        "modelo_embeddings": config.embed_model,
        "ollama_url": config.ollama_base_url,
    }
    logger.info("Indexación completa: %s", stats)
    return stats


def search_protocols(
    query: str,
    k: int = 4,
    config: RagConfig | None = None,
) -> list[Document]:
    """Búsqueda por similitud en la colección institucional."""
    if not query or not query.strip():
        raise ValueError("La consulta no puede estar vacía.")
    store = get_vector_store(config)
    return store.similarity_search(query, k=k)


def search_protocols_with_score(
    query: str,
    k: int = 4,
    config: RagConfig | None = None,
) -> list[tuple[Document, float]]:
    """Búsqueda por similitud devolviendo también la distancia (menor = mejor)."""
    if not query or not query.strip():
        raise ValueError("La consulta no puede estar vacía.")
    store = get_vector_store(config)
    return store.similarity_search_with_score(query, k=k)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Indexa los PDFs de Clínica Benitez en ChromaDB.",
    )
    parser.add_argument(
        "--no-reset",
        dest="reset",
        action="store_false",
        help="Agrega documentos sin borrar la colección existente.",
    )
    parser.set_defaults(reset=True)
    return parser


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = _build_parser().parse_args()
    stats = index_pdfs(reset=args.reset)
    print("\nIndexación finalizada:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
