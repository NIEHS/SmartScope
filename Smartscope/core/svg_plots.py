import drawsvg as draw
from drawsvg import elements as elementsModule
from math import floor, sqrt
from io import StringIO
from Smartscope.core.settings.worker import PLUGINS_FACTORY
import logging

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
    while final_lineLenght <= w*0.1:
        final_value += value
        final_lineLenght += lineLenght
    line = draw.Line(startpoint - final_lineLenght, h * 0.02, startpoint, h * 0.02, stroke='white', stroke_width=ft_sz / 2, id=f'line_{id_type}')
    text = draw.Text(f'{str(final_value)} {unit}', ft_sz, path=line, fill='white', text_anchor='middle', lineOffset=-0.5, id=f'text_{id_type}')
    scalebarGroup.append(line)
    scalebarGroup.append(text)
    return scalebarGroup


def add_legend(label_list, w, h, prefix):
    startpoint = h * 0.96
    ft_sz = h * 0.03
    step = h * 0.035
    legend = draw.Group(id='legend')
    box = draw.Rectangle(w * 0.01, startpoint - (step * (len(label_list) + 0.25)), w * 0.25, step * (len(label_list) + 1.25),
                         fill='gray', stroke='black', stroke_width=floor(ft_sz / 5), opacity=0.6)
    legend.append(box)
    t = draw.Text(f"Legend", ft_sz, x=w * 0.02, y=startpoint, paint_order='stroke',
                  stroke_width=floor(ft_sz / 5), stroke='black', fill="white")
    legend.append(t)
    for (color, label, prefix) in sorted(label_list, key=lambda x: x[1] if isinstance(x[1], (int, float)) else 9999):
        startpoint -= step
        t = draw.Text(f"{prefix} {label}", ft_sz, x=w * 0.02, y=startpoint, paint_order='stroke',
                      stroke_width=floor(ft_sz / 5), stroke='black', class_='legend', label=label, fill=color)
        legend.append(t)
    return legend


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
        return PLUGINS_FACTORY[method].get_label(label[0].label)
    if method == 'CTF Viewer':
        labels = obj.highmagmodel_set.values_list('ctffit', flat=True)
        if len(labels) == 0:
            return 'blue', 'N.D.', ''
        return PLUGINS_FACTORY[method].get_label(labels[0])


class myDrawging(draw.Drawing):
    def asSvg(self, outputFile=None):
        returnString = outputFile is None
        if returnString:
            outputFile = StringIO()
        imgWidth, imgHeight = self.calcRenderSize()
        if self.pixelScale != 1:
            startStr = '''<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
        width="{}" height="{}" viewBox="{} {} {} {}"'''.format(
                imgWidth, imgHeight, *self.viewBox)
        else:
            startStr = '''<?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
        viewBox="{} {} {} {}"'''.format(
                *self.viewBox)
        endStr = '</svg>'
        outputFile.write(startStr)
        elementsModule.writeXmlNodeArgs(self.svgArgs, outputFile)
        outputFile.write('>\n<defs>\n')
        # Write definition elements

        def idGen(base=''):
            idStr = self.idPrefix + base + str(self.idIndex)
            self.idIndex += 1
            return idStr
        prevSet = set((id(defn) for defn in self.otherDefs))

        def isDuplicate(obj):
            nonlocal prevSet
            dup = id(obj) in prevSet
            prevSet.add(id(obj))
            return dup
        for element in self.otherDefs:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, False)
                outputFile.write('\n')
            except AttributeError:
                pass
        allElements = self.allElements()
        for element in allElements:
            try:
                element.writeSvgDefs(idGen, isDuplicate, outputFile, False)
            except AttributeError:
                pass
        outputFile.write('</defs>\n')
        # Generate ids for normal elements
        prevDefSet = set(prevSet)
        for element in allElements:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, True)
            except AttributeError:
                pass
        prevSet = prevDefSet
        # Write normal elements
        for element in allElements:
            try:
                element.writeSvgElement(idGen, isDuplicate, outputFile, False)
                outputFile.write('\n')
            except AttributeError:
                pass
        outputFile.write(endStr)
        if returnString:
            return outputFile.getvalue()

def drawAtlas(atlas, targets, display_type, method) -> myDrawging:
    d = myDrawging(atlas.shape_y, atlas.shape_x, id='square-svg', displayInline=False)
    d.append(draw.Image(0, 0, d.width, d.height, path=atlas.png, embed= not atlas.is_aws))

    shapes = draw.Group(id='atlasShapes')
    text = draw.Group(id='atlasText')

    labels_list = []
    for i in targets:
        color, label, prefix = css_color(i, display_type, method)
        if color is not None:
            sz = floor(sqrt(i.area))
            finder = list(i.finders.all())[0]
            x = finder.x - sz // 2
            y = -(finder.y - sz // 2) + d.height - sz
            r = draw.Rectangle(x, y, sz, sz, id=i.pk, stroke_width=floor(d.width / 300), stroke=color, fill=color, fill_opacity=0, label=label,
                               class_=f'target', onclick="clickSquare(this)")

            if i.selected:
                ft_sz = floor(d.width / 35)
                t = draw.Text(str(i.number), ft_sz, x=x + sz, y=y + sz, id=f'{i.pk}_text', paint_order='stroke',
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


def drawSquare(square, targets, display_type, method) -> myDrawging:
    d = myDrawging(square.shape_y, square.shape_x, id='square-svg', displayInline=False)
    d.append(draw.Image(0, 0, d.width, d.height, path=square.png, embed= not square.is_aws))

    shapes = draw.Group(id='squareShapes')
    text = draw.Group(id='squareText')
    labels_list = []
    bis_groups = {}
    for i in targets:

        color, label, prefix = css_color(i, display_type, method)
        if color is not None:
            finder = list(i.finders.all())[0]
            x = finder.x
            y = -(finder.y) + d.height
            c = draw.Circle(x, y, i.radius, id=i.pk, stroke_width=floor(d.width / 250), stroke=color, fill=color, fill_opacity=0, label=label,
                            class_=f'target', number=i.number, onclick="clickHole(this)")

            if i.selected:
                ft_sz = floor(d.width / 3000 * 80)
                t = draw.Text(str(i.number), ft_sz, x=x + i.radius, y=y + i.radius, id=f'{i.pk}_text', paint_order='stroke',
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


def drawMediumMag(hole, targets, display_type, method, **kwargs) -> myDrawging:
    d = myDrawging(hole.shape_y, hole.shape_x, id='hole-svg', displayInline=False)
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
            y = -(finder.y) + d.height
            
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


def drawHighMag(highmag) -> myDrawging:
    d = myDrawging(highmag.shape_y, highmag.shape_x, id=f'{highmag.name}-svg', displayInline=False)
    d.append(draw.Image(0, 0, d.width, d.height, path=highmag.png, embed= not highmag.is_aws))
    d.append(add_scale_bar(highmag.pixel_size, d.width, d.height, id_type=highmag.name))
    return d