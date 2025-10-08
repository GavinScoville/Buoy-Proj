#Arclength Distance Two Points: 
#look into updating with Haversine formula later 
#Let's do this the right way, with vectors n planes. 
#https://www.movable-type.co.uk/scripts/latlong-vectors.html source for math

import math
R = 6371000 #Radius of the earth(m)

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
    m_cross = sqrt(Gx**2+Gy**2+Gz**2)

    d = R * math.atan2(m_cross,dot) #use atan2 so it's not sensitive to edge cases. 

    print(f"arc length: {d:.2f} meters") #formatting a number neatly in a string using f-strings
    return d
d=arclength(49.903, 145.246, 748.493, 124.727) #ocean papa to neah bay 
s=9.81/(2* math.pi)*13  #wavespeed= g/2pi* Period
d/(s*60**2) # hours from Ocean Papa to Neeah Bay 

def azimuth(North1, West1, North2, West2):
    # convert to radians
    phi1 = math.radians(North1) #radians
    phi2 = math.radians(North2)
    lambda1= math.radians(-West1) #negative becasue its anti-east
    lambda2= math.radians(-West2)

    x1 = R * math.cos(phi1) * math.cos(lambda1) #convert to xyz
    y1 = R * math.cos(phi1) * math.sin(lambda1)
    z1 = R * math.sin(phi1)

    x2 = R * math.cos(phi2) * math.cos(lambda2)
    y2 = R * math.cos(phi2) * math.sin(lambda2)
    z2 = R * math.sin(phi2)

    Nx = y1 #so point one cross north vector
    Ny = -x1 #gives us a plane that goes through the North pole
    Nz = 0

    Gx = y1*z2-z1*y2 #point one cross point two 
    Gy = z1*x2-x1*z2 #gives us the great cicle plane between the two points 
    Gz = x1*y2-y1*x2

    NGx = Ny*Gz-Nz*Gy #this formla is beautiful 
    NGy = Nz*Gx-Nx*Gz #were talking the amount of area outlined by the parallelgram of these two planes normal vectors 
    NGz = Nx*Gy-Ny*Gx #parallel to the interseciton of the two great circles



    east = math.sqrt(NGx**2+NGy**2+NGz**2) #the amount to the East of point A 
    north= Nx*Gx+Ny*Gy+Nz*Gz # the amount North of point A 
    print(east)
    print(north)
    theta = math.degrees(math.atan2(north, east))
    print(f"azimuth from A>B is{theta:.2f}degrees")
    return(theta)

azimuth(49.903, 145.246, 49.903, 124.727) 
azimuth(49.903, 145.246, 748.493, 124.727) 

# Example: Seattle (47.6062°N, 122.3321°W) to Honolulu (21.3069°N, 157.8583°W)
print(arclength(47.6062, -122.3321, 21.3069, -157.8583))

azimuth(47.6062, -122.3321, 21.3069, -157.8583)