from hypothesis import given, strategies as st
from processor import sanitize_license_plate, parse_trip_mileage, format_rental_invoice

@given(st.text() | st.none())
def test_sanitize_license_plate_no_crash(s):
    #To-Do:Using try and except complete this function.
    pass

@given(st.text() | st.none())
def test_parse_trip_mileage_safe(s):
    #To-Do:Using try and except complete this function.
    pass

@given(st.text() | st.none())
def test_format_rental_invoice_safe(s):
    #To-Do:Using try and except complete this function.
    pass