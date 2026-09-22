import re
from typing import Iterator, Optional, Set, Tuple

from quyca.domain.models.calculations_model import Calculations

PARENTHETICAL_SUFFIX = re.compile(r"\s*\([^)]*\)")


def _normalize_label(raw_label: str) -> str:
    return PARENTHETICAL_SUFFIX.sub("", raw_label).strip()


def node_label(node) -> Optional[str]:
    name = getattr(node, "name", None)
    if not name:
        return None
    return _normalize_label(name)


def parse_institutional_coauthorship_network_nodes(data: Calculations) -> Iterator[str]:
    network = data.coauthorship_network
    seen: Set[str] = set()
    for node in network.nodes or []:
        label = node_label(node)
        if label and label not in seen:
            seen.add(label)
            yield label


def parse_institutional_coauthorship_network_edges(data: Calculations) -> Iterator[Tuple[str, str]]:
    network = data.coauthorship_network
    labels_by_id = {node.id: node_label(node) for node in (network.nodes or [])}

    for edge in network.edges or []:
        source_label = labels_by_id.get(edge.source)
        target_label = labels_by_id.get(edge.target)
        if source_label and target_label:
            yield source_label, target_label
