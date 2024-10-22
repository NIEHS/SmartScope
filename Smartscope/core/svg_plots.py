import drawsvg as draw
from math import floor, sqrt
from Smartscope.core.settings.worker import PLUGINS_FACTORY
import logging
from scipy.spatial import Delaunay
import numpy as np

logger = logging.getLogger(__name__)


def add_scale_bar(pixelsize, w, h, id_type='atlas'):
    ft_sz = floor(w / 40)
    scalebarGroup = draw.Group(id='scaleBar')
    startpoint = w * 0.98
    unit = '\u03BCm'
    if pixelsize > 500:
        value = 100
        lineLenght = 1_000_000 / pixelsize
    elif pixelsize > 100:
        value = 10
        lineLenght = 100_000 / pixelsize
    elif pixelsize > 3:
        value = 1
        ft_sz = floor(w / 20)
        lineLenght = 10_000 / pixelsize
    else:
        value = 100
        unit = 'nm'
        ft_sz = floor(w / 20)
        lineLenght = 1_000 / pixelsize
    final_value = value
    final_lineLenght = lineLenght
    while final_lineLenght <= w*0.15:
        final_value += value
        final_lineLenght += lineLenght
    line = draw.Line(startpoint - final_lineLenght, h * 0.98, startpoint, h * 0.98, stroke='white', stroke_width=ft_sz / 2, id=f'line_{id_type}')
    text = draw.Text(f'{str(final_value)} {unit}', ft_sz, path=line, fill='white', text_anchor='middle', line_offset=-0.5, id=f'text_{id_type}')
    scalebarGroup.append(line)
    scalebarGroup.append(text)
    return scalebarGroup


def add_legend(label_list, w, h, prefix):
    startpoint = h * 0.04
    ft_sz = h * 0.03
    step = h * 0.035
    legend = draw.Group(id='legend')
    box = draw.Rectangle(w * 0.01, startpoint - (step + 0.25), w * 0.25, step * (len(label_list) + 1.25),
                         fill='gray', stroke='black', stroke_width=floor(ft_sz / 5), opacity=0.6)
    legend.append(box)
    t = draw.Text(f"Legend", ft_sz, x=w * 0.02, y=startpoint, paint_order='stroke',
                  stroke_width=floor(ft_sz / 5), stroke='black', fill="white")
    legend.append(t)
    for (color, label, prefix) in sorted(label_list, key=lambda x: x[1] if isinstance(x[1], (int, float)) else 9999):
        startpoint += step
        t = draw.Text(f"{prefix} {label}", ft_sz, x=w * 0.02, y=startpoint, paint_order='stroke',
                      stroke_width=floor(ft_sz / 5), stroke='black', class_='legend', label=label, fill=color)
        legend.append(t)
    return legend

def alpha_shape(points, alpha, only_outer=True):
    """
    Compute the alpha shape (concave hull) of a set of points.
    :param points: np.array of shape (n,2) points.
    :param alpha: alpha value.
    :param only_outer: boolean value to specify if we keep only the outer border
    or also inner edges.
    :return: set of (i,j) pairs representing edges of the alpha-shape. (i,j) are
    the indices in the points array.
    """
    assert points.shape[0] > 3, "Need at least four points"
    def add_edge(edges, i, j):
        """
        Add an edge between the i-th and j-th points,
        if not in the list already
        """
        if (i, j) in edges or (j, i) in edges:
            # already added
            assert (j, i) in edges, "Can't go twice over same directed edge right?"
            if only_outer:
                # if both neighboring triangles are in shape, it's not a boundary edge
                edges.remove((j, i))
            return
        edges.add((i, j))
    tri = Delaunay(points)
    edges = set()
    # Loop over triangles:
    # ia, ib, ic = indices of corner points of the triangle
    for ia, ib, ic in tri.vertices:
        pa = points[ia]
        pb = points[ib]
        pc = points[ic]
        # Computing radius of triangle circumcircle
        # www.mathalino.com/reviewer/derivation-of-formulas/derivation-of-formula-for-radius-of-circumcircle
        a = np.sqrt((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2)
        b = np.sqrt((pb[0] - pc[0]) ** 2 + (pb[1] - pc[1]) ** 2)
        c = np.sqrt((pc[0] - pa[0]) ** 2 + (pc[1] - pa[1]) ** 2)
        s = (a + b + c) / 2.0
        area = np.sqrt(s * (s - a) * (s - b) * (s - c))
        circum_r = a * b * c / (4.0 * area)
        if circum_r < alpha:
            add_edge(edges, ia, ib)
            add_edge(edges, ib, ic)
            add_edge(edges, ic, ia)
    return edges

def order_edges_indexes(edges):
    edge = edges.pop(0)
    ordered = [edge[0]]
    while edges:
        for i, pair in enumerate(edges):
            if pair[0] == edge[1]:
                edge = edges.pop(i)
                ordered.append(edge[0])
                break
    return ordered

def css_color(obj, display_type, method):

    if method is None:
        return 'blue', 'target', ''

    # Must use list comprehension instead of a filter query to use the prefetched data
    # Reduces the amount of queries subsitancially.
    if display_type != 'metadata':
        labels = list(getattr(obj, display_type).all())
        label = [i for i in labels if i.method_name == method]
        if len(label) == 0:
            return 'blue', 'target', ''
        return PLUGINS_FACTORY.get_plugin(method).get_label(label[0].label)
    if method == 'CTF viewer':
        labels = obj.highmagmodel_set.values_list('ctffit', flat=True)
        if len(labels) == 0:
            return 'blue', 'N.D.', ''
        return PLUGINS_FACTORY.get_plugin(method).get_label(labels[0])

def drawAtlas(atlas, targets, display_type, method) -> draw.Drawing:
    d = draw.Drawing(atlas.shape_y, atlas.shape_x, id='atlas-svg', displayInline=False, style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=atlas.png, embed= not atlas.is_aws))

    shapes = draw.Group(id='atlasShapes')
    text = draw.Group(id='atlasText')

    labels_list = []
    for i in targets:
        color, label, prefix = css_color(i, display_type, method)

        if color is not None:
            sz = floor(sqrt(i.area))
            finder = list(i.finders.all())[0]
            if not finder.is_position_within_stage_limits():
                color = '#505050'
                label = 'Out of range'
            x = finder.x - sz // 2
            y = (finder.y - sz // 2)
            r = draw.Rectangle(x, y, sz, sz, id=i.pk, stroke_width=floor(d.width / 300), stroke=color, fill=color, fill_opacity=0, label=label,
                               class_=f'target', status=i.status, onclick="clickSquare(this)")

            if i.selected:
                ft_sz = floor(d.width / 35)
                t = draw.Text(str(i.number), ft_sz, x=x + sz, y=y, id=f'{i.pk}_text', paint_order='stroke',
                              stroke_width=floor(ft_sz / 5), stroke=color, fill='white', class_=f'svgtext {i.status}')
                text.append(t)
                r.args['class'] += f" {i.status}"
                if i.status == 'completed':
                    if i.has_active:
                        r.args['class'] += ' has_active'
                    elif i.has_queued:
                        r.args['class'] += ' has_queued'
                    elif i.has_completed:
                        r.args['class'] += ' has_completed'
            labels_list.append((color, label, prefix))
            shapes.append(r)
    d.append(shapes)
    d.append(text)
    d.append(add_scale_bar(atlas.pixel_size, d.width, d.height))
    d.append(add_legend(set(labels_list), d.width, d.height, atlas.pixel_size))
    return d

def drawAtlasNew(atlas, selector_sorter) -> draw.Drawing:
    d = draw.Drawing(atlas.shape_y, atlas.shape_x, id=f'{atlas.prefix_lower}-svg', displayInline=False, style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=atlas.png, embed= not atlas.is_aws))

    shapes = draw.Group(id=f'{atlas.prefix_lower}Shapes')
    text = draw.Group(id=f'{atlas.prefix_lower}Text')

    labels_list = []
    for i, (color, label, prefix) in zip(atlas.targets, selector_sorter.labels):
        if color is not None:
            sz = floor(sqrt(i.area))
            finder = list(i.finders.all())[0]
            if not finder.is_position_within_stage_limits():
                color = '#505050'
                label = 'Out of range'
            x = finder.x - sz // 2
            y = (finder.y - sz // 2)
            r = draw.Rectangle(x, y, sz, sz, id=i.pk, stroke_width=floor(d.width / 300), stroke=color, fill=color, fill_opacity=0, label=label,
                               class_=f'target', status=i.status, onclick=f"click{i.prefix}(this)")

            if i.selected:
                ft_sz = floor(d.width / 35)
                t = draw.Text(str(i.number), ft_sz, x=x + sz, y=y, id=f'{i.pk}_text', paint_order='stroke',
                              stroke_width=floor(ft_sz / 5), stroke=color, fill='white', class_=f'svgtext {i.status}')
                text.append(t)
                r.args['class'] += f" {i.status}"
                # if i.status == 'completed':
                #     if i.has_active:
                #         r.args['class'] += ' has_active'
                #     elif i.has_queued:
                #         r.args['class'] += ' has_queued'
                #     elif i.has_completed:
                #         r.args['class'] += ' has_completed'
            labels_list.append((color, label, prefix))
            shapes.append(r)
    d.append(shapes)
    d.append(text)
    d.append(add_scale_bar(atlas.pixel_size, d.width, d.height))
    d.append(add_legend(set(labels_list), d.width, d.height, atlas.pixel_size))
    return d

def drawSquare(square, targets, display_type, method) -> draw.Drawing:
    if len(targets) > 700:
        return drawSquareGroups(square, targets, display_type, method)
    d = draw.Drawing(square.shape_y, square.shape_x, id='square-svg', displayInline=False,  style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=square.png, embed= not square.is_aws))

    shapes = draw.Group(id='squareShapes')
    text = draw.Group(id='squareText')

    labels_list = []
    bis_groups = {}
    for i in targets:

        color, label, prefix = css_color(i, display_type, method)
        # logger.debug(f'{i.number} -> {color}')
        if color is not None:
            finder = list(i.finders.all())[0]
            if not finder.is_position_within_stage_limits():
                color = '#505050'
                label = 'Out of range'
            x = finder.x
            y = finder.y
            c = draw.Circle(x, y, i.radius, id=i.pk, stroke_width=floor(d.width / 250), stroke=color, fill=color, fill_opacity=0, label=label,
                            class_=f'target',status=i.status, number=i.number, onclick="clickHole(this)")

            if i.selected:
                ft_sz = floor(d.width / 3000 * 80)
                t = draw.Text(str(i.number), ft_sz, x=x + i.radius, y=y - i.radius, id=f'{i.pk}_text', paint_order='stroke',
                              stroke_width=floor(ft_sz / 5), stroke=color, fill='white', class_=f'svgtext {i.status}')  # + qualityClass
                text.append(t)
            if i.status is not None:
                c.args['class'] += f" {i.status}"
                c.args['fill-opacity'] = 0.6 if color != 'blue' else 0
            if i.bis_type is not None:
                c.args['class'] += f" {i.bis_type}"
                if i.bis_type == 'center':
                    c.args['stroke-width'] = floor(d.width / 200)
            if i.bis_group in bis_groups.keys():
                bis_groups[i.bis_group].append(c)
            else:
                bis_groups[i.bis_group] = [c]
            labels_list.append((color, label, prefix))
    for bis_group, item in bis_groups.items():
        g = draw.Group(id=bis_group)
        for i in item:
            g.append(i)
        shapes.append(g)
    d.append(shapes)
    d.append(text)
    d.append(add_scale_bar(square.pixel_size, d.width, d.height, id_type='square'))
    d.append(add_legend(set(labels_list), d.width, d.height, square.pixel_size))
    return d

def drawSquareGroups(square, targets, display_type, method) -> draw.Drawing:
    d = draw.Drawing(square.shape_y, square.shape_x, id='square-svg', displayInline=False,  style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=square.png, embed= not square.is_aws))

    shapes = draw.Group(id='squareShapes')
    text = draw.Group(id='squareText')

    bis_groups = set([i.bis_group for i in targets])
    labels_list = []
    for bis_group in bis_groups:
        points = np.array(list(map(lambda x: (x.finders.all()[0].x, x.finders.all()[0].y), filter(lambda x: x.bis_group == bis_group, targets))))
        if len(points) < 3 or bis_group is None:
            continue
        edges = list(alpha_shape(points, 100))
        edges = order_edges_indexes(edges)
        center = list(filter(lambda x: x.bis_type == 'center', filter(lambda x: x.bis_group == bis_group, targets)))[0]
        finder = list(center.finders.all())[0]
        x = finder.x
        y = finder.y
        color, label, prefix = css_color(center, display_type, method)
        p = draw.Path(id=center.pk, stroke_width=floor(d.width / 250), stroke=color, fill=color, fill_opacity=0, label=label,
                            class_=f'target',status=center.status, number=center.number, onclick="clickHole(this)")  # Add an arrow to the end of a path
        logger.debug(f'Group {bis_group} has {len(points)} points and {len(edges)} edges. {edges}')
        edge = edges.pop(0)
        p.M(*points[edge])
        while edges:
            edge = edges.pop(0)
            p.L(*points[edge]) 
        p.Z()

        if center.selected:
            ft_sz = floor(d.width / 3000 * 80)
            t = draw.Text(str(center.number), ft_sz, x=x, y=y, id=f'{center.pk}_text', paint_order='stroke',
                            stroke_width=floor(ft_sz / 5), stroke=color, fill='white', class_=f'svgtext {center.status}')  # + qualityClass
            text.append(t)
        if center.status is not None:
            p.args['class'] += f" {center.status}"
            p.args['fill-opacity'] = 0.6 if color != 'blue' else 0
        if center.bis_type is not None:
            p.args['class'] += f" {center.bis_type}"

        labels_list.append((color, label, prefix))
        shapes.append(p)
    d.append(shapes)
    d.append(text)
    d.append(add_scale_bar(square.pixel_size, d.width, d.height, id_type='square'))
    d.append(add_legend(set(labels_list), d.width, d.height, square.pixel_size))
    return d
      # Chain multiple path commands    


def drawMediumMag(hole, targets, display_type, method, **kwargs) -> draw.Drawing:
    d = draw.Drawing(hole.shape_y, hole.shape_x, id='hole-svg', displayInline=False,  style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=hole.png, embed= not hole.is_aws))

    shapes = draw.Group(id='holeShapes')
    text = draw.Group(id='holeText')
    labels_list = []
    radius = kwargs.pop('radius', 0.05) / (hole.pixel_size / 10_000) 
    for i in targets:

        color, label, prefix = css_color(i, display_type, method)
        if color is not None:
            finders = list(i.finders.all())
            if len(finders) == 0:
                break
            finder = list(i.finders.all())[0]
            x = finder.x
            y = finder.y
            
            c = draw.Circle(x, y, radius, id=i.pk, stroke_width=floor(d.width / 100), stroke=color, fill=color, fill_opacity=0, label=label,
                            class_=f'target', number=i.number)
            if i.status is not None:
                c.args['class'] += f" {i.status}"
                c.args['fill-opacity'] = 0.6 if color != 'blue' else 0
            labels_list.append((color, label, prefix))
            shapes.append(c)
    d.append(shapes)
    d.append(text)
    d.append(add_scale_bar(hole.pixel_size, d.width, d.height, id_type='hole'))
    d.append(add_legend(set(labels_list), d.width, d.height, hole.pixel_size))
    return d

def drawHighMag(highmag) -> draw.Drawing:
    d = draw.Drawing(highmag.shape_y, highmag.shape_x, id=f'{highmag.name}-svg', displayInline=False, style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=highmag.png, embed= not highmag.is_aws))
    d.append(add_scale_bar(highmag.pixel_size, d.width, d.height, id_type=highmag.name))
    return d


def drawSelector(obj, selector_sorter) -> draw.Drawing:
    d = draw.Drawing(obj.shape_y, obj.shape_x, id='selector-svg', displayInline=False, style_='height: 100%; width: 100%')
    d.append(draw.Image(0, 0, d.width, d.height, path=obj.png, embed= not obj.is_aws))

    shapes = draw.Group(id='selectorShapes')

    for index, i in enumerate(obj.targets):
        sz = floor(sqrt(i.area))
        finder = list(i.finders.all())[0]
        x = finder.x - sz // 2
        y = (finder.y - sz // 2)
        color = 'lightgreen' if selector_sorter.classes[index] != 0 else 'red'
        r = draw.Rectangle(x, y, sz, sz, id=i.pk, stroke_width=floor(d.width / 300), stroke=color, fill=color, fill_opacity=0, class_='selectorTarget',value_=selector_sorter.values[index],)
        shapes.append(r)
    d.append(shapes)
    return d

def drawBase(obj, padding_fraction=0.25) -> draw.Drawing:
    padded_img_size = [obj.shape_x * (1 + padding_fraction), obj.shape_y * (1 + padding_fraction)]
    d = draw.Drawing(*padded_img_size, id=f'{obj.pk}-svg', displayInline=False, style_='height: 100%; width: 100%')
    d.append(draw.Rectangle(0, 0, *padded_img_size, stroke_width=floor(d.width / 100), stroke='black', fill='black', fill_opacity=0))
    d.append(draw.Image((padded_img_size[0]-obj.shape_x)//2, (padded_img_size[1]-obj.shape_y)//2, obj.shape_x, obj.shape_y, path=obj.png, embed= not obj.is_aws))
    return d