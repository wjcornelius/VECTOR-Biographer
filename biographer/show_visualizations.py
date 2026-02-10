"""
Quick visualization launcher - no voice input required.
Use this to view/screenshot the constellation and cluster maps.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from biographer.embeddings import VectorStore
from biographer.gui.visualizations import MemoryVisualizer

def main():
    print("=" * 60)
    print("COGNITIVE SUBSTRATE - Visualization Viewer")
    print("=" * 60)
    print()

    print("Loading vector store...")
    store = VectorStore()
    entry_count = store.get_entry_count()
    print(f"Vector database has {entry_count} entries")
    print()

    visualizer = MemoryVisualizer(store)

    while True:
        print("\nVisualization Options:")
        print("  1. Constellation Map (t-SNE projection)")
        print("  2. Cluster View (sunburst chart)")
        print("  3. Coverage Heatmap (entries by category)")
        print("  4. Gap Radar (coverage vs targets)")
        print("  5. Exit")
        print()

        choice = input("Enter choice (1-5): ").strip()

        if choice == '1':
            print("\nGenerating constellation map...")
            path = visualizer.create_constellation_map(show=True)
            print(f"Saved to: {path}")
            print("(Opened in browser - take your screenshot)")

        elif choice == '2':
            print("\nGenerating cluster view...")
            path = visualizer.create_cluster_view(show=True)
            print(f"Saved to: {path}")
            print("(Opened in browser - take your screenshot)")

        elif choice == '3':
            print("\nGenerating coverage heatmap...")
            path = visualizer.create_theme_heatmap(show=True)
            print(f"Saved to: {path}")
            print("(Opened in browser - take your screenshot)")

        elif choice == '4':
            print("\nGenerating gap radar...")
            path = visualizer.create_gap_radar(show=True)
            print(f"Saved to: {path}")
            print("(Opened in browser - take your screenshot)")

        elif choice == '5':
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice, try again.")


if __name__ == '__main__':
    main()
