from django.shortcuts import render
import re
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import *
from .argusWand import go
from .graphers import *
from .webGrapher import *
from argus_web_app import settings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import urllib
import csv
from zipfile import ZipFile

# TODO: option to dowload all results as zip, option to download log output, find out if storage overlaps, database, accounts
# TODO: get printed output into log
# TODO: link ref points

'''
Renders the main wand page where points and other information are entered.
'''
def home(request):
    return render(
        request,
        'argus_app/index.html',
    )

'''
Runs the wand processing code and then renders the results page. 
Is called by clicking the "GO" button on the main page.
'''
def run(request):
    form = request.POST

    has_cams = False
    has_pts = False
    has_ref = False

    fs = FileSystemStorage()

    # save camera file
    if form['cams']:
        file = request.FILES['camsFile']
        cams_file_name = fs.save(file.name, file)
        cams_file_path = f"{settings.MEDIA_ROOT}/{cams_file_name}"
        has_cams = True
    else:
        print('no cams')
        cams_file = None
    
    # save paired points file
    if form['ppts']:
        ppts_file = request.FILES['pptsFile']
        ppts_file_name = fs.save(ppts_file.name, ppts_file)
        ppts_file_path = f"{settings.MEDIA_ROOT}/{ppts_file_name}"
        has_pts = True
    else:
        ppts_file = None

    # save unpaired points file
    if form['uppts']:
        uppts_file = request.FILES['upptsFile']
        uppts_file_name = fs.save(uppts_file.name, uppts_file)
        uploaded_uppts_url = fs.url(uppts_file_name)
        has_pts = True
    else:
        uppts_file_name = None
        uppts_file = None
   
    # save ref points file
    if form['rpts']:
        rpts_file = request.FILES['rptsFile']
        rpts_file_name = fs.save(rpts_file.name, rpts_file)
        uploaded_rpts_url = fs.url(rpts_file_name)
    else:
        rpts_file_name = None
        rpts_file = None

    # construct arg object to pass into wand module
    args = {
        'cams': cams_file_path,
        'intrinsics_opt': form['sel1'],
        'distortion_opt': form['sel2'],
        'paired_points': ppts_file,
        'unpaired_points': uppts_file,
        'scale': form['scale'],
        'reference_points': rpts_file,
        'reference_type': form['rptsType'],
        'recording_frequency': form['recFreq'],
    }

    if has_cams and has_pts:
        # process points with wand module and save outputs
        xyzs, outliers_and_indicies = go(args)

        # save xyzs to file
        pointsfile = "static/xyzs.csv"
        with open(pointsfile, 'w') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerows(xyzs)

        # save outliers to file
        pointsfile = "static/outliers.csv"
        with open(pointsfile, 'w') as csvfile: 
            csvwriter = csv.writer(csvfile) 
            csvwriter.writerows(outliers_and_indicies)
        
        # do graphing
        xs = xyzs[:,0]
        ys = xyzs[:,1]
        zs = xyzs[:,2]

        fig = plt.figure()
        ax = fig.add_subplot(projection='3d')

        ax.scatter(xs, ys, zs)

        # save plot
        plt.savefig("static/output.png")
        plt.close()

        # create a ZipFile object
        zipObj = ZipFile('static/all_results.zip', 'w')
        # Add multiple files to the zip
        zipObj.write('static/output.png')
        zipObj.write('static/xyzs.csv')
        zipObj.write('static/outliers.csv')
        zipObj.write('media/console.txt')
        # close the Zip File
        zipObj.close()

        # render results page
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(file.name),
            'pPts': read_file(ppts_file.name),
            'upPts': read_file(uppts_file.name),
            'xyzs': xyzs,
            'o_a_i': outliers_and_indicies,
            'log': read_file("console.txt")
            },
        )
   
    # If some points are missing, generate error message:
    return HttpResponse("Missing cameras or points")
    
'''
Helper function to read files from the media storage.
'''
def read_file(file_name):
    if file_name:
        path = 'media/' + file_name
        f = open(path, 'r')
        file_content = f.read()
        f.close()
        try:
            init_list = file_content.split("\n")
            line_list = [line.split(" ") for line in init_list]
            print(file_name)
            remove_empty_list = []
            for idx, line in enumerate(line_list):
                for idx_2, item in enumerate(line):
                    if not item:
                        remove_empty_list.append(idx)
                    else:
                        line_list[idx][idx_2] = float(item)
            for i in remove_empty_list:
                del line_list[i]
            return line_list
        except ValueError:
            return file_content
