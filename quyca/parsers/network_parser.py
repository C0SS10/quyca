from typing import Dict, Any, List

from quyca.models.calculations_model import Calculations


def parse_institutional_coauthorship_network(data: Calculations) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    network = data.coauthorship_network

    sorted_nodes = sorted(network.nodes or [], key=lambda x: x.degree, reverse=True)[:50]

    nodes_ids = [node.id for node in sorted_nodes]
    nodes_data = [node.model_dump() for node in sorted_nodes]

    edges_data = []
    if network.edges is not None:
        for edge in network.edges:
            if edge.source in nodes_ids and edge.target in nodes_ids:
                edges_data.append(edge.model_dump())

    return {"plot": {"nodes": nodes_data, "edges": edges_data}}
