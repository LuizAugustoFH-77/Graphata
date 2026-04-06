from __future__ import annotations

from collections import defaultdict, deque
import math


def compute_automaton_layout(
    state_names,
    transitions,
    initial_states,
    width,
    height,
    node_radius=25,
):
    names = list(dict.fromkeys(state_names))
    if not names:
        return {}

    width = max(int(width), 360)
    height = max(int(height), 260)

    graph, reverse, undirected = _build_graph(names, transitions)
    if _is_dense_graph(names, transitions, graph, reverse):
        order = _dense_order(names, graph, reverse, undirected, set(initial_states))
        positions, anchors = _seed_dense_grid(order, initial_states, width, height, node_radius)
        positions = _relax_positions(
            positions,
            anchors,
            {0: order},
            transitions,
            undirected,
            width,
            height,
            node_radius,
        )
        positions = _spread_overlaps(positions, width, height, node_radius)
        return _fit_positions(positions, width, height, node_radius)

    layer_map = _assign_layers(names, graph, reverse, undirected, set(initial_states))
    layers = _order_layers(names, layer_map, graph, reverse, undirected)
    positions, anchors = _seed_positions(layers, width, height, node_radius)
    positions = _relax_positions(
        positions,
        anchors,
        layers,
        transitions,
        undirected,
        width,
        height,
        node_radius,
    )
    positions = _spread_overlaps(positions, width, height, node_radius)
    return _fit_positions(positions, width, height, node_radius)


def _edge_endpoints(transition):
    if hasattr(transition, "source") and hasattr(transition, "target"):
        return transition.source, transition.target
    return transition


def _build_graph(names, transitions):
    name_set = set(names)
    graph = {name: set() for name in names}
    reverse = {name: set() for name in names}
    undirected = {name: set() for name in names}

    seen = set()
    for transition in transitions:
        source, target = _edge_endpoints(transition)
        if source not in name_set or target not in name_set:
            continue
        edge = (source, target)
        if edge in seen:
            continue
        seen.add(edge)
        if source != target:
            graph[source].add(target)
            reverse[target].add(source)
            undirected[source].add(target)
            undirected[target].add(source)

    return graph, reverse, undirected


def _is_dense_graph(names, transitions, graph, reverse):
    n = len(names)
    if n < 10:
        return False

    unique_edges = {
        _edge_endpoints(transition)
        for transition in transitions
        if _edge_endpoints(transition)[0] in graph and _edge_endpoints(transition)[1] in graph
    }
    avg_out = len(unique_edges) / max(1, n)
    max_in = max((len(reverse[name]) for name in names), default=0)
    max_out = max((len(graph[name]) for name in names), default=0)
    return avg_out >= 2.6 or max_in >= max(6, n // 3) or max_out >= max(6, n // 3)


def _dense_order(names, graph, reverse, undirected, initial_states):
    numeric_order = _numeric_state_order(names)
    if numeric_order:
        return numeric_order

    layer_map = _assign_layers(names, graph, reverse, undirected, initial_states)
    layers = _order_layers(names, layer_map, graph, reverse, undirected)
    order = []
    for lvl in sorted(layers):
        order.extend(layers[lvl])
    return order


def _numeric_state_order(names):
    parsed = []
    for idx, name in enumerate(names):
        suffix = "".join(ch for ch in name if ch.isdigit())
        if not suffix:
            return None
        parsed.append((int(suffix), idx, name))
    parsed.sort()
    return [name for _, _, name in parsed]


def _assign_layers(names, graph, reverse, undirected, initial_states):
    ordered_initials = [name for name in names if name in initial_states]
    if not ordered_initials:
        ordered_initials = [names[0]]

    layer = {}
    queue = deque(ordered_initials)
    for name in ordered_initials:
        layer[name] = 0

    while queue:
        current = queue.popleft()
        for target in sorted(graph[current]):
            if target not in layer:
                layer[target] = layer[current] + 1
                queue.append(target)

    current_max = max(layer.values()) if layer else 0
    remaining = [name for name in names if name not in layer]

    while remaining:
        component = _weak_component(remaining[0], undirected, set(remaining))
        roots = [name for name in component if not (reverse[name] & component)]
        if not roots:
            roots = sorted(component, key=lambda name: (-len(graph[name]), name))[:1]
        roots = sorted(roots)

        directed = _distance_map(component, graph, roots)
        undirected_dist = _distance_map(component, undirected, roots)

        predecessor_layers = [
            layer[pred]
            for name in component
            for pred in reverse[name]
            if pred in layer
        ]
        if predecessor_layers:
            base_layer = max(predecessor_layers) + 1
        else:
            base_layer = current_max + (2 if layer else 0)

        for name in sorted(component, key=lambda item: names.index(item)):
            rel = directed.get(name, undirected_dist.get(name, 0))
            layer[name] = base_layer + rel

        current_max = max(layer.values())
        remaining = [name for name in names if name not in layer]

    return layer


def _weak_component(start, undirected, allowed):
    component = set()
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current in component:
            continue
        component.add(current)
        for neighbor in undirected[current]:
            if neighbor in allowed and neighbor not in component:
                queue.append(neighbor)
    return component


def _distance_map(component, adjacency, roots):
    distances = {}
    queue = deque()
    for root in roots:
        distances[root] = 0
        queue.append(root)

    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency[current]):
            if neighbor in component and neighbor not in distances:
                distances[neighbor] = distances[current] + 1
                queue.append(neighbor)

    return distances


def _order_layers(names, layer_map, graph, reverse, undirected):
    layers = defaultdict(list)
    original_index = {name: idx for idx, name in enumerate(names)}

    for name in names:
        layers[layer_map[name]].append(name)

    ordered_layers = {
        lvl: sorted(
            bucket,
            key=lambda name: (
                len(reverse[name]) == 0,
                -(len(graph[name]) + len(reverse[name])),
                original_index[name],
            ),
        )
        for lvl, bucket in layers.items()
    }

    for _ in range(4):
        order_index = _layer_order_index(ordered_layers)

        for lvl in sorted(ordered_layers)[1:]:
            ordered_layers[lvl].sort(
                key=lambda name: (
                    _barycenter(name, reverse[name], order_index),
                    -len(undirected[name]),
                    original_index[name],
                )
            )
            order_index = _layer_order_index(ordered_layers)

        for lvl in reversed(sorted(ordered_layers)[:-1]):
            ordered_layers[lvl].sort(
                key=lambda name: (
                    _barycenter(name, graph[name], order_index),
                    -len(undirected[name]),
                    original_index[name],
                )
            )

    return ordered_layers


def _layer_order_index(layers):
    return {
        name: idx
        for bucket in layers.values()
        for idx, name in enumerate(bucket)
    }


def _barycenter(name, neighbors, order_index):
    refs = [order_index[neighbor] for neighbor in neighbors if neighbor in order_index]
    if not refs:
        return order_index.get(name, 0)
    return sum(refs) / len(refs)


def _seed_positions(layers, width, height, node_radius):
    margin_x = max(56, int(node_radius * 3.2))
    margin_y = max(48, int(node_radius * 2.8))
    usable_w = max(120, width - 2 * margin_x)
    usable_h = max(120, height - 2 * margin_y)

    layer_ids = sorted(layers)
    layer_count = len(layer_ids)
    x_step = usable_w / max(1, layer_count - 1) if layer_count > 1 else 0
    min_gap = max(node_radius * 2.8, 54)

    positions = {}
    anchors = {}

    for idx, lvl in enumerate(layer_ids):
        bucket = layers[lvl]
        base_x = width / 2 if layer_count == 1 else margin_x + idx * x_step

        lane_count = max(1, math.ceil(len(bucket) * min_gap / usable_h))
        lane_count = min(lane_count, max(1, len(bucket)))
        lane_spacing = min(max(node_radius * 3.0, 48), max(60, x_step * 0.35 if x_step else width * 0.25))

        for lane in range(lane_count):
            lane_nodes = bucket[lane::lane_count]
            if not lane_nodes:
                continue

            gap = usable_h / (len(lane_nodes) + 1)
            x = base_x + (lane - (lane_count - 1) / 2) * lane_spacing
            x = max(margin_x, min(width - margin_x, x))

            for row, name in enumerate(lane_nodes, start=1):
                y = margin_y + row * gap
                positions[name] = [x, y]
                anchors[name] = [x, y]

    return positions, anchors


def _seed_dense_grid(order, initial_states, width, height, node_radius):
    margin_x = max(60, int(node_radius * 3.4))
    margin_y = max(50, int(node_radius * 3.0))
    positions = {}
    anchors = {}

    initials = [name for name in order if name in set(initial_states)]
    rest = [name for name in order if name not in set(initial_states)]

    left_x = margin_x
    if initials:
        gap_y = (height - 2 * margin_y) / (len(initials) + 1)
        for idx, name in enumerate(initials, start=1):
            y = margin_y + idx * gap_y
            positions[name] = [left_x, y]
            anchors[name] = [left_x, y]

    if not rest:
        return positions, anchors

    usable_w = max(160, width - 3 * margin_x)
    usable_h = max(160, height - 2 * margin_y)
    cols = max(3, math.ceil(math.sqrt(len(rest) * width / max(height, 1))))
    cols = min(cols, max(3, len(rest)))
    rows = math.ceil(len(rest) / cols)

    col_gap = usable_w / max(1, cols - 1) if cols > 1 else 0
    row_gap = usable_h / max(1, rows - 1) if rows > 1 else 0
    base_x = margin_x * 2.2 if initials else margin_x

    for idx, name in enumerate(rest):
        row = idx // cols
        col = idx % cols
        x = base_x + col * col_gap
        y = margin_y + row * row_gap
        positions[name] = [x, y]
        anchors[name] = [x, y]

    return positions, anchors


def _relax_positions(positions, anchors, layers, transitions, undirected, width, height, node_radius):
    names = list(positions.keys())
    n = len(names)
    if n <= 1:
        return positions

    margin = max(40, int(node_radius * 2.4))
    min_sep = max(node_radius * 2.6, 48)
    repulsion_range = min_sep * 2.6
    cell_size = repulsion_range
    iterations = 36 if n <= 8 else 54 if n <= 24 else 72 if n <= 60 else 88
    temperature = max(width, height) * 0.045

    unique_edges = []
    seen_edges = set()
    for transition in transitions:
        source, target = _edge_endpoints(transition)
        if source not in positions or target not in positions:
            continue
        edge = (source, target)
        if edge not in seen_edges and source != target:
            seen_edges.add(edge)
            unique_edges.append(edge)

    for _ in range(iterations):
        disp = {name: [0.0, 0.0] for name in names}
        grid = defaultdict(list)

        for name in names:
            x, y = positions[name]
            cell = (int(x // cell_size), int(y // cell_size))
            grid[cell].append(name)

        for name in names:
            x, y = positions[name]
            cx, cy = int(x // cell_size), int(y // cell_size)
            for gx in range(cx - 1, cx + 2):
                for gy in range(cy - 1, cy + 2):
                    for other in grid.get((gx, gy), []):
                        if other <= name:
                            continue
                        ox, oy = positions[other]
                        dx = x - ox
                        dy = y - oy
                        dist = math.hypot(dx, dy)
                        if dist == 0:
                            dx = 0.01
                            dy = 0.01
                            dist = 0.014
                        if dist > repulsion_range:
                            continue

                        force = ((repulsion_range - dist) / repulsion_range) ** 2 * min_sep * 0.85
                        fx = dx / dist * force
                        fy = dy / dist * force
                        disp[name][0] += fx
                        disp[name][1] += fy
                        disp[other][0] -= fx
                        disp[other][1] -= fy

        for source, target in unique_edges:
            sx, sy = positions[source]
            tx, ty = positions[target]
            dx = tx - sx
            dy = ty - sy
            dist = max(math.hypot(dx, dy), 0.01)

            anchor_dx = abs(anchors[target][0] - anchors[source][0])
            ideal = max(min_sep * 1.35, anchor_dx * 0.9)
            force = (dist - ideal) * 0.07
            fx = dx / dist * force
            fy = dy / dist * force

            disp[source][0] += fx
            disp[source][1] += fy
            disp[target][0] -= fx
            disp[target][1] -= fy

        for name in names:
            x, y = positions[name]
            ax, ay = anchors[name]
            disp[name][0] += (ax - x) * 0.22
            disp[name][1] += (ay - y) * 0.08

            neighbors = undirected[name]
            if neighbors:
                avg_y = sum(positions[neighbor][1] for neighbor in neighbors if neighbor in positions) / len(neighbors)
                disp[name][1] += (avg_y - y) * 0.03

        for name in names:
            dx, dy = disp[name]
            length = math.hypot(dx, dy)
            if length > 0:
                scale = min(length, temperature) / length
                dx *= scale
                dy *= scale

            positions[name][0] = max(margin, min(width - margin, positions[name][0] + dx))
            positions[name][1] = max(margin, min(height - margin, positions[name][1] + dy))

        temperature = max(1.5, temperature * 0.94)

    return positions


def _spread_overlaps(positions, width, height, node_radius):
    names = list(positions.keys())
    if len(names) < 2:
        return positions

    margin = max(36, int(node_radius * 2.2))
    min_sep = max(node_radius * 2.4, 44)

    for _ in range(8):
        moved = False
        for idx, name in enumerate(names):
            for other in names[idx + 1:]:
                dx = positions[name][0] - positions[other][0]
                dy = positions[name][1] - positions[other][1]
                dist = math.hypot(dx, dy)
                if dist >= min_sep:
                    continue

                moved = True
                if dist == 0:
                    dx, dy, dist = 0.01, 0.01, 0.014

                push = (min_sep - dist) / 2
                px = dx / dist * push
                py = dy / dist * push

                positions[name][0] = max(margin, min(width - margin, positions[name][0] + px))
                positions[name][1] = max(margin, min(height - margin, positions[name][1] + py))
                positions[other][0] = max(margin, min(width - margin, positions[other][0] - px))
                positions[other][1] = max(margin, min(height - margin, positions[other][1] - py))

        if not moved:
            break

    return positions


def _fit_positions(positions, width, height, node_radius):
    names = list(positions.keys())
    if not names:
        return positions

    margin = max(42, int(node_radius * 2.6))
    min_x = min(positions[name][0] for name in names)
    max_x = max(positions[name][0] for name in names)
    min_y = min(positions[name][1] for name in names)
    max_y = max(positions[name][1] for name in names)

    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    usable_w = max(120, width - 2 * margin)
    usable_h = max(120, height - 2 * margin)
    scale = min(usable_w / span_x, usable_h / span_y, 1.0)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    for name in names:
        x, y = positions[name]
        x = (x - center_x) * scale + width / 2
        y = (y - center_y) * scale + height / 2
        positions[name] = [
            max(margin, min(width - margin, x)),
            max(margin, min(height - margin, y)),
        ]

    return positions
