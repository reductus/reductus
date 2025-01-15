import { select, selectAll, event as _event, mouse } from 'd3-selection';
import { dispatch } from 'd3-dispatch';
import { drag } from 'd3-drag';
import { brush } from 'd3-brush';
import { scaleLinear, scaleLog, scaleSqrt, scalePow } from 'd3-scale';
import { line } from 'd3-shape';
import { axisLeft, axisRight, axisBottom, axisTop } from 'd3-axis';
import { zoom, zoomIdentity } from 'd3-zoom';
import { range, min, max, extent, merge } from 'd3-array';
import { rgb } from 'd3-color';

export const d3 = {
  select, selectAll, mouse,
  get event() {
    return _event
  },
  dispatch,
  drag,
  brush,
  scaleLinear, scaleLog, scaleSqrt, scalePow,
  line,
  axisLeft, axisRight, axisBottom, axisTop,
  zoom, zoomIdentity,
  range, min, max, extent, merge,
  rgb
}

export {
  select,
  selectAll,
  _event as event,
  mouse,
  dispatch,
  drag,
  brush
}