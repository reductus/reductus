#ifndef _REBIN2D_H
#define _REBIN2D_H

#include <iostream>
#include <vector>

#include "rebin.h"

template <class Real> void
print_bins(const std::string &message,
	   unsigned int nx, unsigned int ny, const Real z[])
{
  std::cout << message << std::endl;
  for (unsigned int i=0; i < nx; i++) {
    for (unsigned int j=0; j < ny; j++) {
      std::cout << " " << z[i+j*nx];
    }
    std::cout << std::endl;
  }
}

template <class Real> void
print_bins(const std::string &message,
	   const std::vector<Real> &x,
	   const std::vector<Real> &y,
	   const std::vector<Real> &z)
{
  unsigned int nx = x.size()-1;
  unsigned int ny = y.size()-1;
  assert(nx*ny == z.size());
  print_bins(message,nx,ny,&z[0]);
}


// This is cribbed from rebin_counts in rebin.h, but with the additional
// portion parameter which gives the proportion of the bin to reassign.
// Also, it requires the initialized accumulation vector.
// TODO: make this code the basis of rebin_counts.
template <class Real> void
rebin_counts_portion(const int Nold, const Real xold[], const Real Iold[],
		     const int Nnew, const Real xnew[], Real Inew[],
		     Real ND_portion)
{
  // Note: inspired by rebin from OpenGenie, but using counts per bin
  // rather than rates.

  // Does not work in place
  assert(Iold != Inew);

  // Traverse both sets of bin edges; if there is an overlap, add the portion
  // of the overlapping old bin to the new bin.
  BinIter<Real> from(Nold, xold);
  BinIter<Real> to(Nnew, xnew);
  while (!from.atend && !to.atend) {
    if (to.hi <= from.lo) ++to; // new must catch up to old
    else if (from.hi <= to.lo) ++from; // old must catch up to new
    else {
      const Real overlap = std::min(from.hi,to.hi) - std::max(from.lo,to.lo);
      const Real portion = overlap/(from.hi-from.lo);
      Inew[to.bin] += Iold[from.bin]*portion*ND_portion;
      if (to.hi > from.hi) ++from;
      else ++to;
    }
  }


#if 0
  std::cout << "rebinning with portion " << ND_portion << std::endl;
  std::cout << "old:";
  for (int i=0; i < Nold; i++) std::cout << " " << xold[i];
  std::cout << std::endl;
  for (int i=0; i < Nold-1; i++) std::cout << " " << Iold[i];
  std::cout << std::endl;
  std::cout << "new:";
  for (int i=0; i < Nnew; i++) std::cout << " " << xnew[i];
  std::cout << std::endl;
  for (int i=0; i < Nnew-1; i++) std::cout << " " << Inew[i];
  std::cout << std::endl;
#endif

}

// rebin_counts(Nxold, xold, Nyold, yold, Iold,
//              Nxnew, xnew, Nynew, ynew, Inew)
// Rebin from old to new where:
//    Nxold,Nyold number of original bin edges
//    xold[Nxold+1], yold[Nyold+1] bin edges in x,y
//    Iold[Nxold*Nyold] input array
//    Nxnew,Nynew number of desired bin edges
//    xnew[Nxnew+1], ynew[Nynew+1] desired bin edges
//    Inew[Nxnew*Nynew] result array
template <class Real> void
rebin_counts_2D(const int Nxold, const Real xold[],
	const int Nyold, const Real yold[], const Real Iold[],
	const int Nxnew, const Real xnew[],
	const int Nynew, const Real ynew[], Real Inew[])
{

  // Clear the new bins
  for (int i=0; i < Nxnew*Nynew; i++) Inew[i] = 0.;

  // Traverse both sets of bin edges; if there is an overlap, add the portion
  // of the overlapping old bin to the new bin.  Scale this by the portion
  // of the overlap in y.
  BinIter<Real> from(Nyold, yold);
  BinIter<Real> to(Nynew, ynew);
  while (!from.atend && !to.atend) {
    if (to.hi <= from.lo) ++to; // new must catch up to old
    else if (from.hi <= to.lo) ++from; // old must catch up to new
    else {
      const Real overlap = std::min(from.hi,to.hi) - std::max(from.lo,to.lo);
      const Real portion = overlap/(from.hi-from.lo);
      rebin_counts_portion(Nxold, xold, Iold+from.bin*Nxold,
                           Nxnew, xnew, Inew+to.bin*Nxnew,
                           portion);
      if (to.hi > from.hi) ++from;
      else ++to;
    }
  }

}

template <class Real> inline void
rebin_counts_2D(const std::vector<Real> &xold,
	const std::vector<Real> &yold,
	const std::vector<Real> &Iold,
	const std::vector<Real> &xnew,
	const std::vector<Real> &ynew,
	std::vector<Real> &Inew)
{
  assert( (xold.size()-1)*(yold.size()-1) == Iold.size());
  Inew.resize( (xnew.size()-1)*(ynew.size()-1) );
  rebin_counts_2D(xold.size()-1, &xold[0], yold.size()-1, &yold[0], &Iold[0],
                  xnew.size()-1, &xnew[0], ynew.size()-1, &ynew[0], &Inew[0]);
}

#endif
