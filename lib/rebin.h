#ifndef _REBIN_H
#define _REBIN_H

#include <vector>

// rebin_counts(Nx, x, Ix, Ny, y, Iy)
// Rebin from x to y where:
//    Nx is the number of bins in the data
//    x[Nx+1] is a vector of bin edges
//    I[Nx] is a vector of counts
//    Ny is the number of bins desired
//    y[Ny+1] is a vector of bin edges
//    I[Ny] is a vector of counts
template <class Real> void
rebin_counts(const int Nold, const Real xold[], const Real Iold[],
             const int Nnew, const Real xnew[], Real Inew[])
{
  // Note: inspired by rebin from OpenGenie, but using counts per bin 
  // rather than rates.

  // Clear the new bins
  for (int i=0; i < Nnew; i++) Inew[i] = 0.;

  // Traverse both sets of bin edges; if there is an overlap, add the portion 
  // of the overlapping old bin to the new bin.
  int iold(0), inew(0);
  while (inew < Nnew && iold < Nold) {
    const Real xold_lo = xold[iold];
    const Real xold_hi = xold[iold+1];
    const Real xnew_lo = xnew[inew];
    const Real xnew_hi = xnew[inew+1];
    if ( xnew_hi <= xold_lo ) inew++;      // new must catch up to old
    else if ( xold_hi <= xnew_lo ) iold++; // old must catch up to new
    else {
      // delta is the overlap of the bins on the x axis
      const Real delta = std::min(xold_hi, xnew_hi) - std::max(xold_lo, xnew_lo);
      const Real width = xold_hi - xold_lo;
      const Real portion = delta/width;

      Inew[inew] += Iold[iold]*portion;
      if ( xnew_hi > xold_hi ) iold++;
      else inew++;
    }
  }
}

template <class Real> inline void
rebin_counts(const std::vector<Real> &xold, const std::vector<Real> &Iold,
             const std::vector<Real> &xnew, std::vector<Real> &Inew)
{
  assert(xold.size()-1 == Iold.size());
  Inew.resize(xnew.size()-1);
  rebin_counts(Iold.size(), &xold[0], &Iold[0],
               Inew.size(), &xnew[0], &Inew[0]);
}

// rebin_intensity(Nx, x, Ix, dIx, Ny, y, Iy, dIy)
// Like rebin_counts, but includes uncertainty.  This could of course be
// done separately, but it will be faster to rebin both at the same time.
template <class Real> void
rebin_intensity(const int Nold, const Real xold[], 
		const Real Iold[], const Real dIold[],
		const int Nnew, const Real xnew[], 
		Real Inew[], Real dInew[])
{
  // Note: inspired by rebin from OpenGenie, but using counts per bin rather than rates.

  // Clear the new bins
  for (int i=0; i < Nnew; i++) dInew[i] = Inew[i] = 0.;

  // Traverse both sets of bin edges, and if there is an overlap, add the portion 
  // of the overlapping old bin to the new bin.
  int iold(0), inew(0);
  while (inew < Nnew && iold < Nold) {
    const Real xold_lo = xold[iold];
    const Real xold_hi = xold[iold+1];
    const Real xnew_lo = xnew[inew];
    const Real xnew_hi = xnew[inew+1];
    if ( xnew_hi <= xold_lo ) inew++;      // new must catch up to old
    else if ( xold_hi <= xnew_lo ) iold++; // old must catch up to new
    else {
      // delta is the overlap of the bins on the x axis
      const Real delta = std::min(xold_hi, xnew_hi) - std::max(xold_lo, xnew_lo);
      const Real width = xold_hi - xold_lo;
      const Real portion = delta/width;

      Inew[inew] += Iold[iold]*portion;
      dInew[inew] += square(dIold[iold]*portion);  // add in quadrature
      if ( xnew_hi > xold_hi ) iold++;
      else inew++;
    }
  }

  // Convert variance to standard deviation.
  for (int i=0; i < Nnew; i++) dInew[i] = sqrt(dInew[i]);
}

template <class Real> inline void
rebin_intensity(const std::vector<Real> &xold, 
		const std::vector<Real> &Iold, const std::vector<Real> &dIold,
		const std::vector<Real> &xnew, 
		std::vector<Real> &Inew, std::vector<Real> &dInew)
{
  assert(xold.size()-1 == Iold.size());
  assert(xold.size()-1 == dIold.size());
  Inew.resize(xnew.size()-1);
  dInew.resize(xnew.size()-1);
  rebin_intensity(Iold.size(), &xold[0], &Iold[0], &dIold[0],
		  Inew.size(), &xnew[0], &Inew[0], &dInew[0]);
}

template <class Real> inline void
compute_uncertainty(const std::vector<Real> &counts, 
		    std::vector<Real> &uncertainty)
{
  uncertainty.resize(counts.size());
  for (size_t i=0; i < counts.size(); i++)
    uncertainty[i] = counts[i] != 0 ? sqrt(counts[i]) : 1.;
}


#endif // _REBIN_H
