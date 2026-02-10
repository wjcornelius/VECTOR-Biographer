# Data Visualizations for Cognitive Substrate
"""
Interactive visualizations for exploring Bill's memories and life patterns.
Uses Plotly for rich, interactive charts.
"""

import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import webbrowser
import tempfile

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import numpy as np
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    from sklearn.manifold import TSNE
    from sklearn.cluster import KMeans
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# Color scheme matching the GUI theme
COLORS = {
    'bg': '#1a1a2e',
    'panel': '#16213e',
    'accent': '#00d9ff',
    'text': '#e8e8e8',

    # Original categories
    'self_knowledge': '#3b82f6',   # Blue
    'life_events': '#22c55e',      # Green
    'stories': '#f59e0b',          # Amber
    'relationships': '#ec4899',    # Pink
    'philosophies': '#6366f1',     # Indigo

    # Emotional landscape - warm colors for positive, cool for difficult
    'joys': '#fbbf24',             # Yellow/Gold
    'loves': '#f472b6',            # Light Pink
    'sorrows': '#6b7280',          # Gray
    'fears': '#ef4444',            # Red
    'longings': '#a78bfa',         # Light Purple

    # Growth & wounds
    'wounds': '#991b1b',           # Dark Red
    'healings': '#10b981',         # Emerald
    'losses': '#78716c',           # Stone
    'growth': '#34d399',           # Light Green

    # Character
    'strengths': '#2563eb',        # Bright Blue
    'vulnerabilities': '#c084fc',  # Purple
    'regrets': '#fb923c',          # Orange
    'wisdom': '#8b5cf6',           # Violet
    'questions': '#14b8a6',        # Teal

    # Cognitive architecture
    'decisions': '#06b6d4',        # Cyan
    'mistakes': '#f97316',         # Dark Orange
    'reasoning_patterns': '#64748b',  # Slate
    'value_hierarchies': '#94a3b8',   # Light Slate
    'cognitive_biases': '#475569',    # Dark Slate
    'contradictions': '#f43f5e',      # Rose
    'meaning_structures': '#818cf8',  # Light Indigo
    'mortality_awareness': '#a1a1aa', # Zinc
    'beauties': '#fcd34d',            # Light Yellow
    'body_knowledge': '#84cc16',      # Lime

    'default': '#64748b',
}


def get_table_color(table: str) -> str:
    """Get color for a memory table type."""
    return COLORS.get(table, COLORS['default'])


class MemoryVisualizer:
    """Creates interactive visualizations of Bill's memories."""

    def __init__(self, vector_store=None):
        """Initialize with optional vector store for embeddings."""
        self.vector_store = vector_store
        self.output_dir = Path(tempfile.gettempdir()) / "cognitive_substrate_viz"
        self.output_dir.mkdir(exist_ok=True)

    def create_constellation_map(self, show: bool = True) -> Optional[str]:
        """
        Create a 2D map of all memories clustered by semantic similarity.
        Uses t-SNE to reduce 768-dim embeddings to 2D.
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly not available for visualizations")
            return None

        if not SKLEARN_AVAILABLE:
            print("sklearn not available for dimensionality reduction")
            return None

        if not self.vector_store:
            print("No vector store provided")
            return None

        # Get all data from ChromaDB
        print("Loading embeddings...")
        collection = self.vector_store.collection
        all_data = collection.get(include=['embeddings', 'documents', 'metadatas'])

        # Safely check for embeddings (handles None, empty list, and numpy arrays)
        embeddings_data = all_data.get('embeddings')
        if embeddings_data is None:
            print("No embeddings found")
            return None

        embeddings = np.array(embeddings_data)
        if embeddings.size == 0:
            print("No embeddings found")
            return None
        documents = all_data['documents']
        metadatas = all_data['metadatas']

        print(f"Reducing {len(embeddings)} embeddings to 2D...")

        # Use t-SNE for dimensionality reduction
        tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(embeddings)-1))
        coords = tsne.fit_transform(embeddings)

        # Cluster for coloring
        n_clusters = min(10, len(embeddings) // 10)
        if n_clusters > 1:
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(embeddings)
        else:
            clusters = [0] * len(embeddings)

        # Prepare data for plotting
        tables = [m.get('source_table', 'unknown') for m in metadatas]
        colors = [get_table_color(t) for t in tables]
        texts = [d[:100] + '...' if len(d) > 100 else d for d in documents]

        # Create hover text
        hover_texts = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            table = meta.get('source_table', 'unknown')
            preview = doc[:200] + '...' if len(doc) > 200 else doc
            hover_texts.append(f"<b>{table}</b><br>{preview}")

        # Create figure
        fig = go.Figure()

        # Add points by table type for legend
        for table in set(tables):
            mask = [t == table for t in tables]
            fig.add_trace(go.Scatter(
                x=[coords[i, 0] for i, m in enumerate(mask) if m],
                y=[coords[i, 1] for i, m in enumerate(mask) if m],
                mode='markers',
                name=table.replace('_', ' ').title(),
                marker=dict(
                    size=8,
                    color=get_table_color(table),
                    opacity=0.7,
                    line=dict(width=1, color='white')
                ),
                text=[hover_texts[i] for i, m in enumerate(mask) if m],
                hoverinfo='text'
            ))

        # Layout - legend positioned below chart horizontally to fit all categories
        fig.update_layout(
            title={
                'text': 'Memory Constellation Map',
                'font': {'size': 24, 'color': COLORS['text']}
            },
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['panel'],
            font=dict(color=COLORS['text']),
            legend=dict(
                bgcolor='rgba(22, 33, 62, 0.8)',
                bordercolor=COLORS['accent'],
                borderwidth=1,
                orientation='h',  # Horizontal legend
                yanchor='top',
                y=-0.05,  # Below the chart
                xanchor='center',
                x=0.5,
                font=dict(size=10),
                itemwidth=30,
                traceorder='normal'
            ),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hovermode='closest',
            margin=dict(b=150)  # Extra bottom margin for legend
        )

        # Save and optionally show
        output_path = self.output_dir / "constellation_map.html"
        fig.write_html(str(output_path))
        print(f"Saved to: {output_path}")

        if show:
            webbrowser.open(f'file://{output_path}')

        return str(output_path)

    def create_theme_heatmap(self, show: bool = True) -> Optional[str]:
        """
        Create a heatmap showing coverage depth of different life themes.
        """
        if not PLOTLY_AVAILABLE:
            return None

        if not self.vector_store:
            return None

        # Get table counts
        collection = self.vector_store.collection
        all_data = collection.get(include=['metadatas'])

        # Safely check for metadatas
        metadatas = all_data.get('metadatas')
        if metadatas is None or len(metadatas) == 0:
            return None

        # Count entries by table
        table_counts = {}
        for meta in metadatas:
            table = meta.get('source_table', 'unknown')
            table_counts[table] = table_counts.get(table, 0) + 1

        # Sort by count
        sorted_tables = sorted(table_counts.items(), key=lambda x: x[1], reverse=True)
        tables = [t[0].replace('_', ' ').title() for t in sorted_tables]
        counts = [t[1] for t in sorted_tables]
        colors = [get_table_color(t[0]) for t in sorted_tables]

        # Create horizontal bar chart
        fig = go.Figure()

        fig.add_trace(go.Bar(
            y=tables,
            x=counts,
            orientation='h',
            marker=dict(color=colors),
            text=counts,
            textposition='auto',
        ))

        fig.update_layout(
            title={
                'text': 'Memory Coverage by Category',
                'font': {'size': 24, 'color': COLORS['text']}
            },
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['panel'],
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Number of Entries', gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(title=''),
            height=max(400, len(tables) * 30)
        )

        output_path = self.output_dir / "theme_heatmap.html"
        fig.write_html(str(output_path))

        if show:
            webbrowser.open(f'file://{output_path}')

        return str(output_path)

    def create_cluster_view(self, n_clusters: int = 8, show: bool = True) -> Optional[str]:
        """
        Create a view showing semantic clusters with their themes.
        Uses dominant table types to label each cluster meaningfully.
        """
        if not PLOTLY_AVAILABLE or not SKLEARN_AVAILABLE:
            return None

        if not self.vector_store:
            return None

        # Get clusters from vector store
        clusters = self.vector_store.cluster(n_clusters=n_clusters)

        if not clusters:
            return None

        def get_cluster_theme(cluster: dict) -> str:
            """Generate a meaningful label based on dominant table types."""
            tables = cluster.get('tables', [])
            if not tables:
                return "Miscellaneous"

            # Map table names to friendly theme names
            theme_map = {
                'life_events': 'Life Events',
                'relationships': 'Relationships',
                'stories': 'Stories',
                'self_knowledge': 'Self Knowledge',
                'joys': 'Joys',
                'sorrows': 'Sorrows',
                'wounds': 'Wounds',
                'fears': 'Fears',
                'loves': 'Loves',
                'losses': 'Losses',
                'healings': 'Healings',
                'growth': 'Growth',
                'strengths': 'Strengths',
                'vulnerabilities': 'Vulnerabilities',
                'regrets': 'Regrets',
                'wisdom': 'Wisdom',
                'decisions': 'Decisions',
                'mistakes': 'Mistakes',
                'questions': 'Questions',
                'longings': 'Longings',
                'philosophies': 'Philosophies',
                'creative_works': 'Creative Works',
                'skills_competencies': 'Skills',
                'sensory_memories': 'Sensory',
                'aspirations': 'Aspirations',
            }

            # Get top 2 table types for the label
            themed_tables = [theme_map.get(t, t.replace('_', ' ').title()) for t in tables[:2]]
            return ' & '.join(themed_tables) if themed_tables else "Mixed"

        # Create sunburst chart
        labels = ['Bill\'s Memories']
        parents = ['']
        values = [sum(c['size'] for c in clusters)]
        colors_list = [COLORS['accent']]
        hover_texts = ['All memories in the cognitive substrate']

        for i, cluster in enumerate(clusters):
            theme = get_cluster_theme(cluster)
            cluster_label = f"{theme} ({cluster['size']})"
            labels.append(cluster_label)
            parents.append('Bill\'s Memories')
            values.append(cluster['size'])
            colors_list.append(px.colors.qualitative.Set3[i % 12])

            # Create hover text with representative sample
            rep = cluster.get('representative', '')[:150]
            tables_str = ', '.join(cluster.get('tables', [])[:3])
            hover_texts.append(f"Categories: {tables_str}<br><br>Sample: {rep}...")

            # Add sample entries as children
            for j, sample in enumerate(cluster.get('samples', [])[:3]):
                sample_label = sample[:40] + '...' if len(sample) > 40 else sample
                labels.append(sample_label)
                parents.append(cluster_label)
                values.append(1)
                colors_list.append(px.colors.qualitative.Pastel[i % 10])
                hover_texts.append(sample)

        fig = go.Figure(go.Sunburst(
            labels=labels,
            parents=parents,
            values=values,
            branchvalues='total',
            marker=dict(colors=colors_list),
            textinfo='label',
            insidetextorientation='radial',
            hovertext=hover_texts,
            hoverinfo='text'
        ))

        # Build legend annotation showing cluster themes
        legend_text = "<b>Cluster Themes:</b><br>"
        for i, cluster in enumerate(clusters):
            theme = get_cluster_theme(cluster)
            legend_text += f"  {i+1}. {theme} ({cluster['size']} entries)<br>"

        fig.update_layout(
            title={
                'text': 'Memory Clusters by Theme',
                'font': {'size': 24, 'color': COLORS['text']}
            },
            paper_bgcolor=COLORS['bg'],
            font=dict(color=COLORS['text']),
            margin=dict(t=50, l=0, r=250, b=0),  # Right margin for legend
            annotations=[
                dict(
                    x=1.02, y=0.98,
                    xref='paper', yref='paper',
                    text=legend_text,
                    showarrow=False,
                    font=dict(color=COLORS['text'], size=11),
                    align='left',
                    bgcolor='rgba(22, 33, 62, 0.9)',
                    bordercolor=COLORS['accent'],
                    borderwidth=1,
                    borderpad=10,
                    xanchor='left',
                    yanchor='top'
                )
            ]
        )

        output_path = self.output_dir / "cluster_view.html"
        fig.write_html(str(output_path))

        if show:
            webbrowser.open(f'file://{output_path}')

        return str(output_path)

    def create_session_growth_chart(self, session_data: List[Dict], show: bool = True) -> Optional[str]:
        """
        Create a chart showing knowledge base growth over sessions.
        """
        if not PLOTLY_AVAILABLE:
            return None

        if not session_data:
            return None

        # Extract data
        dates = [s.get('date', f'Session {i}') for i, s in enumerate(session_data)]
        counts = [s.get('total_entries', 0) for s in session_data]

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=dates,
            y=counts,
            mode='lines+markers',
            line=dict(color=COLORS['accent'], width=3),
            marker=dict(size=10, color=COLORS['accent']),
            fill='tozeroy',
            fillcolor='rgba(0, 217, 255, 0.2)'
        ))

        fig.update_layout(
            title={
                'text': 'Knowledge Base Growth',
                'font': {'size': 24, 'color': COLORS['text']}
            },
            paper_bgcolor=COLORS['bg'],
            plot_bgcolor=COLORS['panel'],
            font=dict(color=COLORS['text']),
            xaxis=dict(title='Session', gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(title='Total Entries', gridcolor='rgba(255,255,255,0.1)')
        )

        output_path = self.output_dir / "session_growth.html"
        fig.write_html(str(output_path))

        if show:
            webbrowser.open(f'file://{output_path}')

        return str(output_path)

    def create_gap_radar(self, db_path: str = None, show: bool = True) -> Optional[str]:
        """
        Create a radar chart showing coverage gaps in the cognitive substrate.
        Shows current entries vs. target for key life categories.
        """
        if not PLOTLY_AVAILABLE:
            print("Plotly not available for visualizations")
            return None

        import sqlite3

        # Default database path
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "bill_knowledge_base.db"

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Categories to track with target counts
            # Target represents "well-covered" for a comprehensive biography
            categories_info = {
                'relationships': {'target': 50, 'color': COLORS['relationships'], 'label': 'Key People'},
                'life_events': {'target': 100, 'color': COLORS['life_events'], 'label': 'Life Events'},
                'stories': {'target': 30, 'color': COLORS['stories'], 'label': 'Stories'},
                'joys': {'target': 20, 'color': '#22c55e', 'label': 'Joys'},
                'sorrows': {'target': 15, 'color': '#ef4444', 'label': 'Sorrows'},
                'loves': {'target': 15, 'color': '#ec4899', 'label': 'Loves'},
                'fears': {'target': 10, 'color': COLORS['fears'], 'label': 'Fears'},
                'wounds': {'target': 10, 'color': '#f97316', 'label': 'Wounds'},
                'healings': {'target': 10, 'color': '#10b981', 'label': 'Healings'},
                'strengths': {'target': 15, 'color': '#3b82f6', 'label': 'Strengths'},
                'vulnerabilities': {'target': 10, 'color': '#8b5cf6', 'label': 'Vulnerabilities'},
                'wisdom': {'target': 25, 'color': COLORS['wisdom'], 'label': 'Wisdom'},
                'decisions': {'target': 20, 'color': COLORS['decisions'], 'label': 'Decisions'},
                'regrets': {'target': 10, 'color': '#f59e0b', 'label': 'Regrets'},
                'questions': {'target': 10, 'color': '#06b6d4', 'label': 'Questions'},
            }

            # Get current counts
            current_counts = {}
            for table in categories_info.keys():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    current_counts[table] = cursor.fetchone()[0]
                except sqlite3.Error:
                    current_counts[table] = 0

            conn.close()

            # Prepare data for radar chart
            categories = list(categories_info.keys())
            labels = [categories_info[c]['label'] for c in categories]
            targets = [categories_info[c]['target'] for c in categories]
            actuals = [current_counts[c] for c in categories]

            # Calculate percentages (capped at 100%)
            percentages = [min(100, (a / t) * 100) if t > 0 else 0 for a, t in zip(actuals, targets)]

            # Create radar chart
            fig = go.Figure()

            # Add target (100% for all) as reference
            fig.add_trace(go.Scatterpolar(
                r=[100] * len(categories) + [100],  # Close the shape
                theta=labels + [labels[0]],
                fill='toself',
                fillcolor='rgba(100, 116, 139, 0.1)',
                line=dict(color='rgba(100, 116, 139, 0.5)', width=1, dash='dash'),
                name='Target (100%)'
            ))

            # Add actual coverage
            fig.add_trace(go.Scatterpolar(
                r=percentages + [percentages[0]],  # Close the shape
                theta=labels + [labels[0]],
                fill='toself',
                fillcolor='rgba(0, 217, 255, 0.3)',
                line=dict(color=COLORS['accent'], width=2),
                name='Current Coverage',
                text=[f"{labels[i]}: {actuals[i]}/{targets[i]} ({percentages[i]:.0f}%)"
                      for i in range(len(categories))] + [""],
                hoverinfo='text'
            ))

            # Layout
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[0, 100],
                        ticksuffix='%',
                        tickfont=dict(color=COLORS['text']),
                        gridcolor='rgba(255,255,255,0.1)'
                    ),
                    angularaxis=dict(
                        tickfont=dict(color=COLORS['text'], size=12),
                        gridcolor='rgba(255,255,255,0.1)'
                    ),
                    bgcolor=COLORS['panel']
                ),
                paper_bgcolor=COLORS['bg'],
                font=dict(color=COLORS['text']),
                title={
                    'text': 'Biography Coverage Radar',
                    'font': {'size': 24, 'color': COLORS['text']},
                    'x': 0.5
                },
                legend=dict(
                    bgcolor='rgba(22, 33, 62, 0.8)',
                    bordercolor=COLORS['accent'],
                    borderwidth=1,
                    x=0.85,
                    y=0.95
                ),
                showlegend=True
            )

            # Add annotations for gaps
            gaps = [(labels[i], percentages[i], actuals[i], targets[i])
                    for i in range(len(categories)) if percentages[i] < 30]

            if gaps:
                gap_text = "Significant gaps:<br>" + "<br>".join(
                    [f"  {g[0]}: {g[2]}/{g[3]} ({g[1]:.0f}%)" for g in gaps[:5]]
                )
                fig.add_annotation(
                    x=0.02, y=0.02,
                    xref='paper', yref='paper',
                    text=gap_text,
                    showarrow=False,
                    font=dict(color='#ef4444', size=11),
                    align='left',
                    bgcolor='rgba(22, 33, 62, 0.9)',
                    bordercolor='#ef4444',
                    borderwidth=1,
                    borderpad=5
                )

            output_path = self.output_dir / "gap_radar.html"
            fig.write_html(str(output_path))
            print(f"Saved to: {output_path}")

            if show:
                webbrowser.open(f'file://{output_path}')

            return str(output_path)

        except Exception as e:
            print(f"Error creating gap radar: {e}")
            return None


def create_all_visualizations(vector_store=None, show: bool = True):
    """Create all available visualizations."""
    viz = MemoryVisualizer(vector_store)

    paths = {}

    print("\nCreating Memory Constellation Map...")
    paths['constellation'] = viz.create_constellation_map(show=show)

    print("\nCreating Theme Heatmap...")
    paths['heatmap'] = viz.create_theme_heatmap(show=show)

    print("\nCreating Cluster View...")
    paths['clusters'] = viz.create_cluster_view(show=show)

    return paths


if __name__ == '__main__':
    # Test visualizations
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    try:
        from biographer.embeddings import VectorStore
        store = VectorStore()
        create_all_visualizations(store, show=True)
    except Exception as e:
        print(f"Error: {e}")
