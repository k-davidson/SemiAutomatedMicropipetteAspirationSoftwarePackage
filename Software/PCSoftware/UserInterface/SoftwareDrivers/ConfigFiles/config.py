GUI_COLOURS = dict(
    PURPLE = "#5856d6",
    BLUE = "#0f175c",
    AQUA = "#34aadc",
    LIGHT_BLUE = "#5ac8fa",
    GREEN = "#4cd964",
    PINK = "#ff2d55",
    RED = "#ff3b30",
    ORANGE = "#ff9500",
    YELLOW = "#ffcc00",
    GRAY = "#8e8e93",
    WHITE = "#ffffff",
    BACKGROUND1 = "#5A666B",
    BACKGROUND2 = "#4a5051",
    FOREGROUND1 = "#BDC7C1",
    FOREGROUND2 = "#7E8889"

)


class colourScheme():
    def __init__(self):
        self.styleSheet = dict(
            QPushButton = '''
            ''',
            QTabWidget_pane = '''
            ''',
            QMainWindow = '''
            ''',
            QTabBar_tab_selected = '''
            '''
        )

    def setWidgetStyle(self, widget, backgroundColor = None, colour = None, 
                        borderColor = None, borderWidth = None,
                        borderRadius = None, fontSize = None,
                        fontWeight = None, palette = None):
        if(widget is None):
            return
        
        self.styleSheet[widget] = ""
        
        if(backgroundColor is not None):
            self.styleSheet[widget] += "background: %s;\n"%(backgroundColor)
        
        if(colour is not None):
            self.styleSheet[widget] += "color: %s;\n"%(colour)

        if(palette is not None):
            self.styleSheet[widget] += "background: palette(%s);\n"%(palette)

        if(borderColor is not None and borderWidth is not None):
            self.styleSheet[widget] += "border: %.2fpx solid #FFFFFF;\n"%(borderWidth)

        if(borderRadius is not None):
            self.styleSheet[widget] += "border-radius: %.2fpx;\n"%(borderRadius)

        if(fontSize is not None):
            self.styleSheet[widget] += "font-size: %.2fpt;\n"%(fontSize)

        if(fontWeight is not None):
            self.styleSheet[widget] += "font-weight: %.2f;\n"%(fontWeight)


    
    def toString(self):
        styleString = ""
        for key in self.styleSheet.keys():
            keyString = self.keyString(key)
            styleString += "%s{\n"%(keyString)
            styleString += self.styleSheet[key]
            styleString += "}\n"

        return styleString

    def keyString(self, key):
        return key.replace("_","::")



styleSheet = colourScheme()
styleSheet.setWidgetStyle(
            "QTabWidget_pane",
            backgroundColor = GUI_COLOURS["FOREGROUND1"],
            colour = GUI_COLOURS["WHITE"],
            borderColor= GUI_COLOURS["WHITE"],
            borderWidth= 2, borderRadius = 12)

styleSheet.setWidgetStyle(
            "QTabBar_tab_selected",
            backgroundColor = GUI_COLOURS["FOREGROUND2"],
            colour = GUI_COLOURS["WHITE"])

styleSheet.setWidgetStyle(
            "QTabBar_tab",
            backgroundColor = GUI_COLOURS["BACKGROUND2"],
            colour = GUI_COLOURS["WHITE"])

styleSheet.setWidgetStyle(
            "QGroupBox",
            backgroundColor = GUI_COLOURS["FOREGROUND1"],
            colour = GUI_COLOURS["WHITE"],
            borderColor= GUI_COLOURS["WHITE"],
            borderWidth= 2, borderRadius = 12)

styleSheet.setWidgetStyle(
            "QLabel",
            colour = GUI_COLOURS["BACKGROUND2"])

styleSheet.setWidgetStyle(
    "QMainWindow",
    backgroundColor = GUI_COLOURS["BACKGROUND1"],
    colour = GUI_COLOURS["WHITE"])

styleSheet.setWidgetStyle(
    "QPushButton",
    backgroundColor = GUI_COLOURS["WHITE"],
    colour = GUI_COLOURS["BACKGROUND1"])


    