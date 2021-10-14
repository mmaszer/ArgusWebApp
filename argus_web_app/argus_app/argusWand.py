#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function

import argparse
import shutil
import sys
import tempfile

import numpy as np
import pandas
#from argus.ocam import PointUndistorter, ocam_model
from .base import PointUndistorter, ocam_model
from scipy.sparse import lil_matrix
from six.moves import map
from six.moves import range

#import argus_gui
#import sbaDriver
from .sbaDriver import sbaArgusDriver

from django.core.files.storage import FileSystemStorage

def read_file(request):
    path = 'media/' + request
    f = open(path, 'r')
    file_content = f.read()
    f.close()
    return file_content

# gets data from CSVs. Expects a header.
def parseCSVs(csv):
    print(csv)
    #csv = read_file(csv.name)
    #csv = open(csv)
    path = 'media/' + csv.name
    #if csv.split('.')[-1] == 'csv':
    dataf = pandas.read_csv(path, index_col=False)
    dataf = dataf.dropna(how='all') # remove nan rows
    dataf = dataf.reset_index(drop=True) # reset indices
    return dataf.values
    # else check if we have sparse data representation
    '''elif csv.split('.')[-1] == 'tsv':
        fo = open(csv)
        # expect a header
        line = fo.readline()
        # next line has shape information for the sparse matrix
        line = fo.readline()
        shape = list(map(int, line.split('\t')))
        # ret = lil_matrix((shape[0], shape[1]))
        ret = lil_matrix((shape[0], shape[1]))
        ret[:, :] = np.nan
        line = fo.readline()
        while line != '':
            val = list(map(float, line.split('\t')))
            ret[int(val[0]) - 1, int(val[1]) - 1] = val[2]
            line = fo.readline()
        return ret'''


def preform_wand_caliration(args, unpaired_points, paried_points, ref, cams):
    scale = float(args['scale'])
    display = args.graph
    # print 'Graphing: {0}'.format(display)
    mode = args['intrinsics_opt'] + args['distortion_opt']
    
    # Output files location and tag
    name = args.output_name
    # temporary file name
    if args.tmp != "None":
        tmp = args.tmp
    else:
        tmp = tempfile.mkdtemp()
    # boolean for outlier analysis at the end
    rep = args.outliers
    if paried_points is not None:
        if paried_points.shape[1] != 4 * cams.shape[0]:
            print('Incorrect shape of paired points! Paired points file must have 4*(number of cameras) columns')
            sys.exit()
    if unpaired_points is not None:
        if unpaired_points.shape[1] % (2 * cams.shape[0]) != 0:
            print(
                'Incorrect shape of unpaired points! Unpaired points must have a multiple of 2*(number of cameras) columns')
            sys.exit()
    oCPs = args.output_camera_profiles

    if (paried_points is None) and (unpaired_points is not None):
        print(unpaired_points)
    else:
        print(paried_points[0][0])
        print(unpaired_points)

    driver = sbaArgusDriver(paried_points, unpaired_points, cams, display, scale, mode, ref, name, tmp, rep,
                                      oCPs, args.choose_reference, args.reference_type, args.recording_frequency)
    driver.fix()

    shutil.rmtree(tmp)


#if __name__ == '__main__':
def go(args):
    
    #args = parser.parse_args()
    print('Loading points...')
    sys.stdout.flush()

    # Get paired points from a CSV file as an array, no index column, with or without header
    if args['paired_points']:
        paried_points = parseCSVs(args['paired_points'])
    else:
        paried_points = None
    # Get unpaired points 
    if args['unpaired_points']:
        unpaired_points = parseCSVs(args['unpaired_points'])
    else:
        unpaired_points = None
        
    # Make sure we have a camera profile TXT document
    try:
        path = 'media/' + args['cams'].name
        cams = np.loadtxt(path)
    except Exception as e:
        print(e)
        print('Could not load camera profile! Make sure it is formatted according to the documentation.')
        sys.exit()
        
    # Get reference points::
    # One point - an origin
    # Two - origin and +z-axis
    # Three - origin, +x-axis, +y-axis
    # Four - origin, +x-axis, +y-axis, +z-axis
    # More - gravity or surface reference points
    if args['reference_points']:
        print('Loading reference points')
        ref = pandas.read_csv(args['reference_points'], index_col=False).values
        
        # trim to the rows with data, inclusive of any interior rows of all NaNs
        # changed on 2020-06-18 by Ty Hedrick
        idx = np.where(np.sum(np.isnan(ref),1)<ref.shape[1])
        ref = ref[idx[0][0]:idx[0][-1],:]
        
        # old way - trims all rows with any NaNs, tends to break gravity calibration
        '''
        toDel = list()
        # take out NaNs
        for k in range(ref.shape[0]):
            if True in np.isnan(ref[k]):
                toDel.append(k)
        ref = np.delete(ref, toDel, axis=0)
        '''
        
        
        
        if ref.shape[1] != 2 * cams.shape[0]:
            print('Incorrect shape of reference points! Make sure they are formatted according to the documentation.')
            sys.exit()
    else:
        ref = None
        
    # Check if the camera profile is the correct shape:
    if cams.shape[1] == 12:

        # Format the camera profile to how SBA expects it i.e.
        # take out camera number column, image width and height, then add in skew
        cams = np.delete(cams, [0, 2, 3], 1)
        cams = np.insert(cams, 4, 0., axis=1)
        preform_wand_caliration(args, unpaired_points, paried_points, ref, cams)

    else:
        # Omnidirectional camera model
        models = []
        wand_interpretable_cams = []
        try:
            for index, camera in enumerate(cams):
                # init the omni_supported_cam array to all zeros
                pinhole_from_omni_model = [0 for _ in range(0, 9)]

                # Set the Focal Length 2 to the first index of the omni_supported_cam
                pinhole_from_omni_model[0] = camera[-1]

                # Set K1, K2
                pinhole_from_omni_model[1:3] = camera[7:9]

                # Set a aspect ratio value (always 1)
                pinhole_from_omni_model[3] = 1

                # Set a skew value (nearly always 0)
                pinhole_from_omni_model[4] = 0

                # Set pinhole distortion settings
                pinhole_from_omni_model[5:9] = [0, 0, 0, 0, 0]

                # Argus seems to expect K2, K1 instead of K1, K2, but for formatting it makes
                # much more sense to have K1, K2 so the switch is done here
                k2 = pinhole_from_omni_model[1]
                pinhole_from_omni_model[1] = pinhole_from_omni_model[2]
                pinhole_from_omni_model[2] = k2

                # Append the pin-hole model for the omni camera
                wand_interpretable_cams.append(pinhole_from_omni_model)

                # Get the distortion model for the omni cam
                models.append(PointUndistorter(ocam_model.from_array(camera[1:-1])))

        except IndexError as e:
            print(e)
            print('Incorrect shape of omnidistort model, please reformat!')
            sys.exit(0)

        wand_interpretable_cams = np.array(wand_interpretable_cams)

        # undistort paired points
        points_to_undis = {}
        if type(paried_points) is not type(None):
            for row_index, point_set in enumerate(paried_points):
                new_row = [0 for i in range(0, point_set.shape[0])]
                for cam_number in range(1, cams.shape[0] + 1):
                    offest = cam_number - 2
                    if offest <= 0:
                        index = cam_number
                    else:
                        index = cam_number + offest
                    if cam_number == 1: index = 0
                    while index + 1 < point_set.shape[0]:
                        new_row[index: index + 2] = models[cam_number - 1].undistort_points(np.array([point_set[index],
                                                                                                      point_set[
                                                                                                          index + 1]]).reshape(
                            -1, 1))
                        index += (cams.shape[0] - 1) * 2 + 2
                paried_points[row_index] = new_row

        # undistort unpaired points
        if type(unpaired_points) is not type(None):
            for row_index, point_set in enumerate(unpaired_points):
                new_row = [0 for i in range(0, point_set.shape[0])]
                for cam_number in range(1, cams.shape[0] + 1):
                    offest = cam_number - 2
                    if offest <= 0:
                        index = cam_number
                    else:
                        index = cam_number + offest
                    if cam_number == 1: index = 0
                    while index + 1 < point_set.shape[0]:
                        new_row[index: index + 2] = models[cam_number - 1].undistort_points(np.array([point_set[index],
                                                                                                      point_set[
                                                                                                          index + 1]]).reshape(
                            -1, 1))
                        index += (cams.shape[0] - 1) * 2 + 2
                unpaired_points[row_index] = new_row
                
        # undistort reference points
        if type(ref) is not type(None):
            for row_index, point_set in enumerate(ref):
                new_row = [0 for i in range(0, point_set.shape[0])]
                for cam_number in range(1, cams.shape[0] + 1):
                    offest = cam_number - 2
                    if offest <= 0:
                        index = cam_number
                    else:
                        index = cam_number + offest
                    if cam_number == 1: index = 0
                    while index + 1 < point_set.shape[0]:
                        new_row[index: index + 2] = models[cam_number - 1].undistort_points(np.array([point_set[index],
                                                                                                      point_set[
                                                                                                          index + 1]]).reshape(
                            -1, 1))
                        index += (cams.shape[0] - 1) * 2 + 2
                ref[row_index] = new_row

        preform_wand_caliration(args, unpaired_points, paried_points, ref, wand_interpretable_cams)


#else:
    #pass
