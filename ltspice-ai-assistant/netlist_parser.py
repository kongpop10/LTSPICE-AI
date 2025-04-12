# netlist_parser.py
import re

def extract_plot_directives(netlist_content: str) -> list[str]:
    """
    Extracts node names from .plot directives in a SPICE netlist.

    Args:
        netlist_content: The SPICE netlist as a string.

    Returns:
        A list of node names to be plotted.
    """
    plot_nodes = []
    raw_nodes = []  # Store the original node strings for debugging

    # Regular expression to match .plot directives
    # This pattern matches .plot followed by any simulation type (tran, ac, etc.) and then captures the node names
    plot_pattern = r'^\s*\.plot\s+(?:tran|ac|dc|noise|op)?\s+(.+)$'

    # Find all .plot directives in the netlist
    for line in netlist_content.splitlines():
        match = re.match(plot_pattern, line, re.IGNORECASE)
        if match:
            # Extract the node names from the directive
            nodes_part = match.group(1).strip()
            print(f"Found .plot directive: {nodes_part}")

            # Split by whitespace to get individual node names
            # This handles basic formats like ".plot V(out) V(in)"
            nodes = re.split(r'\s+', nodes_part)

            # Add each node to the list
            for node in nodes:
                # Store the original node string
                raw_nodes.append(node)

                # Check if it's a voltage/current node format like V(OUT) or I(R1)
                if re.search(r'[IV]\(', node, re.IGNORECASE):
                    # Process as a standard V() or I() node
                    try:
                        # Extract the node name from formats like V(out) or I(R1)
                        # First, get the type (V or I)
                        node_type = node.split('(')[0].upper()
                        # Then get the node name inside the parentheses
                        node_name = node.split('(')[1].split(')')[0]

                        # Reconstruct in a standardized format
                        formatted_node = f"{node_type}({node_name})"  # Preserve original case
                        formatted_node_upper = f"{node_type}({node_name.upper()})"  # Uppercase version

                        if formatted_node not in plot_nodes:
                            plot_nodes.append(formatted_node)
                            print(f"Added node: {formatted_node}")

                        # Also add the uppercase version if different
                        if formatted_node_upper != formatted_node and formatted_node_upper not in plot_nodes:
                            plot_nodes.append(formatted_node_upper)
                            print(f"Added uppercase node: {formatted_node_upper}")

                        # Also add just the node name for better matching
                        if node_name not in plot_nodes:
                            plot_nodes.append(node_name)
                            print(f"Added node name: {node_name}")

                        # Add uppercase version of node name
                        if node_name.upper() != node_name and node_name.upper() not in plot_nodes:
                            plot_nodes.append(node_name.upper())
                            print(f"Added uppercase node name: {node_name.upper()}")

                    except (IndexError, ValueError) as e:
                        print(f"Error parsing node {node}: {e}")
                        # If parsing fails, just add the original node name
                        if node not in plot_nodes:
                            plot_nodes.append(node)
                            print(f"Added original node: {node}")
                else:
                    # It might be a direct node name like 'OUT' without V() wrapper
                    # Add it directly to the list
                    if node not in plot_nodes:
                        plot_nodes.append(node)
                        print(f"Added direct node name: {node}")

                    # Also add with V() wrapper for better matching
                    v_node = f"V({node})"
                    if v_node not in plot_nodes:
                        plot_nodes.append(v_node)
                        print(f"Added V() wrapped node: {v_node}")

                    # Add uppercase versions
                    if node.upper() != node and node.upper() not in plot_nodes:
                        plot_nodes.append(node.upper())
                        print(f"Added uppercase direct node: {node.upper()}")

                    v_node_upper = f"V({node.upper()})"
                    if v_node_upper != v_node and v_node_upper not in plot_nodes:
                        plot_nodes.append(v_node_upper)
                        print(f"Added uppercase V() wrapped node: {v_node_upper}")

                # This code block is now handled in the if/else structure above

    print(f"Raw nodes from .plot directives: {raw_nodes}")
    print(f"Processed nodes for matching: {plot_nodes}")
    return plot_nodes
