#ifndef _REBIN2D_H
#define _REBIN2D_H

#include <iostream>
#include <vector>


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
      const Real delta = std::min(xold_hi, xnew_hi)
	- std::max(xold_lo, xnew_lo);
      const Real width = xold_hi - xold_lo;
      const Real portion = delta/width;

      Inew[inew] += Iold[iold]*portion*ND_portion;
      if ( xnew_hi > xold_hi ) iold++;
      else inew++;
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
//    xold[Nxold], yold[Nyold] bin edges in x,y
//    Iold[(Nxold-1)*(Nyold-1)] input array
//    Nxnew,Nynew number of desired bin edges
//    xnew[Nxnew], ynew[Nynew] desired bin edges
//    Inew[(Nxnew-1)*(Nynew-1)] result array
// TODO: N is bin edges in rebin2D but bins in rebin.
template <class Real> void
rebin_counts_2D(const int Nxold, const Real xold[], 
	const int Nyold, const Real yold[], const Real Iold[],
	const int Nxnew, const Real xnew[],
	const int Nynew, const Real ynew[], Real Inew[])
{

  // Clear the new bins
  for (int i=0; i < (Nxnew-1)*(Nynew-1); i++) Inew[i] = 0.;

  // Traverse both sets of bin edges; if there is an overlap, add the portion
  // of the overlapping old bin to the new bin.  Scale this by the portion
  // of the overlap in y.
  int jold(0), jnew(0);
  while (jnew < Nynew && jold < Nyold) {
    //    print_bins("test",Nxnew-1,Nynew-1,&Inew[0]);
    const Real yold_lo = yold[jold];
    const Real yold_hi = yold[jold+1];
    const Real ynew_lo = ynew[jnew];
    const Real ynew_hi = ynew[jnew+1];
    if ( ynew_hi <= ynew_lo ) jnew++;      // new must catch up to old
    else if ( yold_hi <= ynew_lo ) jold++; // old must catch up to new
    else {
      // delta is the overlap of the bins on the y axis
      const Real delta = std::min(yold_hi, ynew_hi)
	- std::max(yold_lo, ynew_lo);
      const Real width = yold_hi - yold_lo;
      const Real portion = delta/width;

      rebin_counts_portion(Nxold, xold, Iold+jold*(Nxold-1),
			   Nxnew, xnew, Inew+jnew*(Nxnew-1),
			   portion);

      if ( ynew_hi > yold_hi ) jold++;
      else jnew++;
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
  rebin2D(xold.size(), &xold[0], yold.size(), &yold[0], &Iold[0],
	  xnew.size(), &xnew[0], ynew.size(), &ynew[0], &Inew[0]);
}

#endif
