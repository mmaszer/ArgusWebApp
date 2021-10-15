from django.shortcuts import render
import re
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import *
from .argusWand import go
from .graphers import *


def home(request):
    return render(
        request,
        'argus_app/index.html',
    )


def run(request):
    form = request.POST

    has_cams = False
    has_pts = False
    has_ref = False

    fs = FileSystemStorage()

    # save camera file
    if form['cams']:
        cams_file = request.FILES['camsFile']
        cams_file_name = fs.save(cams_file.name, cams_file)
        has_cams = True
    else:
        print('no cams')
        cams_file = None
    
    # save paired points file
    if form['ppts']:
        ppts_file = request.FILES['pptsFile']
        ppts_file_name = fs.save(ppts_file.name, ppts_file)
        uploaded_ppts_url = fs.url(ppts_file_name)
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

    args = {
        'cams': cams_file,
        'intrinsics_opt': form['sel1'],
        'distortion_opt': form['sel2'],
        'paired_points': ppts_file,
        'unpaired_points': uppts_file,
        'scale': form['scale'],
        'reference_points': rpts_file,
        'reference_type': form['rptsType'],
        'recording_frequency': form['recFreq'],
    }

    print(read_file(cams_file_name))
    
    # basically need to initialize a wandgrapher with vals from the form and pass that as the argument into "go"
    # obj = wandGrapher(key, nppts, nuppts, scale, ref, indices, ncams, npframes) 
    # obj = wandGrapher(None, read_file(ppts_file_name), read_file(uppts_file_name), form['scale'], read_file(rpts_file_name), None, read_file(cams_file_name), None, cams = read_file(cams_file_name))
    obj = wandGrapher(None, None, None, None, None, None, None, None, cams = read_file(cams_file_name))

    print(request.POST)

    # TODO: check if there is enough info to run
    if has_cams and has_pts:
        go(args)

    # decide what output to render depending on files given
    case1 = (ppts_file != None) and (uppts_file != None)
    case2 = (ppts_file != None) and (uppts_file == None)
    case3 = (ppts_file == None) and (uppts_file != None)
    case4 = case1 and (rpts_file != None)
    case5 = case1 and (rpts_file == None)
    case6 = case2 and (rpts_file != None)
    case7 = case2 and (rpts_file == None)
    case8 = case3 and (rpts_file != None)
    case9 = case3 and (rpts_file == None)

    if (case1 or case5):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(cams_file.name),
            'pPts': read_file(ppts_file.name),
            'upPts': read_file(uppts_file.name)
            },
        )
    elif (case2 or case7):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(cams_file.name),
            'pPts': read_file(ppts_file.name),
            },
        )
    elif (case3 or case9):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(cams_file.name),
            'upPts': read_file(uppts_file.name)
            },
        )
    elif (case4):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(cams_file.name),
            'pPts': read_file(ppts_file.name),
            'upPts': read_file(uppts_file.name),
            'rpts': read_file(rpts_file.name)
            },
        )
    elif (case6):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(cams_file.name),
            'pPts': read_file(ppts_file.name),
            'rpts': read_file(rpts_file.name)
            },
        )
    elif (case8):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(cams_file.name),
            'upPts': read_file(uppts_file.name),
            'rpts': read_file(rpts_file.name)
            },
        )
    else:
        return HttpResponse("Missing cameras or points")
        # exit function
    

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
