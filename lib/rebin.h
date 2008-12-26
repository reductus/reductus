#ifndef _REBIN_H
#define _REBIN_H

#include <iostream>
#include <vector>
#include <stdexcept>

// Define a bin iterator to adapt to either foward or reversed inputs.
template <class Real>
class BinIter {
  bool forward;
  int n;
  const Real *edges;
public:
  int bin;     // Index of the corresponding bin
  Real lo, hi; // Low and high values for the bin edges.
  bool atend;  // True when we increment beyond the final bin.
  BinIter(int _n, const Real *_edges) {
    // n is number of bins, which is #edges-1
    // edges are the values of the bin edges.
    n = _n; edges = _edges;
    forward = edges[0] < edges[n];
    if (forward) {
      bin = 0;
      lo = edges[0];
      hi = edges[1];
    } else {
      bin = n - 1;
      lo = edges[n];
      hi = edges[n-1];
    }
    atend = n < 1;
  }
  BinIter& operator++() {
    if (atend) {
      throw std::out_of_range("moving beyond final bin");
    }
    lo = hi;
    if (forward) {
      bin++;
      atend = (bin >= n);
      if (!atend) hi = edges[bin+1];
    } else {
      bin--;
      atend = (bin < 0);
      if (!atend) hi = edges[bin];
    }
  }
};

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
  BinIter<Real> from(Nold, xold);
  BinIter<Real> to(Nnew, xnew);
  while (!from.atend && !to.atend) {
    //std::cout << "from " << from.bin << ": [" << from.lo << ", " << from.hi << "]\n";
    //std::cout << "to " << to.bin << ": [" << to.lo << ", " << to.hi << "]\n";
    if (to.hi <= from.lo) ++to; // new must catch up to old
    else if (from.hi <= to.lo) ++from; // old must catch up to new
    else {
      const Real overlap = std::min(from.hi,to.hi) - std::max(from.lo,to.lo);
      const Real portion = overlap/(from.hi-from.lo);

      Inew[to.bin] += Iold[from.bin]*portion;
      if (to.hi > from.hi) ++from;
      else ++to;
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

  // Traverse both sets of bin edges; if there is an overlap, add the portion
  // of the overlapping old bin to the new bin.
  BinIter<Real> from(Nold, xold);
  BinIter<Real> to(Nnew, xnew);
  while (!from.atend && !to.atend) {
    //std::cout << "from " << from.bin << ": [" << from.lo << ", " << from.hi << "]\n";
    //std::cout << "to " << to.bin << ": [" << to.lo << ", " << to.hi << "]\n";
    if (to.hi <= from.lo) ++to; // new must catch up to old
    else if (from.hi <= to.lo) ++from; // old must catch up to new
    else {
      const Real overlap = std::min(from.hi,to.hi) - std::max(from.lo,to.lo);
      const Real portion = overlap/(from.hi-from.lo);

      Inew[to.bin] += Iold[from.bin]*portion;
      dInew[to.bin] += square(dIold[from.bin]*portion);  // add in quadrature
      if (to.hi > from.hi) ++from;
      else ++to;
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
