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

    hasCams = False
    hasPts = False
    hasRef = False

    fs = FileSystemStorage()

    # save camera file
    if (len(form['cams']) > 0):        
        camsFile = request.FILES['camsFile']
        camsFileName = fs.save(camsFile.name, camsFile)
        hasCams = True
    else:
        print('no cams')
        camsFile = None
    
    # save paired points file
    if (len(form['ppts']) > 0):
        pptsFile = request.FILES['pptsFile']
        pptsFileName = fs.save(pptsFile.name, pptsFile)
        uploaded_ppts_url = fs.url(pptsFileName)
        hasPts = True
    else:
        pptsFile = None

    # save unpaired points file
    if (len(form['uppts']) > 0):
        upptsFile = request.FILES['upptsFile']
        upptsFileName = fs.save(upptsFile.name, upptsFile)
        uploaded_uppts_url = fs.url(upptsFileName)
        hasPts = True
    else:
        upptsFile = None
   
    # save ref points file
    if (len(form['rpts']) > 0):
        rptsFile = request.FILES['rptsFile']
        rptsFileName = fs.save(rptsFile.name, rptsFile)
        uploaded_rpts_url = fs.url(rptsFileName)
    else:
        rptsFile = None

    args = {
        'cams': camsFile,
        'intrinsics_opt': form['sel1'],
        'distortion_opt': form['sel2'],
        'paired_points': pptsFile,
        'unpaired_points': upptsFile,
        'scale': form['scale'],
        'reference_points': rptsFile,
        'reference_type': form['rptsType'],
        'recording_frequency': form['recFreq'],
    }

    

    # decide what output to render depending on files given
    case1 = (pptsFile != None) and (upptsFile != None)
    case2 = (pptsFile != None) and (upptsFile == None)
    case3 = (pptsFile == None) and (upptsFile != None)
    case4 = case1 and (rptsFile != None)
    case5 = case1 and (rptsFile == None)
    case6 = case2 and (rptsFile != None)
    case7 = case2 and (rptsFile == None)
    case8 = case3 and (rptsFile != None)
    case9 = case3 and (rptsFile == None)

    if (case1 or case5):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(camsFile.name),
            'pPts': read_file(pptsFile.name),
            'upPts': read_file(upptsFile.name)
            },
        )
    elif (case2 or case7):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(camsFile.name),
            'pPts': read_file(pptsFile.name),
            },
        )
    elif (case3 or case9):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(camsFile.name),
            'upPts': read_file(upptsFile.name)
            },
        )
    elif (case4):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(camsFile.name),
            'pPts': read_file(pptsFile.name),
            'upPts': read_file(upptsFile.name),
            'rpts': read_file(rptsFile.name)
            },
        )
    elif (case6):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(camsFile.name),
            'pPts': read_file(pptsFile.name),
            'rpts': read_file(rptsFile.name)
            },
        )
    elif (case8):
        return render(
            request,
            'argus_app/results.html',
            { 
            'args': args,
            'camPts': read_file(camsFile.name),
            'upPts': read_file(upptsFile.name),
            'rpts': read_file(rptsFile.name)
            },
        )
    else:
        return HttpResponse("Missing cameras or points")
        # exit function

    

def read_file(request):
    path = 'media/' + request
    f = open(path, 'r')
    file_content = f.read()
    f.close()
    return file_content
