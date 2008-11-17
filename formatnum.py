# This program is public domain
"""
Format numbers nicely for printing.
"""

import math
__all__ = ['format_uncertainty']

def format_uncertainty(value,uncertainty):
    """
    Given a value and an uncertainty, return a concise string representation.

    The returned string uses only the number of digits warranted by the
    uncertainty in the measurement.
    """
    if uncertainty == None:
        return "%g"%value

    # Process sign
    sign = "-" if value < 0 else ""
    value = abs(value)

    # Represent error as (##) at the end of the digit string
    val_place = int(math.floor(math.log10(value)))
    err_place = int(math.floor(math.log10(uncertainty)))
    err_str = "(%2d)"%int(uncertainty/10.**(err_place-1)+0.5)

    if err_place > val_place:
        # Degenerate case: error bigger than value
        # The mantissa is 0.#(##)e#, 0.0#(##)e# or 0.00#(##)e#
        if err_place - val_place > 2: value = 0
        val_place = int(math.floor((err_place+2)/3.))*3
        digits_after_decimal = val_place - err_place + 1
        val_str = "%.*f%s"%(digits_after_decimal,value/10.**val_place,err_str)
        if val_place != 0: val_str += "e%d"%val_place
    elif err_place == val_place:
        # Degenerate case: error and value the same order of magnitude
        # The value is ##(##)e#, #.#(##)e# or 0.##(##)e#
        val_place = int(math.floor((err_place+1)/3.))*3
        digits_after_decimal = val_place - err_place + 1
        val_str = "%.*f%s"%(digits_after_decimal,value/10.**val_place,err_str)
        if val_place != 0: val_str += "e%d"%val_place
    elif err_place <= 1 and val_place >= -3:
        # Normal case: nice numbers and errors
        # The value is ###.###(##)
        digits_after_decimal = abs(err_place-1)
        val_str = "%.*f%s"%(digits_after_decimal,value,err_str)
    else:
        # Extreme cases: zeros before value or after error
        # The value is ###.###(##)e#, ##.####(##)e# or #.#####(##)e#
        total_digits = val_place - err_place + 2
        val_place = int(math.floor(val_place/3.))*3
        val_str = "%.*g%se%d"%(total_digits,
                               value/10.**val_place,
                               err_str,val_place)

    return sign+val_str


def test():
    value_str = format_uncertainty  # Changed name after testing

    # val_place > err_place
    assert value_str(1235670,766000) == "1.24(77)e6"
    assert value_str(123567.,76600) == "124(77)e3"
    assert value_str(12356.7,7660) == "12.4(77)e3"
    assert value_str(1235.67,766) == "1.24(77)e3"
    assert value_str(123.567,76.6) == "124(77)"
    assert value_str(12.3567,7.66) == "12.4(77)"
    assert value_str(1.23567,.766) == "1.24(77)"
    assert value_str(.123567,.0766) == "0.124(77)"
    assert value_str(.0123567,.00766) == "0.0124(77)"
    assert value_str(.00123567,.000766) == "0.00124(77)"
    assert value_str(.000123567,.0000766) == "124(77)e-6"
    assert value_str(.0000123567,.00000766) == "12.4(77)e-6"
    assert value_str(.00000123567,.000000766) == "1.24(77)e-6"
    assert value_str(.000000123567,.0000000766) == "124(77)e-9"
    assert value_str(.00000123567,.0000000766) == "1.236(77)e-6"
    assert value_str(.0000123567,.0000000766) == "12.357(77)e-6"
    assert value_str(.000123567,.0000000766) == "123.567(77)e-6"
    assert value_str(.00123567,.000000766) == "0.00123567(77)"
    assert value_str(.0123567,.00000766) == "0.0123567(77)"
    assert value_str(.123567,.0000766) == "0.123567(77)"
    assert value_str(1.23567,.000766) == "1.23567(77)"
    assert value_str(12.3567,.00766) == "12.3567(77)"
    assert value_str(123.567,.0764) == "123.567(76)"
    assert value_str(1235.67,.764) == "1235.67(76)"
    assert value_str(12356.7,7.64) == "12356.7(76)"
    assert value_str(123567,76.4) == "123567(76)"
    assert value_str(1235670,764) == "1.23567(76)e6"
    assert value_str(12356700,764) == "12.3567(76)e6"
    assert value_str(123567000,7640) == "123.567(76)e6"
    assert value_str(1235670000,76400) == "1.23567(76)e9"

    # val_place == err_place
    assert value_str(123567,764000) == "0.12(76)e6"
    assert value_str(12356.7,76400) == "12(76)e3"
    assert value_str(1235.67,7640) == "1.2(76)e3"
    assert value_str(123.567,764) == "0.12(76)e3"
    assert value_str(12.3567,76.4) == "12(76)"
    assert value_str(1.23567,7.64) == "1.2(76)"
    assert value_str(.123567,.764) == "0.12(76)"
    assert value_str(.0123567,.0764) == "12(76)e-3"
    assert value_str(.00123567,.00764) == "1.2(76)e-3"
    assert value_str(.000123567,.000764) == "0.12(76)e-3"

    # val_place == err_place-1
    assert value_str(123567,7640000) == "0.1(76)e6"
    assert value_str(12356.7,764000) == "0.01(76)e6"
    assert value_str(1235.67,76400) == "0.001(76)e6"
    assert value_str(123.567,7640) == "0.1(76)e3"
    assert value_str(12.3567,764) == "0.01(76)e3"
    assert value_str(1.23567,76.4) == "0.001(76)e3"
    assert value_str(.123567,7.64) == "0.1(76)"
    assert value_str(.0123567,.764) == "0.01(76)"
    assert value_str(.00123567,.0764) == "0.001(76)"
    assert value_str(.000123567,.00764) == "0.1(76)e-3"

    # val_place == err_place-2
    assert value_str(12356700,7640000000) == "0.0(76)e9"
    assert value_str(1235670,764000000) == "0.00(76)e9"
    assert value_str(123567,76400000) == "0.000(76)e9"
    assert value_str(12356,7640000) == "0.0(76)e6"
    assert value_str(1235,764000) == "0.00(76)e6"
    assert value_str(123,76400) == "0.000(76)e6"
    assert value_str(12,7640) == "0.0(76)e3"
    assert value_str(1,764) == "0.00(76)e3"
    assert value_str(0.1,76.4) == "0.000(76)e3"
    assert value_str(0.01,7.64) == "0.0(76)"
    assert value_str(0.001,0.764) == "0.00(76)"
    assert value_str(0.0001,0.0764) == "0.000(76)"
    assert value_str(0.00001,0.00764) == "0.0(76)e-3"

    # val_place == err_place-3
    assert value_str(12356700,76400000000) == "0.000(76)e12"
    assert value_str(1235670,7640000000) == "0.0(76)e9"
    assert value_str(123567,764000000) == "0.00(76)e9"
    assert value_str(12356,76400000) == "0.000(76)e9"
    assert value_str(1235,7640000) == "0.0(76)e6"
    assert value_str(123,764000) == "0.00(76)e6"
    assert value_str(12,76400) == "0.000(76)e6"
    assert value_str(1,7640) == "0.0(76)e3"
    assert value_str(0.1,764) == "0.00(76)e3"
    assert value_str(0.01,76.4) == "0.000(76)e3"
    assert value_str(0.001,7.64) == "0.0(76)"
    assert value_str(0.0001,0.764) == "0.00(76)"
    assert value_str(0.00001,0.0764) == "0.000(76)"
    assert value_str(0.000001,0.00764) == "0.0(76)e-3"

    # negative values
    assert value_str(-1235670,765000) == "-1.24(77)e6"
    assert value_str(-1.23567,.765) == "-1.24(77)"
    assert value_str(-.00000123567,.0000000765) == "-1.236(77)e-6"
    assert value_str(-12356.7,7.64) == "-12356.7(76)"
    assert value_str(-123.567,764) == "-0.12(76)e3"
    assert value_str(-1235.67,76400) == "-0.001(76)e6"
    assert value_str(-.000123567,.00764) == "-0.1(76)e-3"
    assert value_str(-12356,7640000) == "-0.0(76)e6"
    assert value_str(-12,76400) == "-0.000(76)e6"
    assert value_str(-0.0001,0.764) == "-0.00(76)"


if __name__ == "__main__": test()
