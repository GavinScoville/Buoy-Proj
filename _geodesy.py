#Arclength Distance Two Points: 
#look into updating with Haversine formula later 
#Let's do this the right way, with vectors n planes. 
#https://www.movable-type.co.uk/scripts/latlong-vectors.html source for math


#I need more math background to derive the coreolis effect 
#The PDE's of coeolis effect and current interacitons have me mind boggled.
#this is somehting I need to come back to.

#for now, no coreolis effect, just great circle path  


import math 
import numpy as np
R = 6371000 #Radius of the earth(m)
Omega = 7.2921159e-5 #earths rotation rate in rad/s

def arclength(North1, West1, North2, West2):
    
    phi1 = math.radians(North1) #radians
    phi2 = math.radians(North2)
    lambda1= math.radians(-West1) #negative becasue its anti-east
    lambda2= math.radians(-West2)

    x1 = math.cos(phi1) * math.cos(lambda1) #convert to xyz
    y1 = math.cos(phi1) * math.sin(lambda1)
    z1 = math.sin(phi1)

    x2 = math.cos(phi2) * math.cos(lambda2)
    y2 = math.cos(phi2) * math.sin(lambda2)
    z2 = math.sin(phi2)
    


    dot = x1 * x2 + y1 * y2 + z1 * z2 #dot product 

    Gx = y1*z2-z1*y2 #point one cross point two 
    Gy = z1*x2-x1*z2 #gives us the great cicle plane between the two points 
    Gz = x1*y2-y1*x2
    m_cross = math.sqrt(Gx**2+Gy**2+Gz**2)

    d = R * math.atan2(m_cross,dot) #use atan2 so it's not sensitive to edge cases. 
    return d
d=arclength(49.903, 145.246, 48.493, 124.727) #ocean papa to neah bay 



def azimuth(North1, West1, North2, West2):
    # convert to radians
    phi1 = math.radians(North1) #radians
    phi2 = math.radians(North2)
    lambda1= math.radians(-West1) #negative becasue its anti-east
    lambda2= math.radians(-West2)

    x1 = math.cos(phi1) * math.cos(lambda1) #convert to xyz
    y1 = math.cos(phi1) * math.sin(lambda1)
    z1 = math.sin(phi1)

    x2 = math.cos(phi2) * math.cos(lambda2)
    y2 = math.cos(phi2) * math.sin(lambda2)
    z2 = math.sin(phi2)


    Gx = y1*z2-z1*y2 #point one cross point two 
    Gy = z1*x2-x1*z2 #gives us the great cicle plane between the two points 
    Gz = x1*y2-y1*x2

    Nx = y1 #so point one cross north vector
    Ny = -x1 #gives us a plane that goes through the North pole
    Nz = 0

    GNx = Nz*Gy-Ny*Gz #this formla is beautiful 
    GNy = Nx*Gz-Nz*Gx #were talking the amount of area outlined by the parallelgram of these two planes normal vectors 
    GNz = Ny*Gx-Nx*Gy #parallel to the interseciton of the two great circles

    cross_m = math.sqrt(GNx**2+GNy**2+GNz**2) #magnitude of cross product
    NG_dot_a = x1*GNx+y1*GNy+z1*GNz 
    sintheta = cross_m * NG_dot_a/math.sqrt(NG_dot_a**2) #the sign of NG_dot_a
    costheta = Nx*Gx+Ny*Gy+Nz*Gz 
    bearing = math.degrees(math.atan2(sintheta, costheta))
    return bearing

def cartesian(North1, East1):
    phi1 = math.radians(North1)
    lambda1= math.radians(East1)
    x1 = math.cos(phi1) * math.cos(lambda1) #convert to xyz
    y1 = math.cos(phi1) * math.sin(lambda1)
    z1 = math.sin(phi1)
    cart=np.array([x1,y1,z1])
    return cart






