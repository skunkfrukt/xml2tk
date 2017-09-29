import xml.etree.ElementTree as ET

import tkinter as tk
import tkinter.ttk as ttk


class TkUI:
    @classmethod
    def from_file(cls, master, filename):
        return cls(master, ET.parse(filename).getroot())

    @classmethod
    def from_string(cls, master, xml_string):
        return cls(master, ET.fromstring(xml_string))

    def __init__(self, master, top_etree_node):
        self.master = master
        self.geometry = top_etree_node.attrib.get("geometry")
        if self.geometry not in ("grid", "pack"):
            raise Exception(
                "Toplevel element must have a geometry attribute (grid/pack).")
        self._widgets, self._packlist = _parse_widget_recursive(
            self.master, top_etree_node)

    def __getitem__(self, id_):
        if isinstance(id_, str):
            return self._widgets[id_]
        elif isinstance(id_, (list, tuple)):
            return [self._widgets[x] for x in id_]

    def build(self):
        if self.geometry == "grid":
            self._grid()
        elif self.geometry == "pack":
            self._pack()

    def _pack(self):
        for wpc in self._packlist:
            wpc.widget.pack(**wpc.pack_config)

    def _grid(self):
        for wpc in self._packlist:
            wpc.widget.grid(**wpc.grid_config)

    def map_scrollbars(self, target, x=None, y=None):
        if x is not None:
            self[target].config(xscrollcommand=self[x].set)
            self[x].config(command=self[target].xview)
        if y is not None:
            self[target].config(yscrollcommand=self[y].set)
            self[y].config(command=self[target].yview)


class WidgetGeometryConfig:
    GRID_OPTIONS = (
        "row", "column", "sticky", "rowspan", "columnspan", "padx", "pady")
    PACK_OPTIONS = ("side", "fill", "expand")

    @classmethod
    def default(cls, widget, node):
        geometry_config = {
            "side": node.attrib.get("side"),
            "fill": node.attrib.get("fill"),
            "expand": node.attrib.get("expand"),
            "row": node.attrib.get("row"),
            "column": node.attrib.get("column"),
            "sticky": node.attrib.get("sticky"),
            "rowspan": node.attrib.get("rowspan"),
            "columnspan": node.attrib.get("columnspan"),
            "padx": node.attrib.get("padx"),
            "pady": node.attrib.get("pady")}
        return WidgetGeometryConfig(widget, geometry_config)

    def __init__(self, widget, geometry_config):
        self.widget = widget
        self.geometry_config = geometry_config

    @property
    def grid_config(self):
        return {
            k: v for k, v in self.geometry_config.items()
            if k in self.GRID_OPTIONS}

    @property
    def pack_config(self):
        return {
            k: v for k, v in self.geometry_config.items()
            if k in self.PACK_OPTIONS}


class TextVar:
    """Custom StringVar analogue for use with Text widgets."""
    def __init__(self, widget):
        self.widget = widget

    def get(self):
        """Get the text content of the corresponding widget."""
        return self.widget.get("1.0", tk.END).strip()

    def set(self, value):
        """Set the text content of the corresponding widget."""
        self.widget.delete("1.0", tk.END)
        self.widget.insert(tk.END, value)
        self.widget.update()


def _parse_widget_recursive(master, node):
    tag = node.tag
    try:
        widget, packlist = TAGNAME_TO_FUNCTION_MAPPINGS[tag](master, node)
    except KeyError:
        raise KeyError(f"Unrecognized tag name: <{tag}>")

    id_dict = {}
    if "id" in node.attrib:
        id_dict[node.attrib["id"]] = widget

    for child in node:
        if child.tag in NON_WIDGET_TAGNAMES:
            continue
        child_id_dict, child_packlist = _parse_widget_recursive(
            widget, child)
        id_dict.update(child_id_dict)
        packlist.extend(child_packlist)

    return id_dict, packlist

def _get_common_options(node):
    return {k: v for k, v in node.attrib if k in COMMON_OPTIONS}

def _parse_button(master, node):
    widget = ttk.Button(
        master, text=node.attrib.get("text", ""),
        state=node.attrib.get("state"), width=node.attrib.get("width"),
        height=node.attrib.get("height"))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_canvas(master, node):
    widget = tk.Canvas(
        master, width=node.attrib.get("width"),
        height=node.attrib.get("height"))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_checkbutton(master, node):
    var = tk.IntVar()
    widget = ttk.Checkbutton(
        master, text=node.attrib.get("text", ""), variable=var)
    widget.var = var
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_combobox(master, node):
    var = tk.StringVar()
    values = [value.text for value in node.findall("value")]
    widget = ttk.Combobox(
        master, textvariable=var, width=node.attrib.get("width"),
        height=node.attrib.get("height"), values=values,
        state=node.attrib.get("state"))
    widget.var = var
    widget.adjust_width = lambda: widget.config(
        width=max([len(value) for value in widget["values"]]))
    if values:
        widget.current(0)
        if "width" not in node.attrib:
            widget.adjust_width()
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_entry(master, node):
    var = tk.StringVar()
    var.set(node.attrib.get("text", ""))
    widget = ttk.Entry(
        master, textvariable=var, width=node.attrib.get("width"),
        height=node.attrib.get("height"))
    widget.var = var
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_frame(master, node):
    widget = tk.Frame(
        master, width=node.attrib.get("width"),
        height=node.attrib.get("height"), relief=node.attrib.get("relief"))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_label(master, node):
    widget = ttk.Label(master, text=node.attrib.get("text", ""))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_labelframe(master, node):
    widget = ttk.LabelFrame(master, text=node.attrib.get("text", ""))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_listbox(master, node):
    widget = tk.Listbox(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_menu(master, node):
    widget = tk.Menu(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_menubutton(master, node):
    widget = ttk.Menubutton(master, text=node.attrib.get("text", ""))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_message(master, node):
    if "text" in node.attrib:
        raise Exception(
            "Text attribute found in Message element. "
            "Correct usage is <message>Krafs</message>.")
    widget = tk.Message(master, text=node.text)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_notebook(master, node):
    widget = ttk.Notebook(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_notebook_page(master, node):
    if not isinstance(master, ttk.Notebook):
        raise Exception("<page> must be inside a <notebook>.")
    widget = ttk.Frame(master)
    master.add(widget, text=node.attrib.get("text", ""))
    return widget, []

def _parse_optionmenu(master, node):
    var = tk.StringVar()
    values = [value.text for value in node.findall("value")]
    widget = tk.OptionMenu(master, var, *values)
    widget.var = var
    widget.adjust_width = lambda: widget.config(
        width=max([len(value) for value in widget["values"]]))
    if values:
        var.set(values[0])
        if "width" not in node.attrib:
            widget.adjust_width()
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_panedwindow(master, node):
    widget = ttk.PanedWindow(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_progressbar(master, node):
    widget = ttk.Progressbar(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_radiobutton(master, node):
    widget = ttk.Radiobutton(master, text=node.attrib.get("text"))
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_scale(master, node):
    widget = ttk.Scale(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_scrollbar(master, node):
    widget = ttk.Scrollbar(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_separator(master, node):
    widget = ttk.Separator(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_sizegrip(master, node):
    widget = ttk.Sizegrip(master)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_spinbox(master, node):
    var = tk.StringVar()
    values = [value.text for value in node.findall("value")] or None
    if values and (node.attrib.get("from") or node.attrib.get("to")):
        raise Exception("<spinbox> cannot specify both from/to and values.")
    widget = tk.Spinbox(
        master, from_=node.attrib.get("from"), to=node.attrib.get("to"),
        values=values)
    widget.var = var
    widget.adjust_width = lambda: widget.config(
        width=max([len(str(value)) for value in widget["values"]]))
    if values:
        var.set(values[0])
        if "width" not in node.attrib:
            widget.adjust_width()
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_text(master, node):
    if "text" in node.attrib:
        raise Exception(
            "Text attribute found in Text element. "
            "Correct usage is <text>Xyzzy</text>.")
    widget = tk.Text(
        master, width=node.attrib.get("width"),
        height=node.attrib.get("height"))
    widget.var = TextVar(widget)
    return widget, [WidgetGeometryConfig.default(widget, node)]

def _parse_toplevel(master, node):
    master.title(node.attrib.get("title"))
    return master, []  # No packlist; Toplevel widgets can't be packed.

def _parse_treeview(master, node):
    widget = ttk.Treeview(
        master, height=node.attrib.get("height"),
        selectmode=node.attrib.get("selectmode"),
        show=node.attrib.get("show"))
    return widget, [WidgetGeometryConfig.default(widget, node)]


TAGNAME_TO_FUNCTION_MAPPINGS = {
    "button": _parse_button,
    "canvas": _parse_canvas,
    "checkbutton": _parse_checkbutton,
    "combobox": _parse_combobox,
    "entry": _parse_entry,
    "frame": _parse_frame,
    "label": _parse_label,
    "labelframe": _parse_labelframe,
    "listbox": _parse_listbox,
    "menu": _parse_menu,
    "menubutton": _parse_menubutton,
    "message": _parse_message,
    "notebook": _parse_notebook,
    "optionmenu": _parse_optionmenu,
    "page": _parse_notebook_page,
    "panedwindow": _parse_panedwindow,
    "progressbar": _parse_progressbar,
    "radiobutton": _parse_radiobutton,
    "scale": _parse_scale,
    "scrollbar": _parse_scrollbar,
    "separator": _parse_separator,
    "sizegrip": _parse_sizegrip,
    "spinbox": _parse_spinbox,
    "text": _parse_text,
    "toplevel": _parse_toplevel,
    "treeview": _parse_treeview}

NON_WIDGET_TAGNAMES = ("value",)

COMMON_OPTIONS = ("width", "height", "state")
TK_COMMON_OPTIONS = ()
TTK_COMMON_OPTIONS = ("style",)


def __main():
    """Parse one or more XML files and render the corresponding UI."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="+")
    args = parser.parse_args()
    master = tk.Tk()
    TkUI.from_file(master, args.filenames[0]).build()
    for filename in args.filenames[1:]:
        TkUI.from_file(tk.Toplevel(master), filename).build()
    master.mainloop()


if __name__ == "__main__":
    __main()
