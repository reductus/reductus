from numpy import pi, arange, arctan2, sqrt, meshgrid, linspace, sin, cos, array, log, ones
from scipy import ndimage

def ConvertToCylindrical(array_in, x_min, x_max, y_min, y_max, theta_offset = 0.0, oversample_th = 2.0, oversample_r = 2.0):
    """Take an array in rectangular coordinates and transform into cylindrical
    (r,theta) coordinates.  Must specify axis limits (min and max) in real units
    of both axes.  As a side effect, this allows calculation of the center element ->
    (x0, y0) = (-x_min/x_stepsize, -y_min/y_stepsize)

    the spacing of the input mesh in the transformed variables is approximately:
    dr = (1/r) * (x dx + y dy)
    dtheta = 1/r^2 * sqrt(x^2 dy + y^2 dx)

    the output mesh is has a spacing of dr_min/oversample_r, and
    dtheta_min/oversample_th
    so that the output grid is bigger (larger array) than the input array, when
    oversample_r and oversample_th are greater than 1.

    At each pixel of the output array, a lookup pair of x, y is created
    that correspond to the r, th at that pixel.  The value of the input array
    at x, y is inserted into the output array (at r, th) via the scipy.ndimage function.

    Lookup pairs that are outside the x,y boundaries of the input array result in a zero
    being written at r,th (this occurs every time, as a rectangular r,th space maps onto
    a non-rectangular x,y space)

    A mask with the same dimensions as the output array is also generated, which has a
    value 1 everywhere the mapping was successful, and 0 where unsuccessful.

    Returns: data array in r,th space; mask; and boundaries of new r,th space
    """

    x_axis = linspace(x_min, x_max, array_in.shape[0])
    y_axis = linspace(y_min, y_max, array_in.shape[1])

    x_stepsize = float(x_max - x_min) / array_in.shape[0]
    y_stepsize = float(y_max - y_min) / array_in.shape[1]

    x,y = meshgrid(x_axis, y_axis)
    # meshgrid makes two new arrays with same dimensions as array_in,
    # but filled with x and y coordinates of each point instead of data

    r_in = sqrt(x**2 + y**2)
    theta_in = arctan2(y, x)
    # these are two more arrays with same dimensions as array_in,
    # but filled with the r, theta coordinates of each point of array_in

    dtheta_min = (1.0/r_in[r_in>0]**2 * sqrt(x[r_in>0]**2 * y_stepsize**2 + y[r_in>0]**2 * x_stepsize)).min() * 180.0/pi
    # dtheta is approximately 1/r^2 * sqrt(x^2 dy + y^2 dx)
    th_step = dtheta_min / oversample_th

    dr_min = (1.0/r_in[r_in>0] * ( abs(x[r_in>0] * x_stepsize) + abs(y[r_in>0] * y_stepsize) )).min()
    # dr is (1/r) * (x dx + y dy)
    r_step = dr_min / oversample_r

    th_out_axis = arange(theta_offset, theta_offset + 360.0 + th_step, th_step )
    r_out_axis = arange(r_in.min(), r_in.max(), r_step)

    th_out, r_out = meshgrid(th_out_axis, r_out_axis)

    x_lookup = ( r_out * cos(th_out*pi/180.0) - x_min ) / x_stepsize  # coordinates for looking up data in array_in
    y_lookup = ( r_out * sin(th_out*pi/180.0) - y_min ) / y_stepsize
    #return x_lookup, y_lookup, r_out, th_out

    data_mask = ones(r_out.shape, dtype=int)
    data_mask[x_lookup >= array_in.shape[0]] = 0
    data_mask[x_lookup < 0] = 0
    data_mask[y_lookup >= array_in.shape[1]] = 0
    data_mask[y_lookup < 0] = 0

    #x_lookup.clip(0)
    #y_lookup.clip(0)

    array_out = ndimage.map_coordinates(array_in, array([x_lookup, y_lookup]), order = 1)
    # ndimage.map_coordinates takes a source image, and a set of two arrays: the arrays hold lookup coordinates.
    # Each pixel of a new array (with dimensions equal to the lookup arrays) is set by looking at the pixel
    # in the source image with the coordinate pair specified.

    extent = [th_out.min(), th_out.max(), r_in.min(), r_in.max()]
    return array_out, data_mask, extent
    #self.qxpp.clip(0)
    #self.qzpp.clip(0)

if __name__ == '__main__':
    from pylab import imshow, show, xlabel, ylabel, colorbar, figure, title
    x, y = meshgrid(arange(-50., 150., 1), arange(-20., 30., 1))
    r = sqrt(x**2 + y**2)
    th = arctan2(y, x)
    d = sin(r*pi/25.0)**2
    #d = cos(th)**2 * 1.0/(r + 1.0)**2
    array_out, data_mask, extent = ConvertToCylindrical(d.T, -50, 150, -20, 30)
    # transposing the meshgrid because meshgrid(x,y) has shape (len(y), len(x))

    figure()
    imshow(array_out, aspect = 'auto', origin='lower', extent = extent)
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'$\sin^2(r)$ in cylindrical coords', size='large')
    colorbar()

    figure()
    imshow(d, origin='lower', extent=[-50,150,-20,30])
    xlabel(r'$x$', size='large')
    ylabel(r'$y$', size='large')
    title(r'$\sin^2(r)$ in rectangular coords', size='large')
    colorbar()

    a2, m2, e2 = ConvertToCylindrical(d.T, -50, 150, -20, 30, theta_offset=90.0)
    figure()
    imshow(a2, aspect = 'auto', origin='lower', extent=e2)
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'$\sin^2(r)$ in cylindrical coords with 90.0 deg offset', size='large')
    colorbar()
    show()


