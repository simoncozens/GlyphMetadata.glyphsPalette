# encoding: utf-8

import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from vanilla import *
from AppKit import NSView

OUR_KEY = "uk.co.corvelsoftware.GlyphMetadata"

schema = {
    "Role": {"type": "dropdown", "options": ["Base Consonant", "Dependant Vowel"]},
    "Form": {"type": "dropdown", "options": ["Single Bowl", "Double Bowl"]},
    "Conjunct Form": {"type": "glyph", "demo": "ka-myanmar.below"},
    "Phake Localization": {"type": "glyph", "demo": "ka-aiton"},
}


class GlyphMetadataPalette(PalettePlugin):
    def glyph_combobox(self):
        # We should refresh these on update
        if self.font:
            glyphnames = [g.name for g in self.font.glyphs]
        else:
            glyphnames = []
        return ComboBox("auto", glyphnames, callback=self.callback)

    @objc.python_method
    def settings(self):
        try:
            print("A")
            self.name = Glyphs.localize({"en": u"Glyph Metadata"})
            print("A")
            self.width = 150
            self.font = None
            self.height = 26 + 20 * (1 + len(schema.keys()))
            self.paletteView = Window(
                (self.width, self.height),
                minSize=(self.width, self.height - 10),
                maxSize=(self.width, self.height + 200),
            )
            self.grid_data = []
            self.fields = {}
            for title, role in schema.items():
                print("Building %s" % title)
                if role["type"] == "glyph":
                    value_box = self.glyph_combobox()
                elif role["type"] == "checkbox":
                    value_box = CheckBox("auto", None, callback=self.callback)
                else:
                    value_box = EditText("auto", text=role.get("demo"))
                self.fields[title] = value_box
                self.grid_data.append([TextBox("auto", title), value_box])
            self.paletteView.group = Group((0, 0, 0, 0))
            print("Built group")
            self.paletteView.group.list = GridView(
                (self.margin, self.margin, -self.margin, -self.margin), grid_data,
            )
            print("Built list")

            # Set dialog to NSView
            self.dialog = self.paletteView.group.getNSView()
        except Exception as e:
            print(e)

    @objc.python_method
    def callback(self, sender=None):
        self.saveGlyphMetadata()
        # Sort out any groups
        pass

    # Source -> interface
    @objc.python_method
    def loadGlyphMetadata(self):
        data = self.selectedGlyph.userData.get(OUR_KEY, {})
        for key, obj in self.fields.items():
            if key in data:
                obj.set(data[key])

    # interface -> source
    @objc.python_method
    def saveGlyphMetadata(self):
        data = self.selectedGlyph.userData.get(OUR_KEY, {})
        for key, obj in self.fields.items():
            data[key] = obj.get()
        self.selectedGlyph.userData[OUR_KEY] = data

    @objc.python_method
    def update(self, sender=None):
        pass
        # try:
        #     # do not update in case the palette is collapsed
        #     if self.dialog.frame().origin.y != 0:
        #         return
        #     if sender:
        #         if Glyphs.buildNumber >= 3004:
        #             editView = sender.object()
        #             if editView.windowController() != self.windowController():
        #                 return
        #             self.font = editView.representedObject()
        #         else:
        #             self.font = sender.object()
        #     if not self.font:
        #         return
        #     sharedNames = []
        #     self.paletteView.group.list.showColumn(1, False)
        #     self.selectedGlyph = None
        #     if self.font.selectedLayers:
        #         selectedGlyphs = [
        #             layer.parent for layer in self.font.selectedLayers if layer.parent
        #         ]
        #         if len(selectedGlyphs) == 1:
        #             self.selectedGlyph = selectedGlyphs[0]
        #             self.paletteView.group.list.showColumn(1, True)
        #     if self.selectedGlyph:
        #         self.loadGlyphMetadata()
        # except Exception as e:
        #     print(e)

    # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
    # the following methods are adopted from the SDK without any changes

    @objc.python_method
    def start(self):
        # Adding a callback for the 'GSUpdateInterface' event
        Glyphs.addCallback(self.update, UPDATEINTERFACE)

    @objc.python_method
    def __del__(self):
        Glyphs.removeCallback(self.update)

    @objc.python_method
    def __file__(self):
        """Please leave this method unchanged"""
        return __file__

    # Temporary Fix
    # Sort ID for compatibility with v919:
    _sortID = 0

    @objc.python_method
    def setSortID_(self, id):
        try:
            self._sortID = id
        except Exception as e:
            self.logToConsole("setSortID_: %s" % str(e))

    @objc.python_method
    def sortID(self):
        return self._sortID
