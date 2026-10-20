import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import copy
from matplotlib import cm
import time
from _fetch_buoy_functions import fetch_and_clean_buoy_data

from _3d_visualisation import plot_surf_3d

#this script runs an airy wave model as an approx. for ocean waves on a set map from a specific direction.

start = time.time() #to measure the amount of time it takes to run

def init_from_buoy(buoy_id="46087"):
    try:
        df = fetch_and_clean_buoy_data(buoy_id)
        if df is None or df.empty:
            raise ValueError("Empty dataframe")
        for idx in range(len(df) - 1, -1, -1):
            row = df.iloc[idx]
            h = row.get('WVHT') if 'WVHT' in row.index else None
            T = row.get('DPD') if 'DPD' in row.index else None
            direction = row.get('MWD') if 'MWD' in row.index else None
            if pd.notna(h) and pd.notna(T) and pd.notna(direction):
                h, T, direction = float(h), float(T), float(direction)
                print(f"✓ Loaded from buoy {buoy_id}: h={h:.2f}m, T={T}s, dir={direction}°")
                return {'h': h, 'T': T, 'direction': direction}
        raise ValueError("No valid wave data in dataframe")
    except Exception as e:
        print(f"⚠ Failed to fetch buoy data ({e}), using defaults")
        return {'h': 2.0, 'T': 12.0, 'direction': 60.0}

buoy_params = init_from_buoy(buoy_id="46087")
h = buoy_params['h']
T = buoy_params['T']
wave_direction = buoy_params['direction']

#only adding this for a beta test preview: 
h= 2.2
T = 9 
wave_direction = 282
#It loads a npy file of bathymetry 
#It loads sea state data 
#You add some of the parameters to the numerical model 
#the model runs
#the output is a surf map and a 3d model of the specific surf break of your choosing
#It is designed this way so I can itterativly build new surfmodels without crashing the whole website 

#To do: 
#improve efficency 
#add metadata of wind conditions on top of graphics 

# this is an array of bathymetric data 
depth = np.load("data/the_dump.npy")
zoom = depth[450:700,500:750] #this is for the closeup window 

dx = 10 #set the discrete spatial stepsize. this is what the grid spacing really is

c = 9.8*T/(2*np.pi) #define the wave speed in terms of meters/sec
L = c*T #set the length of wave (m)
dt = .7*dx/c   #choose a timestep that satisfies c where c is the max(c)
st = 0 #sum of all time elapsed

nsteps = 2000 #set the number of time steps
land = depth >= 0 #depth more than 0
near_shore = -L/2 <= depth  #just going to make the dampening a coefficient turn on when it gets close?

x = np.arange(0,depth.shape[1]*dx,dx) #define an array to store x position data
y = np.arange(0,depth.shape[0]*dx,dx) #define an array to store y position data
f = np.zeros((len(y),len(x),3)) #starting with no waves 

#we controll the celarity using these three equaitons for deep, medium, and shallow waters
celarity= np.full((len(y),len(x)),c)
celarity = np.sqrt((9.8 / (2 * np.pi / L)) * np.tanh(np.abs(depth)*2 * np.pi / L))  # phase speed
celarity = np.nan_to_num(celarity, nan = 0.0)
celarity = np.clip(celarity,np.sqrt(9.8*np.abs(depth)),c)# but don't let the celarity} become lower then shallow water or higher then deepwater approx
dt = .5*dx/np.max(celarity) #smaller steps should make it more stable 

#the following is purely for generaiting the waveform for each inlet:
#I htink there is a fancy way to do this with eigenvalues and   vectors and angular frequecies but i am just going to do this the simple way that makes sence ot me:

wave_form = np.sin(np.arange(nsteps)*dt * 2*np.pi / T) * h/2 #do I need to incorperate dt here? 
ang_v= 2*np.pi/T #radians/cycles * cycles/sec = radians/sec 
ang_wavenumber = 2*np.pi/L #radians/meter 

y_wave = np.arange(len(y),0,-1) * dx
x_wave = np.arange(len(x),0,-1) * dx
t = np.arange(nsteps) * dt

#when I come back, I haveto hammer out how to robustly convert
# wave direction to my plain wave form
# which requires taking the direciton vector and applying a transfomation to it
# which then produces a drieciton vector in radians
#which then can be used to compute the direcitons of wave propogaiton in my positive x= east positve y=north 
#coord system

azy=[-np.sin(np.deg2rad(wave_direction)),-np.cos(np.deg2rad(wave_direction))]
k=0
#I think I could also have used a meshgrid here instead of htis style of array
plain_wave = h * np.sin(
    x_wave[None, :] * ang_wavenumber * azy[0] #x meter * the radians/meter* x value of direciton vector
    + y_wave[:, None] * ang_wavenumber * azy[1] #y meters * the radiauns pr meter * y value of direciton vector
    - k*dt * 2*np.pi / T)

#this is my rudementaryway to control which edges are energised :
trans_edge = np.zeros_like(plain_wave, dtype=bool) #this is cool, start them all false, and then fill in the true 
recieve_edge = np.zeros_like(plain_wave, dtype=bool)
one_wave = 5*int(np.ceil(L / dx)) #how many boxes are a part of the wavelength


if(azy[0]>=0):
    recieve_edge[:, -one_wave:] = True #and opposite side, for one wavelength is reciever
    trans_edge[:, 0] = True #if x is positive, then the west is turned on

if(azy[0]<=0): #if x is negative, then the east is turned on
    trans_edge[:,-1] = True 
    recieve_edge[:, :one_wave] = True
    signal_release = len(x)*dx - c * azy[0] * st

if(azy[1]>0):
    trans_edge[0, :] = True #if y is positive, then the south side is turned on 
    recieve_edge[-one_wave:, :] = True
    signal_release = c * azy[1] * st

if (azy[1]<0):
    trans_edge[-1, :] = True # if y is negative, then the north side is turned on
    recieve_edge[:one_wave, :] = True
    signal_release = len(y)*dx - c * azy[1] * st

#we then toggel dampening, which is inversly related to wavelngth/depth but could use some tuning
dampening = .05 * L/(depth**2) 
dampening = np.clip(dampening,0,1)
dampening[recieve_edge]= .5 #this sill hopefullyu dampen the wave on the recieving edges 
dampening[land]= .5 #ok so this should stop any movement of waves onto the land 
dampening = np.nan_to_num(dampening, nan = 0.0)

#if we want the transmitting edge to only release at the corner and then expand to the left and right at the rate of celarity[x] celarity[y]
# so we could redefine the trans edge to be only the trans edge releasing. but this requires us 
# to call on funcitons to process two more matrixes per loop
# or we could just have another boolian mask for a vector x and a vector y
# which allows us to slowly release the trans edge is we can figuure out how to make a 
# logic which uncovers the mask only if trans_edge = T and x_signal release = T 

#speed in the x direction: ang_wavenumber * azy[0]
#speed in the y direciton: ang_wavenumber * azy[1]
#for x axis: start at one edge, propogate the other way. 
#if azy >1, start at 0 go up
#if azy<1, start at length(x) and go down


#could the whole thing be computaitonally reducable if i knew more about laplacer tranform? 

# if waves are comming from multiple sides, how do I decide which edge to dampen and which edge to not? 
# I could start with initial condition: all deep water has wave form upon it
#and all deep water edges are active. 
#for now I dont need to worry about this I suppose. 


def x_signal_release(
        st=st,
        x=x,
        azy=azy,
        c=c):
    x_signal = np.zeros_like(x, dtype=bool)
    x_signal[:np.int_(np.round(c * azy[0] * st)/dx)]=True

    return(x_signal)

x_signal_release(st=20)
x_signal_release(st=-20)




#celarity(x) s 


plt.imshow(plain_wave, origin="lower", cmap="viridis_r",vmin=0, vmax=h)
plt.colorbar()
        #ax = fig.add_subplot(projection = '3d')
plt.title('wave direction= %0.2f ' % (wave_direction) )
        #ax.set_zlim3d(-5,5)       
plt.pause(.1)#can make this dt 
plt.show()

setup_time = time.time() - start
loop_start = time.time() #adding time marker for optimising for loop 

#np.shape(celarity[1:-1,1:-1]**2)
#celarity[1:-1,1:-1]**2*(f[:-2,1:-1, 1]+f[2:,1:-1,1]-2.*f[1:-1,1:-1,1])
#f[1:-1,1:-1, 1] = f[1:-1,1:-1, 0] + .5*celarity[1:-1,1:-1]**2*(f[:-2,1:-1, 0]+f[2:,1:-1,0]-2.*f[1:-1,1:-1,0])*(dt**2/dx**2)\
#                                  + .5*celarity[1:-1,1:-1]**2*(f[1:-1,:-2, 0]+f[1:-1,2:,0]-2.*f[1:-1,1:-1,0])*(dt**2/dx**2)

#first time step in the leap frog algorithm
f[1:-1,1:-1, 1] = f[1:-1,1:-1, 0] + .5*c**2*(f[:-2,1:-1, 0]+f[2:,1:-1,0]-2.*f[1:-1,1:-1,0])*(dt**2/dx**2)\
                                  + .5*c**2*(f[1:-1,:-2, 0]+f[1:-1,2:,0]-2.*f[1:-1,1:-1,0])*(dt**2/dx**2)

#for all additional time steps
for k in range(0,nsteps):

    plain_wave = h * np.sin(
    x_wave[None, :] * ang_wavenumber * azy[0] #x value * the radians/meter* cos(theta)= x value of direciton vector
    + y_wave[:, None] * ang_wavenumber * azy[1] #this si the y value 
    + st * 2*np.pi / T
    )
    #for i in range(1,npts-1):
    #f[:,-1,2] = plain_wave[:,-1] #generating the waveform. its in the last x position, all the y positions, future position
    f[trans_edge,2]=plain_wave[trans_edge]

    #difference in past and 2*present plus c^2*difference in x axis dx2/dt2 plus c^2 plus differnce in y axis dx2/dy2
    #f[1:-1,1:-1,2] = -f[1:-1,1:-1,0] + 2*f[1:-1,1:-1,1] \
    #    + c**2*(f[:-2,1:-1, 1]+f[2:,1:-1,1]-2.*f[1:-1,1:-1,1])*(dt**2/dx**2)\
    #    + c**2*(f[1:-1,:-2, 1]+f[1:-1,2:,1]-2.*f[1:-1,1:-1,1])*(dt**2/dx**2) #the future using the differnece form the past to the present and x1 to x2 and y1 to y2
    
    f[1:-1,1:-1,2] = -f[1:-1,1:-1,0] + 2*f[1:-1,1:-1,1] \
       + celarity[1:-1,1:-1]**2*(f[:-2,1:-1, 1]+f[2:,1:-1,1]-2.*f[1:-1,1:-1,1])*(dt**2/dx**2)\
      + celarity[1:-1,1:-1]**2*(f[1:-1,:-2, 1]+f[1:-1,2:,1]-2.*f[1:-1,1:-1,1])*(dt**2/dx**2)\
        - (dt**2/dx)*dampening[1:-1,1:-1]*(f[1:-1,1:-1,1]-f[1:-1,1:-1,0])
          #the future using the differnece form the past to the present and x1 to x2 and y1 to y2
    
    #f[land, 2] = 0 #bouncing waves off the land
    #en.wikipedia.org/wiki/Engquist–Majda_absorbing_boundary_condition for absorbing boundry conditions

    #push the data back for the leapfrogging
    f[:,:,0] = f[:,:,1] #present becomes past
    f[:,:,1] = f[:,:,2] #future becomes present


    st = st+dt

    alpha_field = np.clip(f[:, :, 2], 0, h)
    alpha_field = alpha_field / (h + .001)
    alpha_field[np.isnan(alpha_field)] = 0

    if k%10 ==0: #use this line to change how often frames are plotted.
                 #e.g. if k%10 ==0 will plot only every 10th timestep.
                 # if nsteps-k <= nsteps*.8 #plots the last 20% 
        fig = plt.figure(1)
        fig.clf()
        plt.imshow(
            land,
            origin="lower",
            cmap="binary",
            alpha=1
        )
        plt.imshow(f[:,:,2]*2, origin="lower", cmap="viridis_r",vmin=0, vmax=3*h, alpha = alpha_field)
        plt.colorbar()
        #ax = fig.add_subplot(projection = '3d')
        plt.title('seconds= %0.2f ' % (st) )
        #ax.set_zlim3d(-5,5)       
        plt.pause(.1)#can make this dt 

    if nsteps - k <= 10:  # last 10 frames
        fig = plt.figure(2)
        fig.clf()
        plt.imshow(
            land,
            origin="lower",
            cmap="binary",
            alpha=1
        )
        plt.imshow(f[:,:,2]*2, origin="lower", cmap="viridis_r",vmin=0, vmax=3*h, alpha = alpha_field)
        plt.colorbar()
        #ax = fig.add_subplot(projection = '3d')
        plt.title('seconds= %0.2f ' % (st) )
        #ax.set_zlim3d(-5,5)       
        plt.savefig("frame_%03d.png" % k)

loop_time = time.time() - loop_start
print(loop_time)
print(setup_time)
#for flat is:
plot_surf_3d(depth[450:700,500:700], np.asarray(f[450:700,500:700,2]),z_scale1=1, z_scale2=1, background="white", clim2=[-3,3]) #this will make a 3d rendering of the interest zone 

#plot_surf_3d(depth[450:650, 0:200], np.asarray(f[500:700, 0:200,2]),z_scale1=1, z_scale2=5, background="white", clim2=[-h/2,h/2]) #this will make a 3d rendering of the interest zone 



        




#so what is we saved f and then every time we ran the simulaiton again we started off where we were
# so what if we break the strait down into smaller portions for computational efficiency? 
    