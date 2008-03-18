#include <iostream>
#include <cmath>
#include <cassert>
#include "rebin.h"

void parray(const char name[], int n, const double v[])
{
  std::cout << name << ": ";			   
  for (int k=0; k < n; k++) {   
    std::cout << v[k] << " ";			   
  }						   
  std::cout << std::endl;			   
}

bool check(int n, const double results[], 
	   const double target[], double tol)
{
  for (int k=0; k < n; k++) {
    if (fabs(results[k]-target[k]) > tol) {
      parray("rebin_counts expected",n,target);
      parray("but got",n,results);
      return false;
    }
  }
  return true;
}

const double tolerance = 1e-14;
#define SHOW(X) parray(#X,sizeof(X)/sizeof(*X),X)
#define TEST(BIN,VAL,REBIN,TARGET) do {		\
    int n = sizeof(BIN)/sizeof(*BIN);		\
    int k = sizeof(TARGET)/sizeof(*TARGET);	\
    std::vector<double> result(k);		\
    rebin_counts(n,BIN,VAL,k,REBIN,&result[0]);	\
    if ( !check(k,&result[0],TARGET,tolerance) ) { \
      retval = 1;				\
      SHOW(BIN); SHOW(VAL); SHOW(REBIN);	\
    }						\
 } while (0)


int main(int argc, char *argv[])
{
  int retval = 0;
  { double // Split a value
      bin[]={1,2,3,4},
      val[]={10,20,30},
      rebin[]={1,2.5,4},
      target[]={20,40};
      TEST(bin,val,rebin,target);
  }
  { double  // bin is a superset of rebin
      bin[]={0,1,2,3,4},
      val[]={5,10,20,30},
      rebin[]={1,2.5,3},
      target[]={20,10};
      TEST(bin,val,rebin,target);
  }
  { double // bin is a subset of rebin
      bin[]={1,   2,   3,   4,   5,  6},
      val[]={  10,  20,  30,  40,  50},
      rebin[]={     2.5, 3.5},
      target[]={25};
      TEST(bin,val,rebin,target);
  }
  { double // one bin to many
      bin[]={1,   2,   3,   4,   5,  6},
      val[]={  10,  20,  30,  40,  50},
      rebin[]={  2.1, 2.2, 2.3, 2.4 },
      target[]={2, 2, 2};
      TEST(bin,val,rebin,target);
  }
  { double // many bins to one
      bin[]={1,   2,   3,   4,   5,  6},
      val[]={  10,  20,  30,  40,  50},
      rebin[]={  2.5, 4.5 },
      target[]={ 60 };
      TEST(bin,val,rebin,target);
  }

#ifdef SPEED_CHECK // cost to rebin a 250x300x1000 dataset
  {
    std::vector<double> bin(1001);
    std::vector<double> val(100);
    std::vector<double> rebin(201);
    std::vector<double> result(200);

    // Linear binning
    for (size_t i=0; i < bin.size(); i++) bin[i]=i;
    for (size_t i=0; i < val.size(); i++) val[i]=10;

    // Logarithmic rebinning
    int n = rebin.size()-1;
    double start = 0.5;
    double stop = bin[bin.size()-1];
    double step = exp(log(stop/start)/n);
    rebin[0] = start;
    for (size_t i=1; i < rebin.size(); i++) rebin[i] = step * rebin[i-1];
    assert(fabs((rebin[rebin.size()-1]-stop)/stop) < 1e-10);

    for (size_t i = 0; i < 250*300; i++) {
      rebin_counts(val.size(),&bin[0],&val[0],
		   result.size(),&rebin[0],&result[0]);
    }
  }
#endif // SPEED_CHECK

  return retval;
}
