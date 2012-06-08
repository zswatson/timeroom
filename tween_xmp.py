from argparse import ArgumentParser
import os, sys, math, time, datetime
import xmp

def calc_exposure_correction_for_xmp(current_xmp, all_xmps, scope):
    shutter_av, aperture_av = calc_average(current_xmp, all_xmps, scope)
    current_shutter = current_xmp.get_val(xmp.SHUTTERTIME)
    current_aperture = current_xmp.get_val(xmp.FNUMBER)

    exposure_correction = calc_exposure_correction(shutter_av, current_shutter,
                                                   aperture_av, current_aperture)

    return exposure_correction    

def calc_exposure_correction(base_shutter, new_shutter, base_aperture, new_aperture):
    return math.log(base_shutter, 2) - math.log(new_shutter, 2) + \
           2 * (math.log(new_aperture, 2) - math.log(base_aperture, 2))

def set_tweened_values(start_xmp, end_xmp, current_xmp):
    for variable in xmp.available_vars:
        start = start_xmp.get_val(variable)
        if start is None:
            start = 0
        end = end_xmp.get_val(variable)
        if end is None:
            end = 0

        current = current_xmp.get_val(variable)

        ratio = float((current_xmp.datetime - start_xmp.datetime).seconds) \
                / float((end_xmp.datetime - start_xmp.datetime).seconds)

        if current:
            current_xmp.set_val(variable, current + start + (end - start) * ratio)
        else:
            current_xmp.set_val(variable, start + (end - start) * ratio)


def calc_average(current_xmp, all_xmps, scope): 

    start_index = 0
    while True:
        tdelta = (current_xmp.datetime - all_xmps[start_index].datetime).seconds
        if tdelta <= scope:
            break
        start_index += 1

    end_index = all_xmps.index(current_xmp)
    
    while True:
        tdelta = (all_xmps[end_index].datetime - current_xmp.datetime).seconds
        if tdelta > scope:
            break
        end_index += 1
        if end_index >= len(all_xmps):
            break
    
    shutter_sum = 0
    aperture_sum = 0
    
    for i in range(start_index, end_index):
        temp_xmp = all_xmps[i]
        shutter_sum += temp_xmp.get_val(xmp.SHUTTERTIME)
        aperture_sum += temp_xmp.get_val(xmp.FNUMBER)
     
    shutter_av = shutter_sum / (end_index - start_index)
    aperture_av = aperture_sum / (end_index - start_index)

    return shutter_av, aperture_av

def load_xmps(source_folder):

    temp_tweenpoints = []

    all_xmps = []
    files = [x for x in os.listdir(source_folder) if x.endswith('.xmp')]

    for filename in files:
        #
        # Get all xmps that have been changed, which will be used as keyframes
        # for tweening.
        #
        
        f = open(source_folder + '/' + filename)
        xmp_data = xmp.load(f)
        f.close()

        if xmp_data.haschanges():
            temp_tweenpoints.append(xmp_data)
        all_xmps.append(xmp_data)

    sorted(all_xmps, key = lambda k: k.datetime)

    tweenpoints = map(lambda k: all_xmps.index(k), temp_tweenpoints)
    tweenpoints.extend((0, len(all_xmps) - 1))
    tweenpoints = list(set(tweenpoints))
    tweenpoints.sort()
 
    return tweenpoints, all_xmps

def compensate_tweenpoints(tweenpoints, all_xmps, scope):
    """ For all tweenpoints, calculate exposure correction, and subtract it from
        the given exposure correction (in order to factor it out of the tweening).
        Operates on all_xmps in place.
    """

    for t in tweenpoints:
        current_xmp = all_xmps[t]
        exposure_correction = calc_exposure_correction_for_xmp(current_xmp, all_xmps, scope)
        current_exposure = current_xmp.get_val(xmp.EXPOSURE)
        if not current_exposure:
            current_exposure = 0

        current_xmp.set_val(xmp.EXPOSURE, current_exposure - exposure_correction)

def tween_xmps(tweenpoints, all_xmps):
    """ Tween all values between all tweenpoints; if value is not set in a
        tweenpoint, assume it is 0. Operates on all_xmps in place.
    """

    for index in range(len(all_xmps)):
        current_xmp = all_xmps[index]
        
        #
        # Tween between whatever tweenpoints are immediately before and after the
        # current xmp
        #
        
        if index not in tweenpoints:
            start_tweenpoint, end_tweenpoint = index, index

            for i in tweenpoints:
                end_tweenpoint = i
                if i > index:
                    break
            
            for i in reversed(tweenpoints):
                start_tweenpoint = i
                if i < index:
                    break

            set_tweened_values(all_xmps[start_tweenpoint], all_xmps[end_tweenpoint], current_xmp)

def smooth_exposures(tweenpoints, all_xmps, scope):
    """ Smooths exposures in place
    """

    for current_xmp in all_xmps:
        #
        # Calculate the exposure correction, and add it to any tweened exposure value
        #

        exposure_correction = calc_exposure_correction_for_xmp(current_xmp, all_xmps, scope)                  
        current_exposure = current_xmp.get_val(xmp.EXPOSURE)
        
        current_xmp.set_val(xmp.EXPOSURE, current_exposure + exposure_correction)


def write_xmps(all_xmps, outfolder):
    """ Writes out xmp files to outfolder, named from original NEF name
    """
    
    for current_xmp in all_xmps:
        current_xmp.write_to_xmp(outfolder)

def set_for_all_xmps(all_xmps, variable, value):
    """ Sets a variable to a specified value for all xmps. Operates in place.
    """
    for current_xmp in all_xmps:
        current_xmp.set_val(variable, value)

parser = ArgumentParser(description="""tween_xmp.py [options] folder

Loads all the xmps in a folder, and picks tweenpoints based on edited xmps.

""")

defaults = dict(tween=False, exposure_smoothing=None, static_vars=[], dest=None)

parser.set_defaults(**defaults)

parser.add_argument('folder', help='Source folder for xmps')

parser.add_argument('-d', '--destination', help='Destination folder for xmps', dest='dest')

parser.add_argument('-t', '--tween', dest='tween',
                  help='Tween between altered xmps.', action="store_true")

parser.add_argument('-x', '--exposure_smoothing', dest='exposure_smoothing', type=float, action="store",
                  help='Seconds on either side to consider when smoothing exposures')

parser.add_argument('-v', '--var', dest='static_vars', nargs='*',
                  help='Variable and value to set for all xmps',
                  action='append')

if __name__ == '__main__':

    args = parser.parse_args()

    statics = {}
    if len(args.static_vars) % 2 != 0:
        raise Exception
    else:
        for i in range(0, len(args.static_vars), 2):
            statics[args.static_vars[i]] = args.static_vars[i + 1]

    tweenpoints, all_xmps = load_xmps(args.folder)
    if args.dest is not None:
        outfolder = args.dest
    else:
        outfolder = args.folder

    try:
        os.mkdir(outfolder)
    except:
        pass

    if not args.exposure_smoothing is None:
        compensate_tweenpoints(tweenpoints, all_xmps, args.exposure_smoothing)

    if args.tween:
        tween_xmps(tweenpoints, all_xmps)

    if not args.exposure_smoothing is None:
        smooth_exposures(tweenpoints, all_xmps, args.exposure_smoothing)

    for var in statics:
        set_for_all_xmps(var, statics[var])
        
    write_xmps(all_xmps, outfolder)





