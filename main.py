#!/usr/bin/env python3
import requests
import re
from typing import Dict, List, Tuple
import argparse
from tabulate import tabulate
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

class MetricsExplorer:
    def __init__(self, host: str = "localhost", port: int = 9100):
        self.base_url = f"http://{host}:{port}"
        self.metrics_cache = None
        self.help_cache = {}

    def fetch_metrics(self) -> List[Tuple[str, float, Dict[str, str], str]]:
        """Fetch and parse all metrics with their help text."""
        response = requests.get(f"{self.base_url}/metrics")
        response.raise_for_status()

        metrics = []
        current_help = ""
        current_type = ""

        for line in response.text.split('\n'):
            if line.startswith('# HELP '):
                current_help = line[7:].split(' ', 1)[1]
            elif line.startswith('# TYPE '):
                current_type = line[7:].split(' ', 1)[1]
            elif not line.startswith('#') and line.strip():
                # Parse metric line
                try:
                    name_part, value_str = line.split(' ')

                    # Parse labels if they exist
                    labels = {}
                    if '{' in name_part:
                        metric_name = name_part[:name_part.index('{')]
                        labels_str = name_part[name_part.index('{') + 1:name_part.rindex('}')]

                        # Parse individual labels
                        for label_pair in re.findall(r'(\w+)="([^"]*)"', labels_str):
                            labels[label_pair[0]] = label_pair[1]
                    else:
                        metric_name = name_part

                    metrics.append((metric_name, float(value_str), labels, current_help))

                    # Cache help text
                    if metric_name not in self.help_cache:
                        self.help_cache[metric_name] = {
                            'help': current_help,
                            'type': current_type
                        }
                except Exception:
                    continue

        return metrics

    def group_metrics(self) -> Dict[str, List[str]]:
        """Group metrics by their prefix."""
        if not self.metrics_cache:
            self.metrics_cache = self.fetch_metrics()

        groups = {}
        for metric_name, _, _, _ in self.metrics_cache:
            # Split on underscore and take first part
            group = metric_name.split('_')[0]
            if group not in groups:
                groups[group] = []
            if metric_name not in groups[group]:
                groups[group].append(metric_name)

        return groups

    def search_metrics(self, search_term: str) -> List[Tuple[str, str, float]]:
        """Search metrics by name or help text."""
        if not self.metrics_cache:
            self.metrics_cache = self.fetch_metrics()

        results = []
        seen = set()  # To avoid duplicates

        for metric_name, value, labels, help_text in self.metrics_cache:
            if search_term.lower() in metric_name.lower() or search_term.lower() in help_text.lower():
                if metric_name not in seen:
                    results.append((metric_name, help_text, value))
                    seen.add(metric_name)

        return results

    def show_metric_details(self, metric_name: str) -> None:
        """Show detailed information about a specific metric."""
        if not self.metrics_cache:
            self.metrics_cache = self.fetch_metrics()

        print(f"\nDetails for metric: {metric_name}")
        print("-" * 50)

        if metric_name in self.help_cache:
            print(f"Type: {self.help_cache[metric_name]['type']}")
            print(f"Help: {self.help_cache[metric_name]['help']}")

        print("\nCurrent values:")
        values = [(metric_name, value, labels) for name, value, labels, _ in self.metrics_cache if name == metric_name]

        if values:
            for _, value, labels in values:
                if labels:
                    print(f"Value: {value} (Labels: {labels})")
                else:
                    print(f"Value: {value}")
        else:
            print("No current values found")

    def interactive(self):
        """Start interactive exploration."""
        while True:
            print("\nMetrics Explorer")
            print("1. List metric groups")
            print("2. Search metrics")
            print("3. Show metric details")
            print("4. Exit")

            choice = input("\nEnter your choice (1-4): ")

            if choice == '1':
                groups = self.group_metrics()
                for group, metrics in groups.items():
                    print(f"\n{group}:")
                    for metric in metrics:
                        print(f"  - {metric}")

            elif choice == '2':
                search_term = input("Enter search term: ")
                results = self.search_metrics(search_term)
                if results:
                    print("\nSearch results:")
                    table = [(name, help_text[:100] + "..." if len(help_text) > 100 else help_text)
                            for name, help_text, _ in results]
                    print(tabulate(table, headers=['Metric', 'Description'], tablefmt='grid'))
                else:
                    print("No results found")

            elif choice == '3':
                if not self.metrics_cache:
                    self.metrics_cache = self.fetch_metrics()
                metrics = sorted(list(set(m[0] for m in self.metrics_cache)))
                completer = WordCompleter(metrics, ignore_case=True)
                metric_name = prompt('Enter metric name: ', completer=completer)
                self.show_metric_details(metric_name)

            elif choice == '4':
                break

def main():
    parser = argparse.ArgumentParser(description='Explore Prometheus Node Exporter metrics')
    parser.add_argument('--host', default='localhost', help='Node exporter host')
    parser.add_argument('--port', type=int, default=9100, help='Node exporter port')
    args = parser.parse_args()

    explorer = MetricsExplorer(args.host, args.port)
    explorer.interactive()

if __name__ == "__main__":
    main()
