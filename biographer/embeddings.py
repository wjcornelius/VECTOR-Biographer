# Vector Embedding Layer for Cognitive Substrate
"""
Provides semantic search capabilities using local embeddings and ChromaDB.
Enables querying memories by meaning rather than keywords.
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import json

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np

# Paths
SOUL_DIR = Path(__file__).parent.parent
VECTOR_DB_PATH = SOUL_DIR / "vector_db"
SQLITE_DB_PATH = SOUL_DIR / "bill_knowledge_base.db"

# Tables to embed (all 27+ cognitive architecture tables)
EMBEDDABLE_TABLES = [
    # Original core tables
    'self_knowledge',
    'life_events',
    'stories',
    'relationships',
    # Cognitive architecture tables
    'decisions',
    'mistakes',
    'reasoning_patterns',
    'value_hierarchies',
    'cognitive_biases',
    'contradictions',
    'meaning_structures',
    'mortality_awareness',
    'body_knowledge',
    # Emotional landscape
    'fears',
    'joys',
    'sorrows',
    'loves',
    'longings',
    # Growth & wounds
    'wounds',
    'healings',
    'losses',
    'growth',
    # Character
    'strengths',
    'vulnerabilities',
    'regrets',
    'wisdom',
    'questions',
]

# Text fields to combine for each table (fallback to common patterns)
TABLE_TEXT_FIELDS = {
    # Original core tables
    'self_knowledge': ['aspect', 'description', 'examples'],
    'life_events': ['event_description', 'emotional_impact', 'lessons_learned'],
    'stories': ['title', 'narrative', 'emotional_core', 'meaning'],
    'relationships': ['person_name', 'relationship_type', 'description', 'significance'],
    # Cognitive architecture tables
    'decisions': ['decision', 'context', 'reasoning', 'outcome'],
    'mistakes': ['mistake', 'context', 'lessons_learned', 'pattern'],
    'reasoning_patterns': ['pattern_name', 'description', 'examples'],
    'value_hierarchies': ['value', 'importance', 'examples'],
    'cognitive_biases': ['bias', 'manifestation', 'triggers'],
    'contradictions': ['contradiction', 'context', 'resolution'],
    'meaning_structures': ['domain', 'meaning', 'importance'],
    'mortality_awareness': ['aspect', 'perspective', 'impact'],
    'body_knowledge': ['aspect', 'description', 'significance'],
    # Emotional landscape
    'fears': ['fear', 'origin', 'manifestation', 'coping'],
    'joys': ['source', 'description', 'frequency'],
    'sorrows': ['title', 'description', 'what_was_lost', 'impact'],
    'loves': ['what_or_who', 'description', 'why_loved', 'how_expressed'],
    'longings': ['what_is_longed_for', 'description', 'why_unfulfilled'],
    # Growth & wounds
    'wounds': ['title', 'description', 'source', 'how_it_manifests'],
    'healings': ['title', 'what_was_healed', 'how_healed', 'what_helped'],
    'losses': ['what_was_lost', 'description', 'relationship_to_bill', 'impact'],
    'growth': ['title', 'description', 'what_triggered_growth', 'what_was_gained'],
    # Character
    'strengths': ['strength_name', 'description', 'how_developed', 'how_it_helps'],
    'vulnerabilities': ['vulnerability', 'description', 'triggers', 'how_managed'],
    'regrets': ['what_happened', 'what_would_do_differently', 'why_it_matters', 'lessons_learned'],
    'wisdom': ['insight', 'source', 'application'],
    'questions': ['question', 'context', 'why_unresolved', 'current_thinking'],
}


class VectorStore:
    """
    Manages vector embeddings for Bill's cognitive substrate.

    Uses nomic-embed-text-v1.5 for embeddings (768 dimensions)
    and ChromaDB for persistent vector storage.
    """

    def __init__(self, model_name: str = "nomic-ai/nomic-embed-text-v1.5"):
        """Initialize the vector store."""
        print(f"Loading embedding model: {model_name}...")

        # Load embedding model
        self.model = SentenceTransformer(model_name, trust_remote_code=True)

        # Ensure vector DB directory exists
        VECTOR_DB_PATH.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.chroma_client = chromadb.PersistentClient(
            path=str(VECTOR_DB_PATH),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="bill_memories",
            metadata={"description": "Bill Cornelius cognitive substrate embeddings"}
        )

        print(f"Vector store ready. Collection has {self.collection.count()} entries.")

    def embed_text(self, text: str) -> List[float]:
        """Convert text to a 768-dimensional embedding vector."""
        # nomic-embed-text requires a task prefix for best results
        prefixed_text = f"search_document: {text}"
        embedding = self.model.encode(prefixed_text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a search query (uses different prefix for queries)."""
        prefixed_query = f"search_query: {query}"
        embedding = self.model.encode(prefixed_query, convert_to_numpy=True)
        return embedding.tolist()

    def add_entry(self, entry_id: str, text: str, metadata: Dict[str, Any]) -> None:
        """Add a single entry to the vector database."""
        embedding = self.embed_text(text)

        # Ensure all metadata values are strings (ChromaDB requirement)
        clean_metadata = {
            k: str(v) if v is not None else ""
            for k, v in metadata.items()
        }

        self.collection.upsert(
            ids=[entry_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[clean_metadata]
        )

    def query(
        self,
        query_text: str,
        top_k: int = 20,
        tables: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for memories semantically similar to the query.

        Args:
            query_text: The search query
            top_k: Number of results to return
            tables: Optional list of tables to filter by

        Returns:
            List of matching memories with scores
        """
        query_embedding = self.embed_query(query_text)

        # Build filter if tables specified
        where_filter = None
        if tables:
            where_filter = {"source_table": {"$in": tables}}

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        memories = []
        if results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                # Convert distance to similarity score (1 - normalized distance)
                distance = results['distances'][0][i] if results['distances'] else 0
                score = max(0, 1 - (distance / 2))  # Cosine distance is 0-2

                metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                memories.append({
                    'text': doc,
                    'score': score,
                    'table': metadata.get('source_table', 'unknown'),
                    'id': metadata.get('source_id', 'unknown'),
                    'category': metadata.get('category', ''),
                    'metadata': metadata
                })

        return memories

    def find_connections(self, memory_text: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Given a memory, find other related memories.

        This is essentially a query using the memory text itself.
        """
        return self.query(memory_text, top_k=top_k + 1)[1:]  # Skip self

    def get_entry_count(self) -> int:
        """Get the number of entries in the vector database."""
        return self.collection.count()

    def sync_from_sqlite(self, progress_callback=None) -> int:
        """
        Sync all entries from SQLite database to vector store.

        Args:
            progress_callback: Optional function called with (current, total) progress

        Returns:
            Number of entries synced
        """
        if not SQLITE_DB_PATH.exists():
            raise FileNotFoundError(f"SQLite database not found: {SQLITE_DB_PATH}")

        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        total_synced = 0
        total_entries = 0

        # First count total entries
        for table in EMBEDDABLE_TABLES:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                total_entries += cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass  # Table doesn't exist

        current = 0

        for table in EMBEDDABLE_TABLES:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                print(f"  Table {table} not found, skipping...")
                continue

            if not rows:
                continue

            print(f"  Processing {table}: {len(rows)} entries...")

            for row in rows:
                row_dict = dict(row)

                # Build text from relevant fields
                text_parts = []
                fields = TABLE_TEXT_FIELDS.get(table, list(row_dict.keys()))

                for field in fields:
                    if field in row_dict and row_dict[field]:
                        value = str(row_dict[field]).strip()
                        if value and value.lower() not in ['none', 'null', '']:
                            text_parts.append(f"{field}: {value}")

                if not text_parts:
                    # Fallback: use all non-empty string fields
                    for key, value in row_dict.items():
                        if isinstance(value, str) and value.strip():
                            text_parts.append(f"{key}: {value}")

                if not text_parts:
                    continue

                text = "\n".join(text_parts)

                # Create unique ID
                entry_id = f"{table}_{row_dict.get('id', current)}"

                # Metadata
                metadata = {
                    'source_table': table,
                    'source_id': str(row_dict.get('id', '')),
                    'category': str(row_dict.get('category', row_dict.get('aspect', ''))),
                }

                try:
                    self.add_entry(entry_id, text, metadata)
                    total_synced += 1
                except Exception as e:
                    print(f"    Error adding {entry_id}: {e}")

                current += 1
                if progress_callback:
                    progress_callback(current, total_entries)

        conn.close()
        print(f"Sync complete. {total_synced} entries in vector database.")
        return total_synced

    def cluster(self, n_clusters: int = 10) -> List[Dict[str, Any]]:
        """
        Group all memories into semantic clusters.

        Returns list of clusters with representative samples.
        """
        # Get all embeddings
        all_data = self.collection.get(include=['embeddings', 'documents', 'metadatas'])

        if all_data['embeddings'] is None or len(all_data['embeddings']) == 0:
            return []

        embeddings = np.array(all_data['embeddings'])

        # Use K-means clustering
        from sklearn.cluster import KMeans

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        # Group entries by cluster
        clusters = []
        for cluster_id in range(n_clusters):
            mask = labels == cluster_id
            cluster_docs = [d for d, m in zip(all_data['documents'], mask) if m]
            cluster_meta = [m for m, included in zip(all_data['metadatas'], mask) if included]

            if cluster_docs:
                # Get cluster center and find closest document as representative
                center = kmeans.cluster_centers_[cluster_id]
                cluster_embeddings = embeddings[mask]
                distances = np.linalg.norm(cluster_embeddings - center, axis=1)
                representative_idx = np.argmin(distances)

                clusters.append({
                    'id': cluster_id,
                    'size': len(cluster_docs),
                    'representative': cluster_docs[representative_idx][:200],
                    'samples': [d[:100] for d in cluster_docs[:5]],
                    'tables': list(set(m.get('source_table', 'unknown') for m in cluster_meta))
                })

        # Sort by size
        clusters.sort(key=lambda c: c['size'], reverse=True)
        return clusters


# CLI interface for testing
def main():
    import argparse

    parser = argparse.ArgumentParser(description='Vector embedding operations')
    parser.add_argument('--sync', action='store_true', help='Sync from SQLite database')
    parser.add_argument('--query', type=str, help='Search for memories')
    parser.add_argument('--connections', type=str, help='Find connections to a memory')
    parser.add_argument('--cluster', type=int, help='Cluster memories into N groups')
    parser.add_argument('--count', action='store_true', help='Show entry count')

    args = parser.parse_args()

    store = VectorStore()

    if args.sync:
        print("\nSyncing from SQLite database...")
        count = store.sync_from_sqlite()
        print(f"Synced {count} entries.")

    if args.query:
        print(f"\nSearching for: {args.query}")
        results = store.query(args.query, top_k=10)
        print(f"Found {len(results)} results:\n")
        for r in results:
            print(f"  [{r['score']:.2f}] ({r['table']}) {r['text'][:100]}...")
            print()

    if args.connections:
        print(f"\nFinding connections to: {args.connections}")
        results = store.find_connections(args.connections, top_k=10)
        print(f"Found {len(results)} connections:\n")
        for r in results:
            print(f"  [{r['score']:.2f}] ({r['table']}) {r['text'][:100]}...")
            print()

    if args.cluster:
        print(f"\nClustering into {args.cluster} groups...")
        clusters = store.cluster(n_clusters=args.cluster)
        for c in clusters:
            print(f"\nCluster {c['id']} ({c['size']} entries, tables: {c['tables']}):")
            print(f"  Representative: {c['representative']}")

    if args.count:
        print(f"\nVector database has {store.get_entry_count()} entries.")


if __name__ == '__main__':
    main()
