import os, sys, math, time, datetime
import xmp

folder = '/Users/zach/Pictures/2012/2012-06-05'

files = [x for x in os.listdir(folder) if x.endswith('.xmp')]

tweenpoints = []

corrections = {}

shutters = set()
apertures = set()

for filename in files:
    f = open(folder + '/' + filename)
    xmp_data = xmp.load(f)
    f.close()

    filename, shutterspeed, fnumber, correction = xmp_data.shot_data()

    shutterspeed = eval(shutterspeed[1:-1] + '.0')
    fnumber = eval(fnumber[1:-1] + '.0')
    
    if shutterspeed not in corrections:
        corrections[shutterspeed] = {}
    if fnumber not in corrections[shutterspeed]:
        corrections[shutterspeed][fnumber] = set()

    if correction:
        corrections[shutterspeed][fnumber].add(correction)

    shutters.add(shutterspeed)
    apertures.add(fnumber)

    if xmp_data.haschanges():
        tweenpoints.append(xmp_data)

table = []
##shutters = list(map(lambda k: eval(k[1:-1] + '.0'), shutters))
##apertures = list(map(lambda k: eval(k[1:-1] + '.0'), apertures))

shutters = list(shutters)
apertures = list(apertures)
shutters.sort()
apertures.sort()

for i in apertures:
    line = {"aperture": i}                
    for j in shutters:
        if i in corrections[j] and len(corrections[j][i]) == 1:
            line[j] = float(list(corrections[j][i])[0].strip('"'))
        elif i in corrections[j] and 0 in corrections[j][i]:
            line[j] = 0
        else:
            line[j] = None
    table.append(line)

import csv

f = open('exptable3.csv', 'w')
r = csv.DictWriter(f, ['aperture'] + shutters)
r.writeheader()
r.writerows(table)
f.close()


