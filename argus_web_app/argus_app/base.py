#!/usr/bin/env python
"""
Python port of ocam calibration routines. This work follows and is 
compatible with omnidirectional camera models from Scaramuzza et al
(2006) and Urban et al (2015).

Scaramuzza et al (2006). A toolbox for easy calibrating omnidirectional cameras.  IROS 2006, Beijing, China.
see also: https://sites.google.com/site/scarabotix/ocamcalib-toolbox/ocamcalib-toolbox-download-page

Urban et al (2015). Improved wide-angle, fisheye and omnidirectional camera calibration, ISPRS Journal of Photogrammetry and Remote Sensing 108:72-79. 
see also: https://github.com/urbste/ImprovedOcamCalib
"""

from __future__ import absolute_import
import logging
import cv2
import numpy as np
import scipy.interpolate
from six.moves import range
FILL_COLOR = (211,160,86) # b,g,r for Carolina Blue
#FILL_COLOR = (0,0,0)


class CMei_model(object):
    def __init__(self,f=600.,width=1440,height=1080,cx=750.,cy=750.,k1=0.,k2=0.,t1=0.,t2=0.,xi=1.):
        """
        Model class for CMei's Omnidirectional model from OpenCV 3.0
        """
        self.f = f # focal length
        self.cx = cx # optical center x
        self.cy = cy # optical center y

        # underlying pinhole model
        self.k1 = k1 # first radial coefficient
        self.k2 = k2 # second radial coefficient
        self.t1 = t1 # first tangential coefficient
        self.t2 = t2 # second tangential coefficient

        self.width = width
        self.height = height

        self.dC = np.array([[k1, k2, t1, t2]])

        # assumes AR = 1
        self.cM = np.zeros((3,3))
        self.cM[0, 0] = f # f
        self.cM[0, 2] = cx
        self.cM[1, 2] = cy
        self.cM[1, 1] = f
        self.cM[2, 2] = 1.

        self.xi = np.array([[xi]])

        # and call the super
        super(CMei_model,self).__init__()

        
    def _from_array(cls,A):

        f = A[0,].astype(np.float32)
        width = int(np.round(A[1,]))
        height = int(np.round(A[2,]))
        cx = A[3,].astype(np.float32)
        cy = A[4,].astype(np.float32)
        k1 = A[5,].astype(np.float32)
        k2 = A[6,].astype(np.float32)
        t1 = A[7,].astype(np.float32)
        t2 = A[8,].astype(np.float32)
        xi = A[9,].astype(np.float32)

        result = cls(f=f,
                     width=width,height=height,
                     cx=cx, cy=cy,
                     k1=k1, k2=k2, t1=t1, t2=t2,
                     xi = xi)
        return result
    from_array = classmethod(_from_array)

    def _from_camera_profile_array(cls,A):

        f = A[1,].astype(np.float32)
        width = int(np.round(A[2,]))
        height = int(np.round(A[3,]))
        cx = A[4,].astype(np.float32)
        cy = A[5,].astype(np.float32)
        k1 = A[7,].astype(np.float32)
        k2 = A[8,].astype(np.float32)
        t1 = A[9,].astype(np.float32)
        t2 = A[10,].astype(np.float32)
        xi = A[12,].astype(np.float32)

        result = cls(f=f,
                     width=width,height=height,
                     cx=cx, cy=cy,
                     k1=k1, k2=k2, t1=t1, t2=t2,
                     xi = xi)
        return result

    from_camera_profile_array = classmethod(_from_camera_profile_array)
        
        
        
        

        



class ocam_model(object):
    def __init__(self,
                 fc=4.,
                 width=1920,height=1440,
                 ss=np.array([0,0,0,0,1],dtype=np.float32),
                 pol=np.array([0,0,0,0,1],dtype=np.float32),
                 c=1.,
                 d=0.,
                 e=0.,
                 xc=960.,
                 yc=720.):
        """
        Follows Scaramuzza (2006)
        width, height is image size
        ss is a 4th order polynomial with r0 leading
        pol is the inverse approximate polynomial
        c,d,e are for an affine transformation
        xc,yc are the image center 
        """
        logging.debug("ocam_model constructor called")
        self.fc = fc
        self.width = width
        self.height = height
        self.ss = ss

        # the following are actually used in my code - DE
        self.pol = pol
        self.c = c
        self.d = d
        self.e = e
        self.xc = xc
        self.yc = yc

        # and call the super
        super(ocam_model,self).__init__()

    def _from_array(cls,A):
        """
        Alternate constructor to read omnidirectional camera from a numpy array
        of shape (13+order) where the coefficients are:
        width,height,c,d,e,cx,cy,ss,pol...
        ss is assumed to be 5 terms
        """
        try:
            assert(len(A)>13)
        except:
            logging.error("bad array passed in argus.ocam.from_array()")

        fc = A[0,].astype(np.float32)
        width = int(np.round(A[1,]))
        height = int(np.round(A[2,]))
        c = A[3,].astype(np.float32)
        d = A[4,].astype(np.float32)
        e = A[5,].astype(np.float32)
        xc = A[6,].astype(np.float32)
        yc = A[7,].astype(np.float32)
        ss = A[8:13].astype(np.float32)
        pol = A[13:,].astype(np.float32)
        result = cls(fc=fc,
                     width=width,height=height,
                     c=c,d=d,e=e,
                     ss=ss,
                     pol=pol,
                     xc=xc,yc=yc)
        return result
    from_array = classmethod(_from_array)

    def _from_csv(cls,S):
        """
        Alternate constructor to read omnidirectional camera from a csv string
        where the csv elements are: fc,width,height,c,d,e,xc,yc,pol...
        """
        A = np.array([float(X) for X in S.strip().split(',')],dtype=np.float32)
        result = cls.from_array(A)
        return result
    from_csv = classmethod(_from_csv)
        
    def to_csv(self):
        """
        provides a comma separated string of the form
        fc,width,height,c,d,e,xc,yc,ss,pol
        """
        L = "{0.fc:1.9f},{0.width:0d},{0.height:0d},{0.c:1.9f},{0.d:1.9f},{0.e:1.9f},{0.xc:1.9f},{0.yc:1.9f},".format(self)+",".join(["{0:1.9f}".format(X) for X in self.ss.tolist()])+","+",".join(["{0:1.9f}".format(X) for X in self.pol.tolist()])
        return L

    def _from_mode(cls,mode):
        """
        Alternate constructor to create omndirectional camera from
        argus.ocam.camera_mode dictionary entry
        """
        S = camera_modes[mode]
        result = cls.from_csv(S)
        return result
    from_mode = classmethod(_from_mode)
        





    def world2cam(self,M):
        """
        Patterned after Scaramuzza (2006) world2cam_fast Matlab routine
        M is a numpy array of shape (3,Npoints).  

        world2cam takes M and projects it into sensor coordinates,
        returning a numpy array of shape (2,Npoints)
        """
        # DENNIS TESTED THIS AND IT SEEMS TO WORK 
        #theta = np.zeros((1,M.shape[1])) # initialize theta
        NORM = np.sqrt((M[0,:]**2.+M[1,:]**2.))

        # the following lines will find scene points along the z-axis
        ind0 = (NORM == 0)
        NORM[ind0] = 1e-9 # to avoid division by zero later
        
        # compute the angle to the point being viewed
        theta = np.arctan2(M[2,:],NORM)
        rho = np.polyval(self.pol,theta)
        # after evaluating Scaramuzza's inverse polynomial,
        # rho is now the distance in pixels of the reprojected points
        # from the image center. 

        # reproject
        x = M[0,:]/NORM*rho
        y = M[1,:]/NORM*rho

        # and add center coordinates / affine transform
        m = np.zeros((2,M.shape[1]))
        m[0,:] = x*self.c + y*self.d + self.xc
        m[1,:] = x*self.e + y        + self.yc
        return(m)



    def cam2world(self,m):
        """
        m is 2,N numpy array of floats
        returns w, 3,N numpy array of floats on the unit sphere that
        are the omnidirectonal 3D coordinates of the optical ray.

        patterned it after Scaramuzza 2008 cam2world.m
        """
        # DENNIS TESTED THIS AND IT SEEMS TO WORK!

        # setup and apply affine transformation
        n_points = m.shape[1]
        A = np.array([[self.c, self.d],[self.e, 1.]])
        T = np.array([[self.xc]*n_points,[self.yc]*n_points])
        m = np.dot(np.linalg.inv(A),m-T)

        # then apply Scaramuzza's omnidirectional camera model
        w = np.zeros((3,n_points))
        w[0,:] = m[0,:]
        w[1,:] = m[1,:]

        # scaramuzza uses getpoint to do this
        rho = np.sqrt(m[0,:]**2.+m[1,:]**2.)
        w[2,:] = np.polyval(self.ss[::-1],rho)

        # normalize coordinates so they have unit length
        w = w/np.linalg.norm(w,axis=0) 
        return(w)












class Undistorter(object):

    def __init__(self,ocam_model,fc=None):
        """
        Creates an undistorter for use with an OCamCalib-type
        Scaramuzza (2006) calibration for fisheye lenses. 

        fc controls how high in z the undistorted image is, 
        and thus controls how much cropping or scooped out 
        edges are seen. 

        This routine creates a grid representing the undistorted world points,
        then projects them to distorted sensor coordinates on the camera using
        world2cam; the maps are then stored for use in reverse order during
        undistortion.
        """
        logging.debug("Undistorter constructor called")
        self.ocam_model = ocam_model
        height = self.ocam_model.height
        width = self.ocam_model.width
        if fc is None:
            fc = self.ocam_model.fc

        # create M 
        M = np.zeros((3,height*width),dtype=np.float32)
        for i in range(height):
            for j in range(width):
                # order as in Scaramuzza!?
                M[0,width*i+j] = float(i) - float(height)/2. 
                M[1,width*i+j] = float(j) - float(width)/2.
                M[2,width*i+j] = -float(width)/float(fc)
        
        # create m warped result
        # for use as a map later
        m = self.ocam_model.world2cam(M).astype(np.float32)
        #print((m,m.shape))
        self.map1 = m[1,:].reshape(height,width) # x
        self.map2 = m[0,:].reshape(height,width) # y
        # NB making these maps may take a while

        # call the super
        super(Undistorter,self).__init__()

    def undistort_frame(self,src,interpolation=None,borderMode=None,borderValue=None):

        """
        uses cv2.remap to undistort a single frame of video
        e.g. for use in DWarp
        """
        #logging.debug("undistort_frame called")
        if interpolation is None:
            interpolation=cv2.INTER_CUBIC # or LANCZOS4
        if borderMode is None:
            borderMode = cv2.BORDER_CONSTANT
        if borderValue is None:
            borderValue = FILL_COLOR
            
        result = cv2.remap(src,
                           self.map1,self.map2,
                           interpolation=interpolation, 
                           borderMode=borderMode,
                           borderValue=borderValue)
        return(result)





class CMeiUndistorter:
    def __init__(self,CMei_model):
        """
        Creates an undistorter using CMei's model from OpenCV 3.0
        CMei's model has the base Pinhole distortion coefficients plus a
        parameter xi to describe the shape of the lens.
        """
        self.model = CMei_model

        # create M, a grid of distorted pixel coordinates
        M = []

        for i in range(-100,self.model.height,5):
            for j in range(-100,self.model.width,5):
                # order as in Scaramuzza!?
                M.append(np.array([float(j),float(i)]))

        self.M = np.array(M)

        self.Md = self.undistort_points(self.M.T).T
        

        self.M = np.array([self.M[i,0] + self.M[i,1]*1j for i in range(len(self.M))])

        self.interpolator = scipy.interpolate.LinearNDInterpolator(self.Md, self.M)
    
        

    def undistort_frame(self,distorted):
        # recommended new camera matrix for undistorting images
        Knew = np.zeros((3,3))
        Knew[0,0] = self.model.width/4.
        Knew[0,2] = self.model.width/2.
        Knew[1,1] = self.model.height/4.
        Knew[1,2] = self.model.height/2.
        Knew[2,2] = 1.

        undistorted = np.zeros_like(distorted)

        return cv2.omnidir.undistortImage(distorted, self.model.cM, self.model.dC, self.model.xi, cv2.omnidir.RECTIFY_PERSPECTIVE, undistorted, Knew)

    def undistort_points(self,pts):
        pts = pts.T

        if len(pts.shape) == 1:
            pts = np.reshape(pts, (1, 1, 2))

            pts = cv2.omnidir.undistortPoints(pts, self.model.cM, self.model.dC, self.model.xi, np.eye(3)).reshape((1, 2))
        else:
            pts = np.reshape(pts, (len(pts), 1, 2))

            pts = cv2.omnidir.undistortPoints(pts, self.model.cM, self.model.dC, self.model.xi, np.eye(3)).reshape((len(pts), 2))
        
        pts[:,0] = pts[:,0]*self.model.f + self.model.cx
        pts[:,1] = pts[:,1]*self.model.f + self.model.cy

        return pts.T

    # double translate for compabititlity with old functions and consistency with Scarmuzza undistort
    """
    argus.ocam.distort_pts:
    Takes:
        - pts: (2,n) array where the first row is x and the second y in unnormalized pixel coordinates
    Returns:
        - distorted_pts: (2,n) array of distorted formated as the inputted arrays
    """
    def distort_points(self, pts):
        pts = pts.T

        pts = self.interpolator(pts)
        ret = np.zeros((len(pts), 2))

        ret[:,0] = np.real(pts)
        ret[:,1] = np.imag(pts)

        return ret.T
        

    def distort_points_old(self, pts):
        pts = pts.T

        rvec = np.reshape(np.array([[1,0,0],[0,1,0],[0,0,1]], np.float32), (3, 1, 3))

        #print(rvec)
        tvec = np.array([0,0,0], np.float32) # translation vector

        # normalize the points
        pts[:,0] = (pts[:,0] - self.model.cx)/self.model.f
        pts[:,1] = (pts[:,1] - self.model.cy)/self.model.f


        p = np.hstack((pts, np.tile(0.5,(pts.shape[0],1)))).astype(np.float32)

        p = np.reshape(p, (p.shape[0], 1, 3))
        ret, _ = cv2.omnidir.projectPoints(p, rvec, tvec, self.model.cM, self.model.xi, self.model.dC)
        
        ret = np.reshape(ret, pts.T.shape)

        #print((ret.shape, self.model.cx, self.model.cy))

        #ret[:,0] = (ret[:,0] - self.model.cx)
        #ret[:,1] = (ret[:,1] - self.model.cy)

        return ret







class PointUndistorter(object):

    def __init__(self,ocam_model,fc=None):
        """
        Creates a point undistorter for use with an OCamCalib-type
        Scaramuzza (2006) calibration for fisheye lenses. 

        fc controls how high in z the undistorted image is, 
        and thus controls how much cropping or scooped out 
        edges are seen. 

        This is like Undistorter but skips the grid creation
        to speed it up
        """
        logging.debug("PointUndistorter constructor called")
        self.ocam_model = ocam_model
        height = self.ocam_model.height
        width = self.ocam_model.width
        if fc is None:
            fc = self.ocam_model.fc

        # DO NOT create M 
        # DO NOT create m warped result
        # for use as a map later

        # call the super
        super(PointUndistorter,self).__init__()
        
    def undistort_points(self,cam1):
        """
        cam1 is a (2,N) numpy array of floats with uv pixel coordinates
        returns a (2,N) numpy array of undistorted uv pixel coordinates
        patterned after Pranav's undistort_pixel.m 
        """
        # check for nans
        ind = np.isnan(cam1)

        # routine uses yx not xy!
        yx = np.zeros((2,cam1.shape[1]),dtype=np.float32)
        yx[0,:] = cam1[1,:].astype(np.float32)
        yx[1,:] = cam1[0,:].astype(np.float32)
        M = self.ocam_model.cam2world(yx)

        # scale back
        width = self.ocam_model.width
        height = self.ocam_model.height
        fc = self.ocam_model.fc
        M[0,:] = M[0,:]/M[2,:]#*(-width/fc)
        M[1,:] = M[1,:]/M[2,:]#*(-width/fc)
        M[2,:] = M[2,:]/M[2,:]#*(-width/fc)
        M = M * float(-width)/float(fc)

        # re-center
        und_points = np.zeros((2,cam1.shape[1]),dtype=np.float32)
        und_points[0,:] = M[1,:]+float(width)/2.
        und_points[1,:] = M[0,:]+float(height)/2.
        und_points[ind] = np.nan
        return(und_points)

    def distort_points(self, uv):
        M = np.zeros((3,uv.shape[1]),dtype=np.float32)
        M[0,:] = uv[1,:]-np.float32(self.ocam_model.height)/2.
        M[1,:] = uv[0,:]-np.float32(self.ocam_model.width)/2.
        M[2,:] = -np.float32(self.ocam_model.width)/np.float32(self.ocam_model.fc)
        m = self.ocam_model.world2cam(M).astype(np.float32)

        result = np.zeros((2,uv.shape[1]),dtype=np.float32)
        result[0,:] = m[1,:] # x
        result[1,:] = m[0,:] # y
        return(result)



























# Cameras are specified here. 
# camera_modes is used in the from_mode alternate constructor to
# return an ocam_model instance for each mode; for Python convenience, the 
# names (tweaked to be valid python identifiers) are also exposed 
# as convenience functions that return an instance of the appropriate 
# ocam_model. 
camera_modes = dict()


# the models here have extended pol 9th order polynomials obtained using
# Urban et al 2015 modifications to Scaramuzza et al 2006.











camera_modes['GoPro-Hero4 Black-1440p-80fps-wide']='4,1920,1440,0.999938379179311,-0.016187871855188,0.016810280637347,718.4445375924397,977.1355515393601,-8.477755708037934e2,0,0.000003883048139e2,-0.000000001510688e2,0.000000000000937e2,0.023985653458955e3,0.203838160012703e3,0.734981309550883e3,1.410692016597674e3,1.452954876183546e3,0.695737475972601e3,0.173495542578852e3,1.092192190554513e3,1.509061883254690e3'
def GoPro_Hero4Black_1440p_80fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-1440p-80fps-wide')

camera_modes['GoPro-Hero4 Black-2.7k-60fps-wide']='4,2704,1520,0.999289595465724,-0.006963540857230,0.007533029275197,7.669108374384379e+02,1.352406563245692e+03,-1.234767106495970e3,0,0.000000233157305e3,-0.000000000021227e3,0.000000000000014e3,0.003495935840111e3,-0.000934751560414e3,-0.079964826002906e3,-0.160849381110099e3,0.072387040959304e3,1.641972973579676e3,2.202560631107756e3'
def GoPro_Hero4Black_27k_60fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-2.7k-60fps-wide')

camera_modes['GoPro-Hero4 Black-4k-30fps-wide']='4,3840,2160,0.999855446730588,-0.007072428051427,0.007617267596385,1.088937028247496e+03,1.920792960011589e+03,-1.750339352554267e3,0,0.000000156358120e3,-0.000000000000341e3,0.000000000000001e3,0.012712262204542e3,0.092259347275331e3,0.377119290809140e3,0.901910976373143e3,2.835853284356173e3,3.250686093619848e3'
def GoPro_Hero4Black_4k_30fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-4k-30fps-wide')

camera_modes['GoPro-Hero4 Black-2.7k4:3-30fps-wide']='5.8,2704,2028,1.002479612109967,-0.002436317109822,0.003442834555677,9.999567386181384e+02,1.374413779158510e+03,-1.186451177097442e3,0,0.000000248481215e3,-0.000000000042082e3,0.000000000000027e3,0.027027547457438e3,0.204554974397187e3,0.602623784593015e3,0.824181901959244e3,0.477441395049410e3,0.148197002949612e3,1.446621729059608e3,2.067405921832096e3'
def GoPro_Hero4Black_27k43_30fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-2.7k4:3-30fps-wide')

camera_modes['GoPro-Hero4 Black-1080p-30fps-wide']='4,1920,1080,1.007781524689579,-0.003542483075365,0.003742925400506,5.313744653721496e+02,9.760901992270241e+02,-8.782338276361955e2,0,0.000003102319339e2,0.000000000032907e2,0.000000000000103e2,0.005078009041660e3,0.032201672029899e3,0.134345783049311e3,0.351984725390143e3,1.334363515806159e3,1.600733049338611e3'
def GoPro_Hero4Black_1080p_30fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-1080p-30fps-wide')

camera_modes['GoPro-Hero4 Black-960p-60fps-wide']='5,1280,960,0.999446991404943,-0.001094974428309,0.001149761071764,4.726683719824036e+02,6.506339006993075e+02,-5.612277003834659e2,0,0.000004846941429e2,0.000000000028547e2,0.000000000000354e2,0.003928536711933e3,0.025801577482894e3,0.103206799918244e3,0.255378726383932e3,0.880152554349658e3,1.032908332215831e3'
def GoPro_Hero4Black_960p_60fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-960p-60fps-wide')

camera_modes['GoPro-Hero4 Black-720p-60fps-wide']='4,1280,720,0.999772046685620,0.002911897081038,-0.002638157541992,3.517153276518804e+02,6.508131998317431e+02,-5.839327530779753e2,0,0.000004546856744e2,0.000000000271871e2,0.000000000000303e2,0.004564589316356e3,0.025087086078785e3,0.088378251137011e3,0.220820620779890e3,0.873586671326510e3,1.060824939018812e3'
def GoPro_Hero4Black_720p_60fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-720p-60fps-wide')

camera_modes['GoPro-Hero4 Black-WVGA-240fps-wide']='4,848,480,1.006134958833511,-3.294295058161427e-04,5.270098550859433e-04,2.355247543774561e+02,4.308256491888478e+02,-3.874821106938145e2,0,0.000007030006369e2,0.000000000073133e2,0.000000000001439e2,0.016660776634262e2,0.102341271571253e2,0.485609841775483e2,1.413458342092289e2,5.800891528406308e2,7.042820095894670e2'
def GoPro_Hero4Black_WVGA_240fps_wide():
    """Dylan Ray collected cal information, July 2015"""
    return ocam_model.from_mode('GoPro-Hero4 Black-WVGA-240fps-wide')

camera_modes['GoPro-Hero3 Black-720p-60fps-wide']='4,1280,720,1.038962477337479,0.011039937655688,-0.010160134900257,3.495968049386204e+02,6.551208185430136e+02,-5.964860064092100e2,0,0.000006317642603e2,-0.000000002252898e2,-0.000000000000015e2,0.031410779538021e3,0.262278344036545e3,0.938094763439947e3,1.923855551044671e3,2.568702786546738e3,2.335637424609530e3,1.936382148401258e3,1.294290018279926e3'
def GoPro_Hero3Black_720p_60fps_wide():
    return ocam_model.from_mode('GoPro-Hero3 Black-720p-60fps-wide')

camera_modes['GoPro-Hero3 Black-1080p-30fps-wide']='4,1920,1080,1.021048672884161,0.050700641021834,-0.050174135405367,5.046272334476868e+02,9.595023792225445e+02,-8.756988129568118e2,0,0.000004379234206e2,-0.000000001157497e2,-0.000000000000005e2,0.046748122943091e3,0.436803624621165e3,1.798819969519065e3,4.277870045493782e3,6.535992531565245e3,6.841467269249026e3,5.071131915877356e3,3.380384896639794e3,1.984422499996136e3'
def GoPro_Hero3Black_1080p_30fps_wide():
    return ocam_model.from_mode('GoPro-Hero3 Black-1080p-30fps-wide')

camera_modes['GoPro-Hero3 Black-2.7k-30fps']='4,2704,1524,1.010103664726166,0.027626104226261,-0.026842379879826,7.154242361854845e+02,1.378448922157604e+03,-1.261953803099550e3,0,0.000000314144462e3,-0.000000000078517e3,0.000000000000014e3,0.018207972798881e3,0.109900472073467e3,0.378600161566831e3,0.995200359638239e3,1.681133481617615e3,2.745646702683811e3,2.494533139909354e3'
def GoPro_Hero3Black_27k_30fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-2.7k-30fps')

camera_modes['GoPro-Hero3 Black-2.7kcin-24fps']='4.8,2704,1440,1.010142699965713,0.056189072228797,-0.055428359998263,6.719627349026216e+02,1.348111096592302e+03,-1.181168011225933e3,0,0.000000353352763e3,-0.000000000133837e3,0.000000000000045e3,-0.010915494583628e3,-0.097138619196201e3,-0.440136716295501e3,-1.121502230469040e3,-1.480040734347465e3,-0.754150026997637e3,1.352944119973815e3,2.069996305321981e3'
def GoPro_Hero3Black_27kcin_24fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-2.7kcin-24fps')

camera_modes['GoPro-Hero3 Black-4k-15fps']='4,3840,2160,1.001151494453641,0.038094926574890,-0.037901447244133,1.002377931339334e+03,1.953556340432706e+03,-1.791690890781179e3,0,0.000000202331087e3,-0.000000000016437e3,-0.000000000000003e3,0.014726715326858e4,0.136554923644694e4,0.554387714551459e4,1.292957564207057e4,1.922002588130750e4,1.924512900717616e4,1.330366650807437e4,0.782923639349421e4,0.418149398196921e4'
def GoPro_Hero3Black_4k_15fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-4k-15fps')

camera_modes['GoPro-Hero3 Black-4kcin-12fps']='4.5,4096,2160,1.000303083861387,0.053757474022190,-0.054021727863310,1.003594159571279e+03,2.042792490105998e+03,-1.790873060476198e3,0,0.000000207063480e3,-0.000000000019161e3,-0.000000000000003e3,0.038421375060623e4,0.377984221587008e4,1.645626828732992e4,4.173878402843500e4,6.827934778214506e4,7.539572241611399e4,5.735719261133632e4,3.019832887177926e4,1.237259074829096e4,0.476257082225256e4'
def GoPro_Hero3Black_4kcin_12fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-4kcin-12fps')

camera_modes['GoPro-Hero3 Black-1440p-48fps']='4,1920,1440,1.000263727706387,0.036457567337562,-0.036141151593174,6.859483202825369e+02,9.575118816472882e+02,-8.574307917841457e2,0,0.000004533399186e2,-0.000000001373757e2,0.000000000000142e2,0.040823980616434e3,0.367763767761128e3,1.464252736627781e3,3.379714599070690e3,5.051762641847280e3,5.270502471520158e3,4.011903355856420e3,2.938078150796307e3,1.877678532184093e3'
def GoPro_Hero3Black_1440p_48fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-1440p-48fps')

camera_modes['GoPro-Hero3 Black-960p-48fps']='4,1280,960,0.999984821016412,0.035932434111839,-0.035631399978587,4.575550574978913e+02,6.399138833590620e+02,-5.729749714788942e2,0,0.000007122657255e2,-0.000000004471922e2,0.000000000001889e2,-0.015543967682837e3,-0.103262099145795e3,-0.287575708562884e3,-0.383356933536081e3,-0.073757842138703e3,0.494647199061879e3,1.192731341254540e3,1.135360273770770e3'
def GoPro_Hero3Black_960p_48fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-960p-48fps')

camera_modes['GoPro-Hero3 Black-WVGA-120fps']='4,848,480,1.009032072040352,0.040311274198631,-0.039391290447238,2.246529853797306e+02,4.260655495716827e+02,-3.889177785982952e2,0,0.000009923934804e2,-0.000000006709810e2,0.000000000002219e2,0.015936841496895e3,0.109263579553096e3,0.346182259433937e3,0.678975611817417e3,0.857007565813106e3,1.010455834950723e3,0.802126886658310e3'
def GoPro_Hero3Black_WVGA_120fps():
    return ocam_model.from_mode('GoPro-Hero3 Black-WVGA-120fps')


camera_modes['ActionCam-H9-1080p-30fps']='4,1920,1080,0.999854689244271,0.006039470047409,-0.004776819128516,5.242638014159094e+02,9.590150550206747e+02,-1.005310512037270e3,0,0.000000348918644e3,-0.000000000004554e3,0.000000000000037e3,0.005595347326982e3,0.047498167614197e3,0.161276854300408e3,0.262887171990382e3,0.179791054033711e3,0.999950819161824e3,1.534247851374442e3'
def ActionCam_H9_1080p_30fps():
    return ocam_model.from_mode('ActionCam-H9-1080p-30fps')

camera_modes['ActionCam-H9-1080p-60fps']='4,1920,1080,1.001227705096788,0.005523761907110,-0.005751736615236,5.285802632069510e+02,9.599193885974470e+02,9.999018448683032e2,0,0.000003375410384e2,0.000000000283223e2,0.000000000000120e2,-0.006806073728541e3,-0.025146665435800e3,0.006760692135450e3,0.138169180938363e3,0.196687625418609e3,1.074908527964842e3,1.559266495563065e3'
def ActionCam_H9_1080p_60fps():
    return ocam_model.from_mode('ActionCam-H9-1080p-60fps')
