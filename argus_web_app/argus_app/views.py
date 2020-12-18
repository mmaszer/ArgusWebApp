from django.shortcuts import render
import re
from datetime import datetime
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .models import *
# from .argusWand import *

def home(request):
    #return HttpResponse("Hello, Django!")
    return render(
        request,
        'argus_app/index.html',
    )

def run(request):
    form = request.POST
    #if request.method == 'POST' and request.FILES['camsFile']:
    
    # if !isinstance(form.scale, int) && !isinstance(form.scale, float):

    hasCams = False
    hasPts = False

    fs = FileSystemStorage()
    # save camera file
    if (len(form['cams']) > 0):        
        camsFile = request.FILES['camsFile']
        camsFileName = fs.save(camsFile.name, camsFile)
        uploaded_cams_url = fs.url(camsFileName)
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

    
    #args = [camsFile, form['sel1'], form['sel2'], pptsFile, upptsFile, form['scale'], rptsFile, form['rptsType'], form['recFreq']]
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

    #print(read_file(filename))
    #print(read_file(args[3].name))
    print(request.POST)

    #argus-wand.go(args)

    return render(
        request,
        'argus_app/results.html',
        { 
        'args': args,
        'camPts': read_file(camsFile.name)
        },
    )

def read_file(request):
    path = 'media/' + request
    f = open(path, 'r')
    file_content = f.read()
    f.close()
    return file_content

def hello_there(request):
    return render(
        request,
        'argus_app/index.html',
    )