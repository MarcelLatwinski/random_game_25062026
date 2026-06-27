import heapq
import math
import pygame

from settings import GRAVITY, PLAYER_JUMP_STRENGTH

DEBUG_PATHS = False

JUMP_HEIGHT_PX = int(round((PLAYER_JUMP_STRENGTH ** 2) / (2 * GRAVITY)))
WALKER_MAX_JUMP_X = 360
WALKER_MAX_JUMP_Y = max(340, int(round(JUMP_HEIGHT_PX * 0.9)))
TANK_MAX_JUMP_X = 300
TANK_MAX_JUMP_Y = max(320, int(round(JUMP_HEIGHT_PX * 0.86)))

WALK_COST = 1.0
DROP_COST = 0.8
JUMP_COST = 1.3
NODE_MARGIN = 20
NODE_SNAP = 3
JUMP_LAUNCH_GAP = 54
DROP_DRIFT_X = 220

class PlatformNode:
    def __init__(self, platform_id, node_type, x, y):
        self.id = f"{platform_id}_{node_type}"
        self.platform_id = platform_id
        self.type = node_type
        self.x = x
        self.y = y

class PlatformEdge:
    def __init__(self, src_id, dest_id, action, cost, required=None):
        self.src_id = src_id
        self.dest_id = dest_id
        self.action = action
        self.cost = cost
        self.required = required

class PlatformGraph:
    def __init__(self, platforms):
        self.nodes = {}
        self.edges = {}
        self.nodes_by_platform = {}
        self.build(platforms)

    def build(self, platforms):
        self.nodes = {}
        self.edges = {}
        self.nodes_by_platform = {}

        for platform in platforms:
            self._add_base_nodes(platform)

        self._add_navigation_nodes(platforms)

        for platform in platforms:
            self._connect_platform_walk_edges(platform)

        for platform in platforms:
            self._add_drop_edges(platform, platforms)

        for platform in platforms:
            self._add_jump_edges(platform, platforms)

    def _add_base_nodes(self, platform):
        self._add_node(platform.id, "left", platform.rect.left + NODE_MARGIN, platform.rect.top)
        self._add_node(platform.id, "center", platform.rect.centerx, platform.rect.top)
        self._add_node(platform.id, "right", platform.rect.right - NODE_MARGIN, platform.rect.top)

    def _add_navigation_nodes(self, platforms):
        for platform in platforms:
            for node_id in self._edge_node_ids(platform):
                start = self.nodes[node_id]
                drop_target = self._drop_target(start, platforms)
                if drop_target:
                    lower_platform, dest_x = drop_target
                    self._ensure_node_at(lower_platform, dest_x, "drop_land")

        for platform in platforms:
            for dest_platform in platforms:
                if dest_platform.id == platform.id:
                    continue
                vertical = platform.rect.top - dest_platform.rect.top
                if vertical <= 0 or vertical > WALKER_MAX_JUMP_Y:
                    continue
                for launch_x, land_x in self._jump_points(platform, dest_platform):
                    self._ensure_node_at(platform, launch_x, f"launch_{dest_platform.id}")
                    self._ensure_node_at(dest_platform, land_x, f"land_{platform.id}")

    def _add_node(self, platform_id, node_type, x, y):
        node = PlatformNode(platform_id, node_type, x, y)
        if node.id in self.nodes:
            return node.id
        self.nodes[node.id] = node
        self.edges[node.id] = []
        self.nodes_by_platform.setdefault(platform_id, []).append(node.id)
        return node.id

    def _add_edge(self, src_id, dest_id, action, cost, required=None):
        for edge in self.edges[src_id]:
            if edge.dest_id == dest_id and edge.action == action:
                return
        self.edges[src_id].append(PlatformEdge(src_id, dest_id, action, cost, required))

    def _ensure_node_at(self, platform, x, node_type):
        x = self._clamp_x(platform, x)
        for node_id in self.nodes_by_platform.get(platform.id, []):
            if abs(self.nodes[node_id].x - x) <= NODE_SNAP:
                return node_id
        return self._add_node(platform.id, f"{node_type}_{int(round(x))}", x, platform.rect.top)

    def _clamp_x(self, platform, x):
        return max(platform.rect.left + NODE_MARGIN, min(x, platform.rect.right - NODE_MARGIN))

    def _edge_node_ids(self, platform):
        return [f"{platform.id}_left", f"{platform.id}_right"]

    def _connect_platform_walk_edges(self, platform):
        node_ids = sorted(self.nodes_by_platform[platform.id], key=lambda node_id: self.nodes[node_id].x)
        for index in range(len(node_ids) - 1):
            left_id = node_ids[index]
            right_id = node_ids[index + 1]
            distance = self._distance(left_id, right_id)
            if distance <= 0:
                continue
            self._add_edge(left_id, right_id, "walk", distance * WALK_COST)
            self._add_edge(right_id, left_id, "walk", distance * WALK_COST)

    def _add_drop_edges(self, platform, platforms):
        for src_id in self._edge_node_ids(platform):
            drop_target = self._drop_target(self.nodes[src_id], platforms)
            if not drop_target:
                continue
            lower_platform, dest_x = drop_target
            dest_id = self._ensure_node_at(lower_platform, dest_x, "drop_land")
            self._add_edge(src_id, dest_id, "drop", self._distance(src_id, dest_id) * DROP_COST)

    def _drop_target(self, start, platforms):
        candidates = []
        for platform in platforms:
            if platform.id == start.platform_id:
                continue
            if platform.rect.top <= start.y + 8:
                continue
            if not (platform.rect.left - DROP_DRIFT_X <= start.x <= platform.rect.right + DROP_DRIFT_X):
                continue
            dest_x = self._clamp_x(platform, start.x)
            candidates.append((platform.rect.top, platform, dest_x))
        if not candidates:
            return None
        _, platform, dest_x = min(candidates, key=lambda candidate: candidate[0])
        return platform, dest_x

    def _add_jump_edges(self, platform, platforms):
        for dest_platform in platforms:
            if dest_platform.id == platform.id:
                continue
            vertical = platform.rect.top - dest_platform.rect.top
            if vertical <= 0 or vertical > WALKER_MAX_JUMP_Y:
                continue
            for launch_x, land_x in self._jump_points(platform, dest_platform):
                src_id = self._ensure_node_at(platform, launch_x, f"launch_{dest_platform.id}")
                dest_id = self._ensure_node_at(dest_platform, land_x, f"land_{platform.id}")
                horizontal = abs(self.nodes[dest_id].x - self.nodes[src_id].x)
                if horizontal <= WALKER_MAX_JUMP_X:
                    cost = self._distance(src_id, dest_id) * JUMP_COST
                    self._add_edge(src_id, dest_id, "jump", cost, required=(horizontal, vertical))

    def _jump_points(self, source, dest):
        points = []
        if dest.rect.left > source.rect.right:
            points.append((source.rect.right - NODE_MARGIN, dest.rect.left + NODE_MARGIN))
        elif dest.rect.right < source.rect.left:
            points.append((source.rect.left + NODE_MARGIN, dest.rect.right - NODE_MARGIN))
        else:
            left_launch = dest.rect.left - JUMP_LAUNCH_GAP
            right_launch = dest.rect.right + JUMP_LAUNCH_GAP
            source_left = source.rect.left + NODE_MARGIN
            source_right = source.rect.right - NODE_MARGIN
            if source_left <= left_launch <= source_right:
                points.append((left_launch, dest.rect.left + NODE_MARGIN))
            if source_left <= right_launch <= source_right:
                points.append((right_launch, dest.rect.right - NODE_MARGIN))
        return points

    def _distance(self, src_id, dest_id):
        src = self.nodes[src_id]
        dest = self.nodes[dest_id]
        return math.hypot(dest.x - src.x, dest.y - src.y)

    def get_nearest_node_on_platform(self, platform, x):
        if platform is None:
            return None
        node_ids = self.nodes_by_platform.get(platform.id, [])
        if not node_ids:
            return None
        return min(node_ids, key=lambda nid: abs(self.nodes[nid].x - x))

    def get_node(self, node_id):
        return self.nodes.get(node_id)

    def get_edges(self, src_id):
        return self.edges.get(src_id, [])

    def _jump_allowed(self, edge, agent_type):
        if edge.action != "jump" or edge.required is None:
            return True
        horizontal, vertical = edge.required
        if agent_type == "walker":
            return horizontal <= WALKER_MAX_JUMP_X and vertical <= WALKER_MAX_JUMP_Y
        return horizontal <= TANK_MAX_JUMP_X and vertical <= TANK_MAX_JUMP_Y

    def astar(self, start_id, goal_id, agent_type):
        if start_id is None or goal_id is None:
            return []
        open_set = []
        heapq.heappush(open_set, (self._heuristic(start_id, goal_id), start_id))
        came_from = {}
        g_score = {start_id: 0.0}

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal_id:
                return self._reconstruct_path(came_from, current)
            for edge in self.get_edges(current):
                if not self._jump_allowed(edge, agent_type):
                    continue
                tentative = g_score[current] + edge.cost
                if tentative < g_score.get(edge.dest_id, float("inf")):
                    came_from[edge.dest_id] = current
                    g_score[edge.dest_id] = tentative
                    priority = tentative + self._heuristic(edge.dest_id, goal_id)
                    heapq.heappush(open_set, (priority, edge.dest_id))
        return []

    def _reconstruct_path(self, came_from, current):
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return list(reversed(path))

    def _heuristic(self, node_id, goal_id):
        return self._distance(node_id, goal_id)

    def draw(self, surface, font, zombies, camera_x=0):
        if not DEBUG_PATHS:
            return
        colors = {
            "walk": (50, 220, 50),
            "drop": (220, 140, 30),
            "jump": (80, 150, 250),
        }
        for src_id, edges in self.edges.items():
            src = self.nodes[src_id]
            for edge in edges:
                dest = self.nodes[edge.dest_id]
                pygame.draw.line(
                    surface,
                    colors.get(edge.action, (255, 255, 255)),
                    (src.x - camera_x, src.y),
                    (dest.x - camera_x, dest.y),
                    2,
                )
        for node in self.nodes.values():
            pygame.draw.circle(surface, (255, 255, 255), (int(node.x - camera_x), int(node.y)), 5)
            text = font.render(node.type[0].upper(), True, (255, 255, 255))
            surface.blit(text, (node.x - camera_x - 6, node.y - 26))
        for platform_id, node_ids in self.nodes_by_platform.items():
            first = self.nodes.get(f"{platform_id}_center", self.nodes[node_ids[0]])
            text = font.render(str(platform_id), True, (255, 255, 0))
            surface.blit(text, (first.x - camera_x - 6, first.y - 50))
        for zombie in zombies:
            if not hasattr(zombie, "path") or not zombie.path:
                continue
            for idx, node_id in enumerate(zombie.path):
                node = self.nodes.get(node_id)
                if not node:
                    continue
                pygame.draw.circle(surface, (255, 80, 80), (int(node.x - camera_x), int(node.y)), 8, 2)
                if idx == zombie.current_path_index:
                    pygame.draw.circle(surface, (255, 255, 0), (int(node.x - camera_x), int(node.y)), 10, 2)
            if hasattr(zombie, "current_platform") and zombie.current_platform is not None:
                info = f"P{zombie.current_platform.id}"
                text = font.render(info, True, (255, 255, 0))
                surface.blit(text, (zombie.rect.x - camera_x, zombie.rect.y - 22))


def get_current_platform(entity, platforms, tolerance=8):
    if not getattr(entity, "on_ground", False):
        return None
    bottom = entity.rect.bottom
    centerx = entity.rect.centerx
    for platform in platforms:
        if bottom >= platform.rect.top - tolerance and bottom <= platform.rect.top + tolerance:
            if centerx >= platform.rect.left + 4 and centerx <= platform.rect.right - 4:
                return platform
    return None
