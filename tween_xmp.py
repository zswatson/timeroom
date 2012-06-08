import os, sys, math, time, datetime
import xmp

SCOPE = 600 ## number of seconds before and after a frame to
            ## consider when adjusting exposure

def calc_exposure_correction_for_xmp(current_xmp, all_xmps):
    shutter_av, aperture_av = calc_average(current_xmp, all_xmps)
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


def calc_average(current_xmp, all_xmps): 

    start_index = 0
    while True:
        tdelta = (current_xmp.datetime - all_xmps[start_index].datetime).seconds
        if tdelta <= SCOPE:
            break
        start_index += 1

    end_index = all_xmps.index(current_xmp)
    
    while True:
        tdelta = (all_xmps[end_index].datetime - current_xmp.datetime).seconds
        if tdelta > SCOPE:
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

def compensate_tweenpoints(tweenpoints, all_xmps):
    """ For all tweenpoints, calculate exposure correction, and subtract it from
        the given exposure correction (in order to factor it out of the tweening).
        Operates on all_xmps in place.
    """

    for t in tweenpoints:
        current_xmp = all_xmps[t]
        exposure_correction = calc_exposure_correction_for_xmp(current_xmp, all_xmps)
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

def smooth_exposures(tweenpoints, all_xmps):
    """ Smooths exposures in place
    """

    for current_xmp in all_xmps:
        #
        # Calculate the exposure correction, and add it to any tweened exposure value
        #

        exposure_correction = calc_exposure_correction_for_xmp(current_xmp, all_xmps)                  
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

tweenpoints, all_xmps = load_xmps('./old_xmps')
outfolder = '.'

try:
    os.mkdir(outfolder)
except:
    pass

compensate_tweenpoints(tweenpoints, all_xmps)
tween_xmps(tweenpoints, all_xmps)
smooth_exposures(tweenpoints, all_xmps)
##set_for_all_xmps(xmp.CAMERAPROFILE, 'D40_IR_1')
write_xmps
