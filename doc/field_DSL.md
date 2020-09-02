

## Multiplicity Specifier (None, ?, *, +)
 *  None: required, shared value for all data sets {multiple: false, required: true}
 *  ?: optional, shared value for all data sets {multiple: false, required: false}
 *  +: required, one value per data set {multiple: true, required: true}
 *  *: optional, one value per data set {multiple: true, required: false}

## Length Specifier ([n])
*  No brackets: value is not treated as a list {length: 1}
*  Empty brackets: value is a list of unspecified length {length: 0}
*  Non-empty brackets: value is a list of specified length {length: n}
    * e.g. \[6\] means length = 6