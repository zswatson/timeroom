import datetime

EXPOSURE = 'Exposure2012'
CONTRAST = 'Contrast2012'
HIGHLIGHTS = 'Highlights2012'
SHADOWS = 'Shadows2012'
WHITES = 'Whites2012'
BLACKS = 'Blacks2012'
CLARITY = 'Clarity2012'
VIBRANCE = 'Vibrance'
SATURATION = 'Saturation'
TEMPERATURE = 'Temperature'
TINT = 'Tint'
CAMERAPROFILE = 'CameraProfile'

RAWFILENAME = 'RawFileName'
SHUTTERTIME = 'ExposureTime'
FNUMBER = 'FNumber'
DATETIMEORIGINAL = 'DateTimeOriginal'

WHITEBALANCE = "WhiteBalance"

CRS = 'crs'
EXIF = 'exif'

available_vars = [EXPOSURE, CONTRAST, HIGHLIGHTS, SHADOWS, WHITES, TINT,
                  BLACKS, CLARITY, VIBRANCE, SATURATION, TEMPERATURE]

NEF_vars = [RAWFILENAME, SHUTTERTIME, FNUMBER, DATETIMEORIGINAL]

__var_cats__ = {EXPOSURE:CRS, CONTRAST:CRS, HIGHLIGHTS:CRS, SHADOWS:CRS,
                WHITES:CRS, TINT:CRS, BLACKS:CRS, CLARITY:CRS, VIBRANCE:CRS,
                SATURATION:CRS, TEMPERATURE:CRS, RAWFILENAME:CRS,
                SHUTTERTIME:EXIF, FNUMBER:EXIF, DATETIMEORIGINAL:EXIF,
                WHITEBALANCE:CRS, CAMERAPROFILE:CRS}

def attach_sign(value):
    if value > 0:
        sign = "+"
    else:
        sign = "-"
    return sign + str(value) 

class xmp_object(object):
    """ Reads in Lightroom 4 Mac Version xmp files, pulls out selected data
        (see available_vars) into a dictionary, and allows writing out of
        any changes
    """

    def float_val(self, val):
        a = val[1:-1]
        if a.startswith('+'):
            a = a[1:]

        b = None

        try:
            b = eval(a + '.0')
        except:
            b = float(a)

        if b is None:
            raise Exception()
        else:
            return b

    def strip_quotes(self, val):
        return val[1:-1]

    def format_val(self, val):
        """ currently just makes the value a string and wraps it in double
            quotes
        """
        return '"' + str(val) + '"'
            
    def __split_line__(self, line):
        """ Splits a line of the xmp into category, variable, and value
        """
        line = line.strip()
        cat, pair = line.split(':', 1)
        key, val = pair.split('=', 1)
        return cat, key, val

    def __create_line__(self, cat, key, val):
        """ Creates a line for writing to xmp
        """
        val = self.format_val(val)
        return cat + ':' + key + '=' + val

    def __add__(self, cat, key, val):
        """ Adds a category-variable-calue triplet to the __data__ dictionary
        """
        
        if cat not in self.__data__:
            self.__data__[cat] = {}
        self.__data__[cat][key] = val

    def __add_line__(self, line):
        """ Reads in a line from xmp, extracts category, variable, and value,
            and writes it to the __data__dictionary
        """

        cat, key, val = self.__split_line__(line)

        try:
            val = self.float_val(val)
        except:
            val = self.strip_quotes(val)        
        
        self.__add__(cat, key, val)
    
    def __init__(self, lines):
        self.__header__ = []
        self.__data__ = {}
        self.__footer__ = []
        self.__indent__ = '   '
        
        datastart = '  <rdf:Description '
        dataend = '>\n'

        target = self.__header__
        #
        # Read in all the values in; dump into header until we run into
        # datastart, then start building data dicts; when dataend shows up,
        # dump into footer
        #
        for line in lines:
            global bob
            bob = line
            if target == self.__header__ and line.startswith(datastart):
                self.__header__.append(datastart)
                line = line[len(datastart):]
                self.__add_line__(line)
                target = self.__data__
                continue
            elif target == self.__data__ and line.endswith(dataend):
                self.__footer__.append(dataend)
                line = line[:-len(dataend)]
                self.__add_line__(line)
                target = self.__footer__
                continue

            if target == self.__data__:
                self.__add_line__(line)
            else:
                target.append(line)

        self.datetime = self.get_datetime()

    def write_to_xmp(self, folder = '.'):
        filename = self.get_val(RAWFILENAME).strip('"')[:-3] + 'xmp'
        self.write(folder + '/' + filename)
        

    def write(self, filename):
        outfile = open(filename, 'w')
        
        for line in self.__header__:
            outfile.write(line)

        datalines = []
        for cat in self.__data__:
            for key in self.__data__[cat]:
                val = self.__data__[cat][key]
                datalines.append(self.__create_line__(cat, key, val))

        outfile.write(datalines[0] + '\n')
        for i in range(1, len(datalines) - 1):
            outfile.write(self.__indent__ + datalines[i] + '\n')
        outfile.write(self.__indent__ + datalines[-1])

        for line in self.__footer__:
            outfile.write(line)
        outfile.close()

    def haschanges(self):
        """ Returns True if the xmp has any adjustments in it, False if it's
            just NEF data
        """
        
        if 'crs' in self.__data__ and len(self.__data__['crs']) > 1:
            return True
        else:
            return False

    def set_val(self, key, val):
        """ Write a category-variable-value triplet to __data__
        """
        cat = __var_cats__[key]

        if key == 'Temperature' or key == 'Tint':
            self.set_val('WhiteBalance', 'Custom')
        
        if cat not in self.__data__:
            self.__data__[cat] = {}
        self.__data__[cat][key] = val

    def get_val(self, key):
        a = None
        cat = __var_cats__[key]
        try:
            a = self.__data__[cat][key]
        except:
            pass

        return a

    def get_datetime(self):
        raw = self.get_val('DateTimeOriginal')
        if raw[-6] == '-' or raw[-6] == '+':
            raw = raw[:-6]
        
        d = datetime.datetime.strptime(raw, '%Y-%m-%dT%H:%M:%S.%f')

        return d

    def shot_data(self):
        """ Grab some specific NEF data
        """
        filename = self.get_val('RawFileName')
        shutterspeed = self.get_val('ExposureTime')
        fnumber = self.get_val('FNumber')
        correction = self.get_val('Exposure2012')
        return filename, shutterspeed, fnumber, correction
                
def load(f):
    return xmp_object(f.readlines())
        
##f = open('DSC_0000_og.xmp')
##
##a = load(f)
##f.close()
##
####for i in xmp_object.available_vars:
####    import random
####    a.set_val('crs', i, random.randint(-10, 10))
##
##a.set_contrast(50)
##a.set_exposure(.5)
##a.set_temp(3800)
##
##a.write('DSC_0000.xmp')

