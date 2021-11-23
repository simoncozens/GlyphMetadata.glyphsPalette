# encoding: utf-8

import objc
from GlyphsApp import *
import GlyphsApp
from GlyphsApp.plugins import *
import vanilla
from collections import OrderedDict
from AppKit import NSView, NSForegroundColorAttributeName, NSColor, NSAttributedString

OUR_KEY = "uk.co.corvelsoftware.GlyphMetadata"

# plist_schema = [
#     [
#         "Status",
#         {"type": "Dropdown", "options": ["Draft", "Test", "In Review", "Final"]},
#     ],
#     ["Consultant checked", {"type": "Checkbox"}],
#     ["Consultant feedback", {"type": "Textbox"}],
#     ["Feedback integrated", {"type": "Checkbox"}],
#     ["Conjunct form", {"type": "Glyphbox"}],
#     ["Width", {"type": "Dropdown", "options": ["Other", "Single Bowl", "Double Bowl"]}],
# ]


def grey(s):
    fontAttributes = {NSForegroundColorAttributeName: NSColor.placeholderTextColor()}
    return NSAttributedString.alloc().initWithString_attributes_(s, fontAttributes)


def system_image_button(image_name, tooltip, callback):
    image = NSImage.imageNamed_(image_name)
    widget = vanilla.ImageButton("auto", imageObject=image, callback=callback)
    widget.getNSButton().setBordered_(False)
    widget.getNSButton().setToolTip_(tooltip)
    return widget


# Just using this for testing to stop the Vanilla crash issue. :-/
def remove_callbacks(obj):
    if hasattr(obj, "_target"):
        obj._target = vanilla.vanillaBase.VanillaCallbackWrapper(None)
        obj._target.callback = None
        obj._nsObject.setTarget_(obj._target)
    if hasattr(obj, "subviews"):
        for obj in obj.subviews():
            print("Removing callback on %s" % obj)
            remove_callbacks(obj)


# Different kinds of metadata widget you can use


class Widget:
    def refresh(self, other):
        pass

    def class_suffix(self, value):
        return None

    def class_suffixes(self):
        return []

    def associated_button(self, field_name, other):
        return vanilla.TextBox("auto", "")

    def serialize(self):
        return {"type": self.__class__.__name__}


class Dropdown(Widget):
    default_value = 0

    def __init__(self, options=[]):
        self.options = options

    def make_control(self, other):
        return vanilla.PopUpButton("auto", self.options, callback=other.callback)

    def associated_button(self, field_name, other):
        go_box = system_image_button(
            "NSFollowLinkFreestandingTemplate",
            "Open tab with all glyphs",
            other.openTab,
        )
        go_box.field = field_name
        return go_box

    def class_suffix(self, value):
        if value < len(self.options) and value >= 0:
            return self.options[value]

    def class_suffixes(self):
        return self.options

    def serialize(self):
        return {"type": "Dropdown", "options": self.options}


class Checkbox(Widget):
    default_value = False

    def make_control(self, other):
        return vanilla.CheckBox("auto", None, callback=other.callback)

    def associated_button(self, field_name, other):
        go_box = system_image_button(
            "NSFollowLinkFreestandingTemplate",
            "Open tab with all glyphs",
            other.openTab,
        )
        go_box.field = field_name
        return go_box

    def class_suffix(self, value):
        if value:
            return "yes"
        return "no"

    def class_suffixes(self):
        return ["yes", "no"]


class Glyphbox(Widget):
    default_value = ""

    def make_control(self, other):
        if other.font:
            glyphnames = [g.name for g in other.font.glyphs]
        else:
            glyphnames = []
        cb = vanilla.ComboBox("auto", glyphnames, callback=other.callback)
        self.cb = cb
        return cb

    def refresh(self, other):
        if other.font:
            value = self.cb.get()
            all_glyphs = [g.name for g in other.font.glyphs]
            self.cb.setItems(all_glyphs)
            self.cb.set(value)

    def associated_button(self, field_name, other):
        go_box = system_image_button(
            "NSFollowLinkFreestandingTemplate", "Go to this glyph", other.gotoGlyph,
        )
        go_box.field = field_name
        return go_box


class Textbox(Widget):
    default_value = ""

    def make_control(self, other):
        return vanilla.EditText("auto", callback=other.callback)


# The actual palette!


class GlyphMetadataPalette(PalettePlugin):
    @objc.python_method
    def settings(self):
        try:

            mainMenu = NSApplication.sharedApplication().mainMenu()
            self.generation = 0
            self.name = Glyphs.localize({"en": u"Glyph Metadata"})
            self.width = 150
            self.margin = 5
            self.font = None
            self.schema = {}
            self.selectedGlyph = None
            self.rebuilding_schema_editor_mutex = (
                False  # Work around double callback bug
            )
            if Glyphs.font:
                self.font = Glyphs.font
            plist_schema = Glyphs.font.userData.get("OUR_KEY", [])
            self.buildSchemaFromPlist(plist_schema)
            self.height = 52 + 20 * (1 + len(self.schema.keys()))
            self.paletteView = vanilla.Window(
                (self.width, self.height),
                minSize=(self.width, self.height - 10),
                maxSize=(self.width, self.height + 200),
            )
            self.paletteView.group = vanilla.Group((0, 0, 0, 0))
            self.paletteView.group.schema_editor = vanilla.Button(
                (0, -25, 100, 20), "Edit schema", callback=self.openSchemaEditor
            )
            self.buildInterfaceFromSchema()
            self.dialog = self.paletteView.group.getNSView()
        except Exception as e:
            self.logError(traceback.format_exc())

    @objc.python_method
    def buildSchemaFromPlist(self, plist):
        self.schema = OrderedDict()
        for key, value in plist:
            if value["type"] == "Checkbox":
                self.schema[key] = Checkbox()
            elif value["type"] == "Glyphbox":
                self.schema[key] = Glyphbox()
            elif value["type"] == "Dropdown":
                self.schema[key] = Dropdown(value.get("options"))
            else:
                self.schema[key] = Textbox()
        print(self.schema)

    def buildInterfaceFromSchema(self):
        if hasattr(self.paletteView.group, "list"):
            delattr(self.paletteView.group, "list")

        if not self.schema:
            return
        # print("Building interface")
        self.grid_data = []
        self.titles = {}
        self.fields = {}
        for title, role in self.schema.items():
            value_box = role.make_control(self)
            # role.refresh(self)
            go_box = role.associated_button(title, self)
            title_box = vanilla.TextBox("auto", title)
            self.fields[title] = value_box
            self.titles[title] = title_box
            self.grid_data.append([title_box, value_box, go_box])

        self.paletteView.group.list = vanilla.GridView(
            (self.margin, self.margin, -self.margin, -self.margin - 30),
            self.grid_data,
            columnPadding=(2, 2),
            rowPadding=(2, 2),
            rowSpacing=5,
            columnSpacing=5,
            columnPlacement="leading",
            rowPlacement="top",
            rowAlignment="lastBaseline",
        )
        self.height = 26 + 20 * (len(self.schema.keys()))
        self.paletteView.resize(self.width, self.height)

    @objc.python_method
    def callback(self, sender=None):
        self.saveGlyphMetadata()
        self.makeClasses()

    @objc.python_method
    def gotoGlyph(self, sender=None):
        field = self.fields[sender.field]
        current_value = field.get()
        if current_value:
            Glyphs.font.newTab("/" + current_value)

    @objc.python_method
    def openTab(self, sender=None):
        if not sender:
            return
        field = self.fields[sender.field]
        current_value = field.get()
        relevant_glyphs = [
            "/" + g.name
            for g in self.font.glyphs
            if g.userData.get(OUR_KEY, {}).get(sender.field) == current_value
        ]

        Glyphs.font.newTab("".join(relevant_glyphs))
        print(relevant_glyphs)

    def makeClasses(self):
        try:
            all_glyph_data = {
                g.name: g.userData.get(OUR_KEY, {}) for g in self.font.glyphs
            }
            our_classes = {}
            # Add all classes, so things which have empty are
            # removed. i.e. if there are no longer any foo_Yes items then
            # foo_Yes still needs to be altered
            for key, schema_item in self.schema.items():
                for suffix in schema_item.class_suffixes():
                    our_classes["gmd_%s_%s" % (key, suffix)] = []

            # Now populate them from the glyphs
            for glyph, data in all_glyph_data.items():
                for key, value in data.items():
                    if key not in self.schema:
                        continue
                    schema_item = self.schema[key]
                    suffix = schema_item.class_suffix(value)
                    if not suffix:
                        continue
                    class_name = "gmd_%s_%s" % (key, suffix)
                    class_name.replace(" ", "_")
                    our_classes.setdefault(class_name, []).append(glyph)
            for name, glyphs in our_classes.items():
                if self.font.classes[name]:
                    self.font.classes[name].code = " ".join(glyphs)
                else:
                    my_class = GSClass(name, " ".join(glyphs))
                    self.font.classes.append(my_class)
                # Tidy up
                if not glyphs:
                    del self.font.classes[name]
        except Exception as e:
            self.logError(traceback.format_exc())

    @objc.python_method
    def schemaChanged(self, sender=None):
        self.buildSchemaFromPlist(Glyphs.font.userData[OUR_KEY])
        self.buildInterfaceFromSchema()
        if self.selectedGlyph:
            self.loadGlyphMetadata()

    @objc.python_method
    def start(self):
        # Adding a callback for the 'GSUpdateInterface' event
        Glyphs.addCallback(self.update, UPDATEINTERFACE)

    @objc.python_method
    def __del__(self):
        # remove the callback
        Glyphs.removeCallback(self.update)

    @objc.python_method
    def update(self, sender):
        """
    Called from the notificationCenter if the info in the current Glyph window has changed.
    This can be called quite a lot, so keep this method fast.
    """
        try:
            # do not update in case the palette is collapsed
            if self.dialog.frame().origin.y != 0:
                return
            oldfont = self.font
            # print("Update!")
            # print("Old font: %s" % str(oldfont))
            if sender:
                if Glyphs.buildNumber >= 3004:
                    editView = sender.object()
                    self.font = editView.representedObject()
                else:
                    self.font = sender.object()
            # else:
            # print("No sender")
            # print("New font: %s" % str(self.font))
            if not self.font:
                self.paletteView.group.schema_editor.enable(False)
                return
            self.paletteView.group.schema_editor.enable(True)
            if self.font != oldfont:  # Or glyphs have changed
                # print("Font has changed!!")
                # Rebuild interface
                self.buildInterfaceFromSchema()
                if self.schema:
                    for widget in self.schema.values():
                        widget.refresh(self)
            if self.schema:
                self.paletteView.group.list.showColumn(1, False)
                self.paletteView.group.list.showColumn(2, False)
                self.selectedGlyph = None
                if self.font.selectedLayers:
                    selectedGlyphs = [
                        layer.parent
                        for layer in self.font.selectedLayers
                        if layer.parent
                    ]
                    if len(selectedGlyphs) == 1:
                        self.selectedGlyph = selectedGlyphs[0]
                        self.paletteView.group.list.showColumn(1, True)
                        self.paletteView.group.list.showColumn(2, True)
                if self.selectedGlyph:
                    self.loadGlyphMetadata()
        except Exception as e:
            self.logError(traceback.format_exc())

    # Source -> interface
    @objc.python_method
    def loadGlyphMetadata(self):
        try:
            print("Loading glyph userdata for %s" % self.selectedGlyph)
            data = self.selectedGlyph.userData.get(OUR_KEY, {})
            print(data)
            for key, obj in self.fields.items():
                if key in data:
                    obj.set(data[key])
                    self.titles[key].set(key)
                else:
                    # Set to default
                    obj.set(self.schema[key].default_value)
                    self.titles[key].set(grey(key))
        except Exception as e:
            self.logError(traceback.format_exc())

    # interface -> source
    @objc.python_method
    def saveGlyphMetadata(self):
        try:
            data = self.selectedGlyph.userData.get(OUR_KEY, {})
            for key, obj in self.fields.items():
                data[key] = obj.get()
                self.titles[key].set(key)
            self.selectedGlyph.userData[OUR_KEY] = data
        except Exception as e:
            self.logError(traceback.format_exc())

    def currentSchemaEditor(self):
        if hasattr(self, "schema_editor_window_%s" % self.generation):
            return getattr(self, "schema_editor_window_%s" % self.generation)

    def openSchemaEditor(self, sender=None):
        if hasattr(self, "schema_editor_window_%s" % self.generation):
            # Just leak it. At least it doesn't crash.
            pass
        self.generation = self.generation + 1
        schema_editor_window = vanilla.FloatingWindow(
            (500, 500), title="Metadata Schema Editor",
        )
        setattr(
            self, "schema_editor_window_%s" % self.generation, schema_editor_window,
        )
        schema_editor_window.parent = self
        schema_editor_window.new_schema = OrderedDict(self.schema)
        self.rebuildSchemaEditor("Initial setup")

        schema_editor_window.add_row = vanilla.Button(
            (0, -23, 100, 20), "Add Row", callback=self.schemaEditorAddRow
        )
        schema_editor_window.save = vanilla.Button(
            (120, -23, 100, 20), "Save", callback=self.schemaEditorSave
        )
        schema_editor_window.show()

    @objc.python_method
    def rebuildSchemaEditor(self, why):
        if self.rebuilding_schema_editor_mutex:
            return
        self.rebuilding_schema_editor_mutex = True
        try:
            # print("Rebuilding: %s" % why)
            schema_editor_window = self.currentSchemaEditor()
            if hasattr(schema_editor_window, "schema_grid"):
                gridView = schema_editor_window.schema_grid.getNSGridView()
                rows = gridView.numberOfRows()
                for i in range(rows - 1, 0, -1):
                    item = gridView.rowAtIndex_(i)
                    item.setHidden_(True)
                    gridView.removeRowAtIndex_(i)
            else:
                schema_editor_window.schema_grid = vanilla.GridView(
                    (0, 0, -0, -26),
                    [
                        [
                            vanilla.TextBox((0, 0, 100, 26), "Name"),
                            vanilla.TextBox("auto", "Widget Type"),
                            vanilla.TextBox("auto", ""),
                            vanilla.TextBox("auto", "Remove"),
                        ]
                    ],
                    columnPadding=(5, 5),
                    columnSpacing=10,
                    rowPadding=(2, 2),
                    columnPlacement="center",
                    rowPlacement="top",
                    rowAlignment="lastBaseline",
                )
            self.schema_editor_stuff = []  # We need to hold them, I think
            for title, widget in schema_editor_window.new_schema.items():
                title_box = vanilla.EditText(
                    (0, 0, 100, 26),
                    title,
                    callback=self.schemaEditorRenameRow,
                    continuous=False,
                )
                title_box.old_title = title
                options = ["Dropdown", "Glyphbox", "Checkbox", "Textbox"]
                type_box = vanilla.PopUpButton(
                    "auto", options, callback=self.schemaEditorChangeType
                )
                type_box.title = title
                type_box.setItem(widget.__class__.__name__)
                if isinstance(widget, Dropdown):
                    edit_options_box = system_image_button(
                        "NSActionTemplate", "Edit Options", self.schemaEditorEditOptions
                    )
                    edit_options_box.title = title
                else:
                    edit_options_box = vanilla.TextBox("auto", "")
                remove_box = system_image_button(
                    "NSRemoveTemplate", "Remove this row", self.schemaEditorRemoveRow
                )
                remove_box.title = title
                row = [title_box, type_box, edit_options_box, remove_box]
                self.schema_editor_stuff.append(row)
                schema_editor_window.schema_grid.appendRow(row)
            schema_editor_window.getNSWindow().setViewsNeedDisplay_(True)
        except Exception as e:
            self.logError(traceback.format_exc())
        self.rebuilding_schema_editor_mutex = False

    @objc.python_method
    def schemaEditorRemoveRow(self, sender=None):
        del self.currentSchemaEditor().new_schema[sender.title]
        self.rebuildSchemaEditor("Removed row")

    @objc.python_method
    def schemaEditorEditOptions(self, sender=None):
        pass

    @objc.python_method
    def schemaEditorRenameRow(self, sender=None):
        new_name = sender.get()
        old_name = sender.old_title
        # print("Renaming %s -> %s" % (old_name, new_name))
        self.currentSchemaEditor().new_schema = OrderedDict(
            [
                (new_name, v) if k == old_name else (k, v)
                for k, v in self.currentSchemaEditor().new_schema.items()
            ]
        )
        # print(self.currentSchemaEditor().new_schema)
        self.rebuildSchemaEditor("Renamed row")

    @objc.python_method
    def schemaEditorAddRow(self, sender=None):
        print("Hello, %s" % sender)
        self.currentSchemaEditor().new_schema["New Entry"] = Textbox()
        self.rebuildSchemaEditor("Added row")

    @objc.python_method
    def schemaEditorChangeType(self, sender=None):
        newtype = sender.getItem()
        # print("Changing %s to %s" % (sender.title, newtype))
        if newtype == "Checkbox":
            self.currentSchemaEditor().new_schema[sender.title] = Checkbox()
        elif newtype == "Glyphbox":
            self.currentSchemaEditor().new_schema[sender.title] = Glyphbox()
        elif newtype == "Textbox":
            self.currentSchemaEditor().new_schema[sender.title] = Textbox()
        elif newtype == "Dropdown":
            self.currentSchemaEditor().new_schema[sender.title] = Dropdown()
        # print(self.currentSchemaEditor().new_schema)
        self.rebuildSchemaEditor("Changed type")

    @objc.python_method
    def schemaEditorSave(self, sender=None):
        print("Save")
        serialized_schema = [
            (title, widget.serialize())
            for title, widget in self.currentSchemaEditor().new_schema.items()
        ]
        print(serialized_schema)
        self.font.userData[OUR_KEY] = serialized_schema
        self.schemaChanged()

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__
