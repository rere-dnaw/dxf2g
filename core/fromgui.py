class GLWidget():
    def __init__(self, parent=None):
        self.shapes = Shapes([])
        self.orientation = 0
        self.wpZero = 0
        self.routearrows = []
        self.expprv = None

        self.isPanning = False
        self.isRotating = False
        self.isMultiSelect = False
        self._lastPos = QPoint()

        self.posX = 0.0
        self.posY = 0.0
        self.posZ = 0.0
        self.rotX = 0.0
        self.rotY = 0.0
        self.rotZ = 0.0
        self.scale = 1.0
        self.scaleCorr = 1.0

        self.showPathDirections = False
        self.showDisabledPaths = False

        self.BB = BoundingBox()

        self.tol = 0
    
    def plotAll(self, shapes):
        for shape in shapes:
            self.paint_shape(shape)
            self.shapes.append(shape)
        self.drawWpZero()
    