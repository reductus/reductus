from PIL import Image, ImageDraw
import numpy

def annular_mask_antialiased(shape, center, inner_radius, outer_radius,
                             background_value=0.0, mask_value=1.0,
                             oversampling=8):
    """
    Takes shape tuple: (x, y) - this is the size of the output image
    center tuple: (x, y)
    inner_radius: float
    outer_radius: float
    background_value: float (the image is initialized to this value)
    mask_value: floate (the annulus is drawn with this value)
    oversampling: int (the mask is drawn on a canvas this many times bigger
    than the final size, then resampled down to give smoother edges)
    """
    # Create a 32-bit float image
    intermediate_shape = (shape[0]*int(oversampling), shape[1]*int(oversampling))
    im = Image.new('F', intermediate_shape, color=background_value)

    # Making a handle to the drawing tool
    draw = ImageDraw.Draw(im)

    # Have to scale everything in the problem by the oversampling
    outer_radius_r = outer_radius * oversampling
    inner_radius_r = inner_radius * oversampling
    center_r = (center[0] * oversampling, center[1] * oversampling)


    # Calculate bounding box for outer circle
    x_outer_min = center_r[0] - outer_radius_r
    x_outer_max = center_r[0] + outer_radius_r
    y_outer_min = center_r[1] - outer_radius_r
    y_outer_max = center_r[1] + outer_radius_r
    outer_bbox = [x_outer_min, y_outer_min, x_outer_max, y_outer_max]

    # Calculate bounding box for inner circle
    x_inner_min = center_r[0] - inner_radius_r
    x_inner_max = center_r[0] + inner_radius_r
    y_inner_min = center_r[1] - inner_radius_r
    y_inner_max = center_r[1] + inner_radius_r
    inner_bbox = [x_inner_min, y_inner_min, x_inner_max, y_inner_max]

    # Draw the circles:  outer one first
    draw.ellipse(outer_bbox, fill=mask_value)

    # Now overlay the inner circle
    draw.ellipse(inner_bbox, fill=background_value)

    # Now bring it back to size, with antialiasing
    #im.thumbnail(shape, Image.ANTIALIAS)
    # This produced artifacts - output.max() was > mask_value by 10% or more!

    # Using numpy reshape instead (rebinning) - see Scipy cookbook
    output = numpy.asarray(im)
    output = output.reshape(shape[0], oversampling, shape[1], oversampling).mean(1).mean(2)
    return output
