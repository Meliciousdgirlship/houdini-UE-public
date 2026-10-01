"""Self-contained tower and bridge construction functions used by V006.
"""
import math


def make_ring(y, half_x, half_z):
    return [
        make_point(position)
        for position in [
            (tower_x - half_x, y, tower_z - half_z),
            (tower_x + half_x, y, tower_z - half_z),
            (tower_x + half_x, y, tower_z + half_z),
            (tower_x - half_x, y, tower_z + half_z),
        ]
    ]

def connect_rings(lower, upper, color, label):
    for side in range(4):
        following = (side + 1) % 4

        add_face(
            [
                lower[side],
                upper[side],
                upper[following],
                lower[following],
            ],
            color,
            label
        )

def add_band(bottom, top, half_x, half_z, color, label):
    lower = make_ring(bottom, half_x, half_z)
    upper = make_ring(top, half_x, half_z)

    add_face(lower, color, label)
    connect_rings(lower, upper, color, label)
    add_face(list(reversed(upper)), color, label)

def make_timber_bridge(
    wall_min,
    wall_max,
    deck_y,
    center_z,
    width
):
    xmin = wall_min - WALL_EMBED
    xmax = wall_max + WALL_EMBED

    length = xmax - xmin
    clear_length = wall_max - wall_min
    center_x = (xmin + xmax) * 0.5

    # 横向铺设木板
    board_count = max(
        2,
        int(math.ceil(length / 0.24))
    )

    board_step = length / board_count
    board_gap = min(0.008, board_step * 0.04)

    for index in range(board_count):
        x = xmin + (index + 0.5) * board_step

        color = (
            WOOD_LIGHT
            if index % 3 != 0
            else (0.38, 0.245, 0.13)
        )

        make_box(
            (
                x,
                deck_y - DECK_THICKNESS * 0.5,
                center_z
            ),
            (
                board_step - board_gap,
                DECK_THICKNESS,
                width
            ),
            color,
            "bridge_deck"
        )

    # 桥底两条纵梁
    beam_width = 0.16
    beam_offset = width * 0.5 - beam_width * 0.5 - 0.04

    for sign in (-1, 1):
        make_box(
            (
                center_x,
                deck_y - DECK_THICKNESS - BEAM_HEIGHT * 0.5,
                center_z + sign * beam_offset
            ),
            (
                length,
                BEAM_HEIGHT,
                beam_width
            ),
            WOOD_DARK,
            "bridge_beam"
        )

    # 两侧栏杆
    post_width = 0.12
    rail_thickness = 0.10
    rail_offset = width * 0.5 - post_width * 0.5

    post_start = wall_min + post_width * 0.5
    post_end = wall_max - post_width * 0.5
    rail_span = post_end - post_start

    bay_count = max(
        1,
        int(math.ceil(rail_span / 0.85))
    )

    for sign in (-1, 1):
        z = center_z + sign * rail_offset

        # 主立柱
        for index in range(bay_count + 1):
            x = post_start + rail_span * index / bay_count

            make_box(
                (
                    x,
                    deck_y + RAIL_HEIGHT * 0.5,
                    z
                ),
                (
                    post_width,
                    RAIL_HEIGHT,
                    post_width
                ),
                WOOD,
                "bridge_post"
            )

        # 顶部扶手
        make_box(
            (
                center_x,
                deck_y + RAIL_HEIGHT - rail_thickness * 0.5,
                z
            ),
            (
                clear_length,
                rail_thickness,
                0.14
            ),
            WOOD_LIGHT,
            "bridge_handrail"
        )

        # 下横杆
        lower_rail_y = deck_y + 0.22

        make_box(
            (
                center_x,
                lower_rail_y,
                z
            ),
            (
                clear_length,
                0.08,
                0.09
            ),
            WOOD,
            "bridge_lower_rail"
        )

        # 栏杆细竖杆
        spindle_bottom = lower_rail_y + 0.04
        spindle_top = deck_y + RAIL_HEIGHT - rail_thickness

        for bay in range(bay_count):
            bay_start = post_start + rail_span * bay / bay_count
            bay_end = post_start + rail_span * (bay + 1) / bay_count

            for fraction in (1.0 / 3.0, 2.0 / 3.0):
                x = bay_start + (bay_end - bay_start) * fraction

                make_box(
                    (
                        x,
                        (spindle_bottom + spindle_top) * 0.5,
                        z
                    ),
                    (
                        0.055,
                        spindle_top - spindle_bottom,
                        0.055
                    ),
                    WOOD,
                    "bridge_spindle"
                )

def make_arch_support(
    wall_min,
    wall_max,
    deck_y,
    center_z,
    width
):
    center_x = (wall_min + wall_max) * 0.5
    clear_length = wall_max - wall_min

    # 石结构顶面接住木纵梁
    support_top = (
        deck_y
        - DECK_THICKNESS
        - BEAM_HEIGHT
    )

    pier_width = min(
        PIER_WIDTH,
        clear_length * 0.18
    )

    opening_left = wall_min + pier_width
    opening_right = wall_max - pier_width
    radius_x = (opening_right - opening_left) * 0.5

    arch_thickness = min(
        ARCH_THICKNESS,
        pier_width
    )

    # 接近半圆的弧形；限制拱高以留出落地支撑。
    arch_rise = min(
        radius_x * 0.90,
        support_top * 0.32
    )

    spring_y = (
        support_top
        - arch_thickness
        - arch_rise
    )

    if radius_x <= 0.10 or spring_y <= 0.15:
        raise hou.NodeError(
            "桥下空间不足以生成拱洞，请增加层高或桥间距。"
        )

    # 承重结构略收进桥面
    support_depth = max(0.40, width - 0.20)
    zmin = center_z - support_depth * 0.5
    zmax = center_z + support_depth * 0.5

    # 两端落地支撑，一直延伸至木梁底部。
    pier_ranges = [
        (wall_min - WALL_EMBED, opening_left),
        (opening_right, wall_max + WALL_EMBED),
    ]

    for index, (xmin, xmax) in enumerate(pier_ranges):
        pier_center_x = (xmin + xmax) * 0.5
        pier_size_x = xmax - xmin

        make_box(
            (
                pier_center_x,
                support_top * 0.5,
                center_z
            ),
            (
                pier_size_x,
                support_top,
                support_depth
            ),
            STONE,
            "bridge_pier"
        )

        # 柱脚
        base_height = min(0.22, spring_y * 0.25)

        make_box(
            (
                pier_center_x,
                base_height * 0.5,
                center_z
            ),
            (
                pier_size_x + 0.10,
                base_height,
                support_depth + 0.12
            ),
            STONE_DARK,
            "bridge_pier_base"
        )

        # 起拱处柱头
        make_box(
            (
                pier_center_x,
                spring_y - 0.06,
                center_z
            ),
            (
                pier_size_x + 0.06,
                0.12,
                support_depth + 0.08
            ),
            STONE_LIGHT,
            "bridge_pier_cap"
        )

    # 分块生成拱券。
    # 内弧形成通道顶部，外弧以上由石墙填充承托桥面。
    for index in range(ARCH_SEGMENTS):
        angle_a = math.pi * index / ARCH_SEGMENTS
        angle_b = math.pi * (index + 1) / ARCH_SEGMENTS

        inner_a = (
            center_x + radius_x * math.cos(angle_a),
            spring_y + arch_rise * math.sin(angle_a)
        )

        inner_b = (
            center_x + radius_x * math.cos(angle_b),
            spring_y + arch_rise * math.sin(angle_b)
        )

        outer_a = (
            center_x
            + (radius_x + arch_thickness) * math.cos(angle_a),
            spring_y
            + (arch_rise + arch_thickness) * math.sin(angle_a)
        )

        outer_b = (
            center_x
            + (radius_x + arch_thickness) * math.cos(angle_b),
            spring_y
            + (arch_rise + arch_thickness) * math.sin(angle_b)
        )

        shade = (index % 3 - 1) * 0.025

        arch_color = tuple(
            value + shade
            for value in STONE_LIGHT
        )

        # 拱券前后稍微凸出，突出石砌拱边。
        make_prism(
            [
                inner_a,
                inner_b,
                outer_b,
                outer_a,
            ],
            zmin - 0.035,
            zmax + 0.035,
            arch_color,
            "bridge_arch"
        )

        # 拱上填充：下沿沿外弧，上沿托住木梁。
        # 顶点与拱顶重合时去掉重复点。
        fill_profile = [
            outer_a,
            outer_b,
            (outer_b[0], support_top),
            (outer_a[0], support_top),
        ]

        cleaned = []

        for position in fill_profile:
            if (
                not cleaned
                or abs(position[0] - cleaned[-1][0])
                + abs(position[1] - cleaned[-1][1]) > 0.000001
            ):
                cleaned.append(position)

        if (
            len(cleaned) > 1
            and abs(cleaned[0][0] - cleaned[-1][0])
            + abs(cleaned[0][1] - cleaned[-1][1]) < 0.000001
        ):
            cleaned.pop()

        make_prism(
            cleaned,
            zmin,
            zmax,
            STONE,
            "bridge_spandrel"
        )
