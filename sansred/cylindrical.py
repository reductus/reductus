from numpy import pi, arange, arctan2, sqrt, meshgrid, linspace, sin, cos, array, log, ones, histogram2d, logical_and, zeros_like, ones_like, degrees, mod

def ConvertToCylindrical(array_in, x_min, x_max, y_min, y_max, theta_offset = 0.0, min_r = None, oversample_th = 1.0, oversample_r = 1.0):
    x_axis = linspace(x_min, x_max, array_in.shape[1])
    y_axis = linspace(y_min, y_max, array_in.shape[0])

    x_stepsize = float(x_max - x_min) / (array_in.shape[1] - 1)
    y_stepsize = float(y_max - y_min) / (array_in.shape[0] - 1)

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
    if min_r == None:
        min_r = dr_min

    th_out_min = theta_offset
    th_out_max = theta_offset + 360.0 + th_step
    th_out_axis = arange(th_out_min, th_out_max, th_step )

    r_in_min = r_in.min()
    r_in_max = r_in.max()
    r_out_min = max(r_in.min(), min_r)
    r_out_max = r_in_max
    r_out_axis = arange(r_out_min, r_out_max, r_step)

    th_out, r_out = meshgrid(th_out_axis, r_out_axis)
    output_grid = zeros_like(th_out)
    output_norm = zeros_like(th_out)

    forward_r_list = ( r_in - r_in_min ).flatten()
    forward_th_list = (mod(degrees(theta_in) - theta_offset, 360.0) + theta_offset).flatten()

    reverse_x = (r_out * cos(th_out*pi/180.0))
    reverse_y = (r_out * sin(th_out*pi/180.0))

    inshape = r_in.shape
    reverse_norm = (ones_like(th_out)).flatten()
    hist2d, xedges, yedges = histogram2d(reverse_x.flatten(),reverse_y.flatten(), \
        bins = (inshape[1],inshape[0]), range=((x_min, x_max + x_stepsize),(y_min,y_max+y_stepsize)), weights=reverse_norm)
    input_count = hist2d.T # how many bins in the output map to this bin in the input in the reverse mapping
    input_count += 1.0 # how many bins will be mapped in the forward mapping (all of them)

    forward_weights = (array_in/input_count).flatten()
    forward_norm = (1.0 / input_count).flatten()

    outshape = th_out.shape
    #print('outshape: ', outshape)
    hist2d, xedges, yedges = histogram2d(forward_r_list,forward_th_list, \
        bins = (outshape[0],outshape[1]), range=((r_out_min,r_out_max+r_step),(th_out_min,th_out_max+th_step)), weights=forward_weights)
    output_grid += hist2d # counts in every pixel in input added to corresponding output pixel (forward)
    hist2d, xedges, yedges = histogram2d(forward_r_list,forward_th_list, \
        bins = (outshape[0],outshape[1]), range=((r_out_min,r_out_max+r_step),(th_out_min,th_out_max+th_step)), weights=forward_norm)
    output_norm += hist2d # weight of every pixel in input added to corresponding output-weight pixel (forward)

    reverse_x_lookup = ((reverse_x - x_min) / x_stepsize).astype(int)
    reverse_y_lookup = ((reverse_y - y_min) / y_stepsize).astype(int)

    reverse_mask = logical_and((reverse_x_lookup >=0), (reverse_x_lookup < r_in.shape[1]))
    reverse_mask = logical_and(reverse_mask, (reverse_y_lookup >= 0))
    reverse_mask = logical_and(reverse_mask, (reverse_y_lookup < r_in.shape[0]))

    reverse_x_lookup = reverse_x_lookup[reverse_mask]
    reverse_y_lookup = reverse_y_lookup[reverse_mask]

    reverse_r_list = r_out[reverse_mask]
    reverse_th_list = th_out[reverse_mask]

    reverse_weights = (array_in/input_count)[reverse_y_lookup, reverse_x_lookup]
    reverse_norm = (1.0/input_count)[reverse_y_lookup, reverse_x_lookup]

    # counts from corresponding pixel in input added to every output pixel (reverse lookup)
    output_grid[reverse_mask] += reverse_weights

    # weight of corresponding pixel in input added to every output-weight pixel (reverse lookup)
    output_norm[reverse_mask] += reverse_norm

    normalized = zeros_like(output_grid)
    normalized[reverse_mask] = output_grid[reverse_mask] / output_norm[reverse_mask]
    output = output_grid.copy()
    extent = [th_out.min(), th_out.max(), r_out.min(), r_out.max()]

    return output_grid, output_norm, normalized, extent

if __name__ == '__main__':
    from pylab import imshow, show, xlabel, ylabel, colorbar, figure, title
    x, y = meshgrid(linspace(-50., 150., 201), linspace(-20., 30., 51))
    r = sqrt(x**2 + y**2)
    th = arctan2(y, x)
    d = sin(r*pi/25.0)**2
    #d = cos(th)**2 * 1.0/(r + 1.0)**2
    array_out, data_mask, normalized, extent = ConvertToCylindrical(d, -50, 150, -20, 30)
    # transposing the meshgrid because meshgrid(x,y) has shape (len(y), len(x))

    figure()
    imshow(array_out, aspect = 'auto', origin='lower', extent = extent, interpolation="nearest")
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'$\sin^2(r)$ in cylindrical coords', size='large')
    colorbar()

    figure()
    imshow(data_mask, aspect = 'auto', origin='lower', extent=extent, interpolation="nearest")
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'norm for $\sin^2(r)$ in cylindrical coords', size='large')
    colorbar()

    figure()
    imshow(normalized, aspect = 'auto', origin='lower', extent=extent, interpolation="nearest")
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'normalized transform for $\sin^2(r)$ in cylindrical coords', size='large')
    colorbar()

    figure()
    imshow(d, origin='lower', extent=[-50,150,-20,30], interpolation="nearest")
    xlabel(r'$x$', size='large')
    ylabel(r'$y$', size='large')
    title(r'$\sin^2(r)$ in rectangular coords', size='large')
    colorbar()

    a2, m2, n2, e2 = ConvertToCylindrical(d, -50, 150, -20, 30, theta_offset=-90.0)
    figure()
    imshow(a2, aspect = 'auto', origin='lower', extent=e2, interpolation="nearest")
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'$\sin^2(r)$ in cylindrical coords with -90.0 deg offset', size='large')
    colorbar()

    print("show?")
    figure()
    imshow(n2, aspect = 'auto', origin='lower', extent=e2, interpolation="nearest")
    #imshow(m2.T, origin='lower', extent=e2, interpolation="nearest")
    xlabel(r'$\theta ({}^{\circ})$', size='large')
    ylabel(r'$r$', size='large')
    title(r'normalized $\sin^2(r)$ in cylindrical coords with -90.0 deg offset', size='large')
    colorbar()
    show()
